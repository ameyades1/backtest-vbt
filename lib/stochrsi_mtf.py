"""Monthly pullback: triple-timeframe EMA61 trend + RSI > 50 + Stochastic RSI cross from oversold.

Signal, evaluated at each monthly close (bar b):
    monthly Close > EMA61(monthly)
    last completed week (ending on or before the month's last trading day): Close > EMA61(weekly)
    month's last daily Close > EMA61(daily)
    RSI(14, Wilder) on monthly closes > 50
    Stochastic RSI (14 RSI, 14 stoch, K=3, D=3, scale 0-100) on monthly bars:
        K crosses above D this month (K[b-1] <= D[b-1], K[b] > D[b]) and D[b] < oversold (30)
Entry    buy-stop above the signal candle's High during the next month; fill max(level, Open).
Stop     stop="candle": signal candle's Low (fixed).
         stop="prev_week": Low of the last completed week before the entry day (fixed).
Exit     fixed target_pct, or (target_pct=None) next open after a monthly close below EMA61.
Fill rules as lib/ema61.py: gaps fill at Open, stop before target on the same day,
entry day checks only the Close.
"""
import numpy as np
import pandas as pd
from .ema61 import Trade, resample

SPAN = 61


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    diff = close.diff()
    up = diff.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-diff.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return 100 - 100 / (1 + up / dn)


def stoch_rsi(close: pd.Series, n_rsi=14, n_stoch=14, k=3, d=3):
    r = rsi(close, n_rsi)
    lo, hi = r.rolling(n_stoch).min(), r.rolling(n_stoch).max()
    st = (r - lo) / (hi - lo) * 100
    K = st.rolling(k).mean()
    return r, K, K.rolling(d).mean()


def signal_mask(daily: pd.DataFrame, oversold: float = 30.0, rsi_min: float = 50.0):
    m, w = resample(daily, "M"), resample(daily, "W")
    ema_m = m["Close"].ewm(span=SPAN, adjust=False, min_periods=SPAN).mean()
    ema_w = w["Close"].ewm(span=SPAN, adjust=False, min_periods=SPAN).mean()
    ema_d = daily["Close"].ewm(span=SPAN, adjust=False, min_periods=SPAN).mean()
    days = daily.index
    # last daily bar of each month, last week ending on/before it
    last_day = np.searchsorted(days, m.index, side="right") - 1
    w_last = np.searchsorted(w.index, days[last_day], side="right") - 1
    w_ok = np.where(w_last >= 0, (w["Close"] > ema_w).to_numpy()[np.clip(w_last, 0, None)], False)
    d_ok = (daily["Close"] > ema_d).to_numpy()[last_day]
    r, K, D = stoch_rsi(m["Close"])
    cross = (K > D) & (K.shift() <= D.shift()) & (D < oversold)
    sig = (m["Close"] > ema_m).to_numpy() & w_ok & d_ok & (r > rsi_min).to_numpy() & cross.to_numpy()
    return m, ema_m, sig


def simulate(daily: pd.DataFrame, symbol: str, target_pct: float | None = None,
             oversold: float = 30.0, stop: str = "candle") -> list[Trade]:
    m, ema_m, sig = signal_mask(daily, oversold)
    if len(m) <= SPAN:
        return []
    days = daily.index
    d = daily[["Open", "High", "Low", "Close"]].to_numpy()
    m_end = np.searchsorted(days, m.index, side="right")
    w = resample(daily, "W")
    w_end = np.searchsorted(days, w.index, side="right")          # first day after each week
    last_w = np.searchsorted(w_end, np.arange(len(days)), side="right") - 1
    w_low = w["Low"].to_numpy()
    ema_exit_days = {m_end[i] for i in np.flatnonzero((m["Close"] < ema_m).to_numpy())}
    trades, free = [], 0
    for b in np.flatnonzero(sig):
        start = m_end[b]
        if start < free or start >= len(days):
            continue
        end = m_end[b + 1] if b + 1 < len(m) else len(days)
        level = m["High"].iat[b]
        hit = np.flatnonzero(d[start:end, 1] > level)
        if not len(hit):
            continue
        k = start + hit[0]
        entry = max(level, d[k, 0])
        if stop == "prev_week":
            if last_w[k] < 0:
                continue
            sl = w_low[last_w[k]]
        else:
            sl = m["Low"].iat[b]
        if sl >= entry:
            continue
        tgt = entry * (1 + target_pct) if target_pct is not None else np.inf
        exit_px = exit_day = None
        reason = "open"
        c = d[k, 3]
        if c <= sl:
            exit_px, exit_day, reason = c, k, "stop-entry-day"
        elif c >= tgt:
            exit_px, exit_day, reason = tgt, k, "target-entry-day"
        else:
            for j in range(k + 1, len(days)):
                o, h, l = d[j, 0], d[j, 1], d[j, 2]
                if o <= sl:
                    exit_px, exit_day, reason = o, j, "stop-gap"; break
                if o >= tgt:
                    exit_px, exit_day, reason = o, j, "target-gap"; break
                if target_pct is None and j in ema_exit_days:
                    exit_px, exit_day, reason = o, j, "close<ema"; break
                if l <= sl:
                    exit_px, exit_day, reason = sl, j, "stop"; break
                if h >= tgt:
                    exit_px, exit_day, reason = tgt, j, "target"; break
        trades.append(Trade(symbol, m.index[b], days[k], entry,
                            days[exit_day] if exit_day is not None else None,
                            exit_px, reason, sl))
        free = (exit_day + 1) if exit_day is not None else len(days)
    return trades


def simulate_weekly(daily: pd.DataFrame, symbol: str, target_pct: float | None = None,
                    oversold: float = 30.0, rsi_min: float = 50.0) -> list[Trade]:
    """Same setup on weekly candles. Signal at week close b:
        last *completed* month Close > monthly EMA61, weekly Close > weekly EMA61,
        week's last daily Close > daily EMA61, weekly RSI > 50,
        weekly StochRSI K crosses above D with D < oversold.
    Entry buy-stop above signal week High during the next week; stop = signal week Low.
    No target: exit next open after a weekly close below weekly EMA61."""
    w, m = resample(daily, "W"), resample(daily, "M")
    if len(w) <= SPAN:
        return []
    days = daily.index
    ema_w = w["Close"].ewm(span=SPAN, adjust=False, min_periods=SPAN).mean()
    ema_m = m["Close"].ewm(span=SPAN, adjust=False, min_periods=SPAN).mean()
    ema_d = daily["Close"].ewm(span=SPAN, adjust=False, min_periods=SPAN).mean()
    w_last = np.searchsorted(days, w.index, side="right") - 1        # last daily bar of each week
    m_last = np.searchsorted(days, m.index, side="right") - 1        # last daily bar of each month
    mi = np.searchsorted(m_last, w_last, side="right") - 1            # last month completed by then
    m_ok = np.where(mi >= 0, (m["Close"] > ema_m).to_numpy()[np.clip(mi, 0, None)], False)
    d_ok = (daily["Close"] > ema_d).to_numpy()[w_last]
    r, K, D = stoch_rsi(w["Close"])
    cross = (K > D) & (K.shift() <= D.shift()) & (D < oversold)
    sig = (w["Close"] > ema_w).to_numpy() & m_ok & d_ok & (r > rsi_min).to_numpy() & cross.to_numpy()

    d = daily[["Open", "High", "Low", "Close"]].to_numpy()
    w_end = w_last + 1
    ema_exit_days = {w_end[i] for i in np.flatnonzero((w["Close"] < ema_w).to_numpy())}
    trades, free = [], 0
    for b in np.flatnonzero(sig):
        start = w_end[b]
        if start < free or start >= len(days):
            continue
        end = w_end[b + 1] if b + 1 < len(w) else len(days)
        level, sl = w["High"].iat[b], w["Low"].iat[b]
        hit = np.flatnonzero(d[start:end, 1] > level)
        if not len(hit):
            continue
        k = start + hit[0]
        entry = max(level, d[k, 0])
        if sl >= entry:
            continue
        tgt = entry * (1 + target_pct) if target_pct is not None else np.inf
        exit_px = exit_day = None
        reason = "open"
        c = d[k, 3]
        if c <= sl:
            exit_px, exit_day, reason = c, k, "stop-entry-day"
        elif c >= tgt:
            exit_px, exit_day, reason = tgt, k, "target-entry-day"
        else:
            for j in range(k + 1, len(days)):
                o, h, l = d[j, 0], d[j, 1], d[j, 2]
                if o <= sl:
                    exit_px, exit_day, reason = o, j, "stop-gap"; break
                if o >= tgt:
                    exit_px, exit_day, reason = o, j, "target-gap"; break
                if target_pct is None and j in ema_exit_days:
                    exit_px, exit_day, reason = o, j, "close<ema"; break
                if l <= sl:
                    exit_px, exit_day, reason = sl, j, "stop"; break
                if h >= tgt:
                    exit_px, exit_day, reason = tgt, j, "target"; break
        trades.append(Trade(symbol, w.index[b], days[k], entry,
                            days[exit_day] if exit_day is not None else None,
                            exit_px, reason, sl))
        free = (exit_day + 1) if exit_day is not None else len(days)
    return trades
