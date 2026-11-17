"""Legacy engine kept only for tests/test_engine_parity.py; use lib/engine.py.
Triple-timeframe EMA61 breakout with a weekly stop.

Signal   monthly candle with Open < EMA61(monthly) < Close.
Entry    during the next month, on the first day where
           High > breakout High                              (buy-stop; fill max(level, Open))
           last COMPLETED week's Close >= weekly EMA61       (weekly filter)
           previous day's Close >= daily EMA61               (daily filter)
Stop     Low of the last completed week before entry.
           stop_mode='fixed' : never moves
           stop_mode='trail' : after each completed week, raised to that week's Low (never lowered)
Exit     fixed target_pct, or (target_pct=None) next open after a monthly close below EMA61;
         optional max_days time exit at the open of the first day >= max_days after entry.
Daily-bar fill rules as in lib/ema61.py: gaps fill at Open, stop before target on the same day,
entry day checks only the Close.
"""
import numpy as np
import pandas as pd
from ..ema61 import Trade, resample

SPAN = 61


def simulate(daily: pd.DataFrame, symbol: str, target_pct: float | None = None,
             stop_mode: str = "fixed", filters: bool = True,
             max_days: int | None = None) -> list[Trade]:
    m = resample(daily, "M")
    w = resample(daily, "W")
    if len(m) <= SPAN:
        return []
    ema_m = m["Close"].ewm(span=SPAN, adjust=False, min_periods=SPAN).mean()
    ema_w = w["Close"].ewm(span=SPAN, adjust=False, min_periods=SPAN).mean()
    ema_d = daily["Close"].ewm(span=SPAN, adjust=False, min_periods=SPAN).mean().to_numpy()
    brk = ((m["Open"] < ema_m) & (ema_m < m["Close"])).to_numpy()
    below_m = (m["Close"] < ema_m).to_numpy()

    days = daily.index
    d = daily[["Open", "High", "Low", "Close"]].to_numpy()
    m_end = np.searchsorted(days, m.index, side="right")          # first day after month
    w_end = np.searchsorted(days, w.index, side="right")          # first day after week
    # for each day: index of last completed week (week whose end-day < today)
    last_w = np.searchsorted(w_end, np.arange(len(days)), side="right") - 1
    w_low, w_close, w_ema = w["Low"].to_numpy(), w["Close"].to_numpy(), ema_w.to_numpy()
    ema_exit_days = {m_end[i] for i in np.flatnonzero(below_m)}

    trades, free = [], 0
    for b in np.flatnonzero(brk):
        start = m_end[b]
        if start < free or start >= len(days) or b + 1 > len(m):
            continue
        end = m_end[b + 1] if b + 1 < len(m) else len(days)
        level = m["High"].iat[b]
        k = None
        for j in range(start, end):
            if d[j, 1] <= level:
                continue
            lw = last_w[j]
            if lw < 0:
                continue
            if filters:
                if np.isnan(w_ema[lw]) or w_close[lw] < w_ema[lw]:
                    continue
                if j == 0 or np.isnan(ema_d[j - 1]) or d[j - 1, 3] < ema_d[j - 1]:
                    continue
            k = j
            break
        if k is None:
            continue
        entry = max(level, d[k, 0])
        stop = w_low[last_w[k]]
        if stop >= entry:                                         # no valid risk
            continue
        init_stop = stop
        tgt = entry * (1 + target_pct) if target_pct is not None else np.inf
        exit_px = exit_day = None
        reason = "open"
        c = d[k, 3]
        if c <= stop:
            exit_px, exit_day, reason = c, k, "stop-entry-day"
        elif c >= tgt:
            exit_px, exit_day, reason = tgt, k, "target-entry-day"
        else:
            for j in range(k + 1, len(days)):
                if stop_mode == "trail":
                    lw = last_w[j]
                    if lw > last_w[k]:
                        stop = max(stop, w_low[lw])
                o, h, l = d[j, 0], d[j, 1], d[j, 2]
                if max_days is not None and (days[j] - days[k]).days >= max_days:
                    exit_px, exit_day, reason = o, j, "time"; break
                if o <= stop:
                    exit_px, exit_day, reason = o, j, "stop-gap"; break
                if o >= tgt:
                    exit_px, exit_day, reason = o, j, "target-gap"; break
                if target_pct is None and j in ema_exit_days and j > k:
                    exit_px, exit_day, reason = o, j, "close<ema"; break
                if l <= stop:
                    exit_px, exit_day, reason = stop, j, "stop"; break
                if h >= tgt:
                    exit_px, exit_day, reason = tgt, j, "target"; break
        trades.append(Trade(symbol, m.index[b], days[k], entry,
                            days[exit_day] if exit_day is not None else None,
                            exit_px, reason, init_stop))
        free = (exit_day + 1) if exit_day is not None else len(days)
    return trades
