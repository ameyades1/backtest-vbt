"""EMA61 breakout with Sharekhan-style trailing stop-loss, simulated on daily bars.

Signal (on the signal timeframe, e.g. monthly):
    breakout candle: Open < EMA61 < Close           (EMA on that timeframe's closes)
Entry:
    buy-stop at the breakout candle's High, valid for the next `valid_bars` bars.
    Filled on the first daily bar whose High > level, at max(level, Open) (gap-up -> open).
Exit (one of):
    trail_pct=X : Sharekhan trailing SL. Trail amount is fixed in RUPEES at entry
                  (X% of entry price), stop = highest high since entry - trail.
                  Ratchets up only; today's high moves the stop from tomorrow
                  (conservative, avoids intrabar order ambiguity).
                  Fill at stop, or at Open if the day gaps below the stop.
    trail_pct=None : baseline - exit at next day's open after a signal-timeframe
                  close below EMA61.
On the entry day the stop is only checked against the close (unknown intraday order).
Assumes the stop-limit always fills (gap -> open price).
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd

RESAMPLE = {"D": None, "W": "W-FRI", "M": "ME"}


def resample(daily: pd.DataFrame, tf: str) -> pd.DataFrame:
    if tf == "D":
        return daily
    return daily.resample(RESAMPLE[tf]).agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
    ).dropna()


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


def signals(daily: pd.DataFrame, tf: str = "M", span: int = 61):
    """Return (bars, ema, breakout mask) on the signal timeframe."""
    bars = resample(daily, tf)
    ema = bars["Close"].ewm(span=span, adjust=False, min_periods=span).mean()
    brk = (bars["Open"] < ema) & (ema < bars["Close"])
    return bars, ema, brk


def simulate(daily: pd.DataFrame, symbol: str, tf: str = "M", span: int = 61,
             trail_pct: float | None = 0.10, valid_bars: int = 1,
             stop_at_low: bool = False, target_pct: float | None = None,
             max_days: int | None = None) -> list[Trade]:
    """stop_at_low / target_pct: fixed stop at the breakout candle's Low and/or a fixed
    target at entry*(1+target_pct). Used instead of the trailing stop (trail_pct ignored).
    With stop_at_low and no target, the exit falls back to close<EMA61 (plus the stop).
    max_days: time exit - sell at the open of the first day >= max_days calendar days after entry."""
    bars, ema, brk = signals(daily, tf, span)
    d = daily[["Open", "High", "Low", "Close"]].to_numpy()
    days = daily.index
    # map each signal bar to the daily index range of the bars that follow it
    bar_end = np.searchsorted(days, bars.index, side="right")      # first day after bar
    below = (bars["Close"] < ema).to_numpy()
    trades, i = [], 0                                                # i = first free day
    for b in np.flatnonzero(brk.to_numpy()):
        start = bar_end[b]
        if start < i or start >= len(days):
            continue                                                 # in a trade / no data
        stop_bar = min(b + valid_bars, len(bars) - 1)
        end = bar_end[stop_bar] if b + valid_bars < len(bars) else len(days)
        level = bars["High"].iat[b]
        hit = np.flatnonzero(d[start:end, 1] > level)
        if not len(hit):
            continue
        k = start + hit[0]
        entry = max(level, d[k, 0])
        exit_px = exit_day = None
        reason = "open"
        if stop_at_low or target_pct is not None:
            stop = bars["Low"].iat[b] if stop_at_low else -np.inf
            tgt = entry * (1 + target_pct) if target_pct is not None else np.inf
            ema_exit = set(bar_end[sb] for sb in np.flatnonzero(below[b + 1:]) + b + 1) \
                if target_pct is None else set()
            c = d[k, 3]
            if c <= stop:                                            # entry day: close only
                exit_px, exit_day, reason = c, k, "stop-entry-day"
            elif c >= tgt:
                exit_px, exit_day, reason = tgt, k, "target-entry-day"
            else:
                for j in range(k + 1, len(days)):
                    o, h, l = d[j, 0], d[j, 1], d[j, 2]
                    if max_days is not None and (days[j] - days[k]).days >= max_days:
                        exit_px, exit_day, reason = o, j, "time"; break
                    if o <= stop:
                        exit_px, exit_day, reason = o, j, "stop-gap"; break
                    if o >= tgt:
                        exit_px, exit_day, reason = o, j, "target-gap"; break
                    if j in ema_exit:
                        exit_px, exit_day, reason = o, j, "close<ema"; break
                    if l <= stop:                                    # stop first if both
                        exit_px, exit_day, reason = stop, j, "stop"; break
                    if h >= tgt:
                        exit_px, exit_day, reason = tgt, j, "target"; break
        elif trail_pct is not None:
            trail = entry * trail_pct                                # fixed rupees
            stop = entry - trail
            if d[k, 3] <= stop:                                      # entry day: close only
                exit_px, exit_day, reason = d[k, 3], k, "stop-entry-day"
            else:
                hh = max(entry, d[k, 1])
                for j in range(k + 1, len(days)):
                    stop = hh - trail
                    o, h, l = d[j, 0], d[j, 1], d[j, 2]
                    if o <= stop:
                        exit_px, exit_day, reason = o, j, "stop-gap"
                        break
                    if l <= stop:
                        exit_px, exit_day, reason = stop, j, "stop"
                        break
                    hh = max(hh, h)
        else:
            sig_bars = np.flatnonzero(below[b + 1:]) + b + 1
            for sb in sig_bars:
                j = bar_end[sb]
                if j > k and j < len(days):
                    exit_px, exit_day, reason = d[j, 0], j, "close<ema"
                    break
        trades.append(Trade(symbol, bars.index[b], days[k], entry,
                            days[exit_day] if exit_day is not None else None,
                            exit_px, reason,
                            bars["Low"].iat[b] if stop_at_low else None))
        i = (exit_day + 1) if exit_day is not None else len(days)
    return trades


def equity(trades: list[Trade], daily: pd.DataFrame, fee: float, slip: float,
           cash: float = 100_000.0) -> tuple[pd.Series, list[float]]:
    """Daily equity of one stock sleeve (all-in per trade) and net return per trade."""
    close = daily["Close"]
    eq = pd.Series(np.nan, index=close.index)
    rets, cur = [], cash
    pos = {t.entry_date: t for t in trades}
    in_trade, shares, t = False, 0.0, None
    for day, c in close.items():
        if not in_trade and day in pos:
            t = pos[day]
            buy = t.entry * (1 + slip) * (1 + fee)
            shares, start_cash, in_trade = cur / buy, cur, True
        if in_trade and t.exit_date == day:
            cur = shares * t.exit * (1 - slip) * (1 - fee)
            rets.append(cur / start_cash - 1)
            in_trade = False
        eq[day] = shares * c if in_trade else cur
    if in_trade:                                   # mark open trade to market
        rets.append(shares * close.iloc[-1] * (1 - slip) * (1 - fee) / start_cash - 1)
    return eq, rets


def stats(eq: pd.Series, rets: list[float], trades: list | None = None,
          stock_days: int | None = None) -> dict:
    eq = eq.dropna()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    dr = eq.pct_change().dropna()
    r = np.array(rets) if rets else np.array([np.nan])
    return {
        "CAGR %": ((eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1) * 100,
        "Max DD %": (eq / eq.cummax() - 1).min() * 100,
        "Sharpe": dr.mean() / dr.std() * np.sqrt(252) if dr.std() > 0 else np.nan,
        "Trades": len(rets),
        "Win %": (r > 0).mean() * 100,
        "Avg trade %": np.nanmean(r) * 100,
        "Avg win %": np.nanmean(r[r > 0]) * 100 if (r > 0).any() else np.nan,
        "Avg loss %": np.nanmean(r[r <= 0]) * 100 if (r <= 0).any() else np.nan,
        "Median trade %": np.nanmedian(r) * 100,
        **_holding(trades, eq.index[-1], stock_days),
    }


def _holding(trades, last, stock_days):
    if not trades:
        return {}
    held = np.array([((t.exit_date or last) - t.entry_date).days for t in trades])
    out = {"Avg hold days": held.mean(), "Median hold days": float(np.median(held))}
    if stock_days:
        out["Exposure %"] = held.sum() / stock_days * 100
    return out
