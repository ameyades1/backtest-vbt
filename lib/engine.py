"""One configurable trade engine for every strategy in strategies/*.json.

Config (a dict, normally loaded from JSON):
  timeframe   "M" | "W"                    signal candles
  setup       {"type": "ema_breakout", "span": 61}             Open < EMA < Close
              {"type": "stochrsi_cross", "rsi": 14, "stoch": 14, "k": 3, "d": 3, "oversold": 30}
                                                               %K crosses above %D with %D < oversold
              {"type": "stochrsi_macd", ...stochrsi keys..., "macd": [12, 26, 9], "window": 3}
                                                               MACD crosses above its signal line with
                                                               MACD < 0, on the StochRSI-cross candle or
                                                               within `window` candles after it; signal
                                                               is the MACD-cross candle
              {"type": "stochrsi_wmacd", ...stochrsi keys..., "macd": [12, 26, 9], "window_weeks": 13}
                                                               timeframe "W": monthly StochRSI cross (completed
                                                               month), then weekly MACD crosses above signal
                                                               below zero within N weeks of that month's end
  filters     (checked at the signal candle's close, all optional)
              {"trend_ema": {"span": 61, "timeframes": ["M", "W", "D"]},   close > EMA on each,
                                                                           using the last completed bar
               "rsi_min": {"period": 14, "value": 50, "timeframe": "M"}}   RSI on the signal timeframe
                                                                           (or the last completed `timeframe` bar)
  entry       {"valid_bars": 1,                 buy-stop above the signal High for the next N bars
               "day_filters": {"weekly_ema": 61, "daily_ema": 61, "market_sma": 200}}
                                                optional, checked on the fill day:
                                                last completed week's Close >= weekly EMA,
                                                previous day's Close >= daily EMA,
                                                market (lib/market.py) above its N-day SMA at the
                                                previous close; pass the regime as `market`
  stop        {"type": "none" | "signal_low" | "prev_week_low" | "trail_pct", "pct": 0.10,
               "trail": "weekly_low"}           trail_pct: Sharekhan trail fixed in rupees;
                                                trail weekly_low: raise to each completed week's Low
              "market_tighten": "weekly_low" | "exit"   while the market (as market_sma) closed below its
                                                SMA the day before: raise the stop to the last completed
                                                week's Low | sell at that day's Open
  exits       {"target_pct": 0.15 | null,
               "ema_close": {"span": 61, "timeframe": "M"} | null,
                                                   next open after a close below EMA (signal timeframe
                                                   unless `timeframe` is given)
               "max_days": 180 | null}             open of the first day >= N calendar days after entry
Fill rules: gaps fill at Open; each day checks time, gap-stop, gap-target, EMA exit, stop, target
in that order; the entry day checks only the Close. One open trade per stock.
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd
from .indicators import resample, ema, rsi, stoch_rsi, macd


@dataclass
class Trade:
    symbol: str
    signal_date: pd.Timestamp
    entry_date: pd.Timestamp
    entry: float
    exit_date: pd.Timestamp | None
    exit: float | None
    reason: str
    stop: float | None = None


def _on_candles(daily, ftf, values, last_day):
    """Value of a per-candle array of timeframe `ftf` at the last completed `ftf` candle, for each signal
    candle whose last daily bar is `last_day`. Weekly: week label (Friday) on/before that day; monthly:
    the month's last trading day."""
    days = daily.index
    fb = resample(daily, ftf)
    ref = fb.index if ftf == "W" else days[np.searchsorted(days, fb.index, side="right") - 1]
    idx = np.searchsorted(ref, days[last_day], side="right") - 1
    return np.where(idx >= 0, values[np.clip(idx, 0, None)], False), idx


def _signal_mask(daily, bars, tf, cfg):
    days = daily.index
    setup = cfg["setup"]
    if setup["type"] == "ema_breakout":
        e = ema(bars["Close"], setup.get("span", 61))
        sig = ((bars["Open"] < e) & (e < bars["Close"])).to_numpy()
    elif setup["type"] == "stochrsi_cross":
        _, K, D = stoch_rsi(bars["Close"], setup.get("rsi", 14), setup.get("stoch", 14),
                            setup.get("k", 3), setup.get("d", 3))
        sig = ((K > D) & (K.shift() <= D.shift()) & (D < setup.get("oversold", 30))).to_numpy()
    elif setup["type"] == "stochrsi_macd":
        _, K, D = stoch_rsi(bars["Close"], setup.get("rsi", 14), setup.get("stoch", 14),
                            setup.get("k", 3), setup.get("d", 3))
        st = (K > D) & (K.shift() <= D.shift()) & (D < setup.get("oversold", 30))
        m, ms, _ = macd(bars["Close"], *setup.get("macd", [12, 26, 9]))
        mx = (m > ms) & (m.shift() <= ms.shift()) & (m < 0)
        recent = st.astype(int).rolling(setup.get("window", 3) + 1, min_periods=1).max() > 0
        sig = (mx & recent).to_numpy()
    elif setup["type"] == "stochrsi_wmacd":
        # monthly StochRSI cross sets up; weekly MACD cross below zero within `window_weeks` triggers
        mb = resample(daily, "M")
        _, K, D = stoch_rsi(mb["Close"], setup.get("rsi", 14), setup.get("stoch", 14),
                            setup.get("k", 3), setup.get("d", 3))
        mcross = ((K > D) & (K.shift() <= D.shift()) & (D < setup.get("oversold", 30))).to_numpy()
        m_last = days[np.searchsorted(days, mb.index, side="right") - 1]     # month's last trading day
        cross_days = m_last[mcross]
        ld = days[np.searchsorted(days, bars.index, side="right") - 1]
        k = np.searchsorted(cross_days, ld, side="right") - 1                # latest completed cross
        since = (np.where(k >= 0, (ld - cross_days[np.clip(k, 0, None)]).days, 10 ** 6) if len(cross_days)
                 else np.full(len(ld), 10 ** 6))
        m, ms, _ = macd(bars["Close"], *setup.get("macd", [12, 26, 9]))
        mx = ((m > ms) & (m.shift() <= ms.shift()) & (m < 0)).to_numpy()
        sig = mx & (since <= 7 * setup.get("window_weeks", 13))
    else:
        raise ValueError(f"unknown setup {setup['type']}")
    sig = sig.copy()
    f = cfg.get("filters", {})
    last_day = np.searchsorted(days, bars.index, side="right") - 1       # last daily bar of each candle
    if "trend_ema" in f:
        span = f["trend_ema"].get("span", 61)
        for ftf in f["trend_ema"]["timeframes"]:
            if ftf == tf:
                sig &= (bars["Close"] > ema(bars["Close"], span)).to_numpy()
            elif ftf == "D":
                sig &= (daily["Close"] > ema(daily["Close"], span)).to_numpy()[last_day]
            else:
                fb = resample(daily, ftf)
                ok = (fb["Close"] > ema(fb["Close"], span)).to_numpy()
                sig &= _on_candles(daily, ftf, ok, last_day)[0]
    if "rsi_min" in f:
        rtf = f["rsi_min"].get("timeframe", tf)
        rb = bars if rtf == tf else resample(daily, rtf)
        ok = (rsi(rb["Close"], f["rsi_min"].get("period", 14)) > f["rsi_min"]["value"]).to_numpy()
        sig &= ok if rtf == tf else _on_candles(daily, rtf, ok, last_day)[0]
    return sig


def simulate(daily: pd.DataFrame, symbol: str, cfg: dict, market: pd.Series | None = None) -> list[Trade]:
    tf = cfg["timeframe"]
    bars = resample(daily, tf)
    days = daily.index
    sig = _signal_mask(daily, bars, tf, cfg)
    d = daily[["Open", "High", "Low", "Close"]].to_numpy()
    bar_end = np.searchsorted(days, bars.index, side="right")          # first day after each candle

    entry_cfg, stop_cfg, ex = cfg.get("entry", {}), cfg.get("stop", {"type": "none"}), cfg.get("exits", {})
    valid = entry_cfg.get("valid_bars", 1)
    dayf = entry_cfg.get("day_filters", {})
    stype = stop_cfg.get("type", "none")
    mt = stop_cfg.get("market_tighten")                 # None | "weekly_low" | "exit"
    need_weeks = stype == "prev_week_low" or stop_cfg.get("trail") == "weekly_low" or "weekly_ema" in dayf \
        or mt == "weekly_low"
    if need_weeks:
        w = resample(daily, "W")
        w_end = np.searchsorted(days, w.index, side="right")
        last_w = np.searchsorted(w_end, np.arange(len(days)), side="right") - 1   # last completed week
        w_low = w["Low"].to_numpy()
        if "weekly_ema" in dayf:
            w_close, w_ema = w["Close"].to_numpy(), ema(w["Close"], dayf["weekly_ema"]).to_numpy()
    if "daily_ema" in dayf:
        d_ema = ema(daily["Close"], dayf["daily_ema"]).to_numpy()
    if "market_sma" in dayf or mt:
        if market is None:
            raise ValueError("market_sma filter / market_tighten need the market regime (lib.market.regime)")
        mkt_ok = market.astype(float).shift(1).reindex(days, method="ffill").fillna(0).to_numpy() > 0
    target = ex.get("target_pct")
    max_days = ex.get("max_days")
    ema_exit = set()
    if ex.get("ema_close"):
        etf = ex["ema_close"].get("timeframe", tf)
        eb = bars if etf == tf else resample(daily, etf)
        e_end = bar_end if etf == tf else np.searchsorted(days, eb.index, side="right")
        below = (eb["Close"] < ema(eb["Close"], ex["ema_close"].get("span", 61))).to_numpy()
        ema_exit = {e_end[i] for i in np.flatnonzero(below)}

    trades, free = [], 0
    for b in np.flatnonzero(sig):
        start = bar_end[b]
        if start < free or start >= len(days):
            continue
        end = bar_end[min(b + valid, len(bars) - 1)] if b + valid < len(bars) else len(days)
        level = bars["High"].iat[b]
        k = None
        for j in range(start, end):
            if d[j, 1] <= level:
                continue
            if need_weeks and last_w[j] < 0:
                continue
            if "weekly_ema" in dayf:
                lw = last_w[j]
                if np.isnan(w_ema[lw]) or w_close[lw] < w_ema[lw]:
                    continue
            if "market_sma" in dayf and not mkt_ok[j]:
                continue
            if "daily_ema" in dayf:
                if j == 0 or np.isnan(d_ema[j - 1]) or d[j - 1, 3] < d_ema[j - 1]:
                    continue
            k = j
            break
        if k is None:
            continue
        entry = max(level, d[k, 0])
        trail_amt = None
        if stype == "signal_low":
            stop = bars["Low"].iat[b]
        elif stype == "prev_week_low":
            stop = w_low[last_w[k]]
        elif stype == "trail_pct":
            trail_amt = entry * stop_cfg["pct"]
            stop = entry - trail_amt
        else:
            stop = -np.inf
        if stop >= entry:
            continue
        init_stop = stop if stype in ("signal_low", "prev_week_low") else None
        tgt = entry * (1 + target) if target is not None else np.inf
        exit_px = exit_day = None
        reason = "open"
        c = d[k, 3]
        if c <= stop:
            exit_px, exit_day, reason = c, k, "stop-entry-day"
        elif c >= tgt:
            exit_px, exit_day, reason = tgt, k, "target-entry-day"
        else:
            hh = max(entry, d[k, 1])
            for j in range(k + 1, len(days)):
                if trail_amt is not None:
                    stop = hh - trail_amt
                elif stop_cfg.get("trail") == "weekly_low" and last_w[j] > last_w[k]:
                    stop = max(stop, w_low[last_w[j]])
                if mt == "weekly_low" and not mkt_ok[j] and last_w[j] >= 0:
                    stop = max(stop, w_low[last_w[j]])
                o, h, l = d[j, 0], d[j, 1], d[j, 2]
                if mt == "exit" and not mkt_ok[j]:
                    exit_px, exit_day, reason = o, j, "market"; break
                if max_days is not None and (days[j] - days[k]).days >= max_days:
                    exit_px, exit_day, reason = o, j, "time"; break
                if o <= stop:
                    exit_px, exit_day, reason = o, j, "stop-gap"; break
                if o >= tgt:
                    exit_px, exit_day, reason = o, j, "target-gap"; break
                if j in ema_exit:
                    exit_px, exit_day, reason = o, j, "close<ema"; break
                if l <= stop:
                    exit_px, exit_day, reason = stop, j, "stop"; break
                if h >= tgt:
                    exit_px, exit_day, reason = tgt, j, "target"; break
                hh = max(hh, h)
        trades.append(Trade(symbol, bars.index[b], days[k], entry,
                            days[exit_day] if exit_day is not None else None,
                            exit_px, reason, init_stop))
        free = (exit_day + 1) if exit_day is not None else len(days)
    return trades
