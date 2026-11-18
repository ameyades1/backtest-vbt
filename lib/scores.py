"""Ranking scores for portfolio.run(rank="score" | "score_tightest"). Each returns a day x symbol table
that uses only data known before the entry day (already shifted by one day). Higher = preferred.

Config: sizing.score = {"type": ..., "tiebreak": "mom12" (optional)}
  macd_turn       monthly MACD (12,26,9) of the last completed month:
                  2 = histogram rising while MACD < 0, 1 = rising with MACD >= 0, 0 = falling
  weekly_pattern  1 if a TA-Lib bullish pattern fired on any of the last `weeks` completed weekly candles
                  (patterns: CDLENGULFING, CDLHAMMER, CDLMORNINGSTAR, CDLPIERCING by default)
  macd_pattern    macd_turn + weekly_pattern (0..3)
  tiebreak mom12  adds 0.9 x the stock's percentile rank of 12-month return that day (ties broken by
                  relative strength; never outweighs one point)
"""
import numpy as np
import pandas as pd
from .indicators import resample, macd

PATTERNS = ["CDLENGULFING", "CDLHAMMER", "CDLMORNINGSTAR", "CDLPIERCING"]


def _to_days(v: pd.Series, daily: pd.DataFrame) -> pd.Series:
    """Candle values indexed by candle label -> daily series, known from the candle's last trading day,
    shifted one day so the entry day only sees completed candles."""
    days = daily.index
    v = v.copy()
    v.index = days[np.searchsorted(days, v.index, side="right") - 1]
    v = v[~v.index.duplicated(keep="last")]
    return v.reindex(days, method="ffill").shift(1)


def macd_turn(daily, tf="M", params=(12, 26, 9)):
    b = resample(daily, tf)
    m, _, h = macd(b["Close"], *params)
    v = pd.Series(np.where(h > h.shift(), np.where(m < 0, 2.0, 1.0), 0.0), index=b.index)
    v[h.isna() | h.shift().isna()] = np.nan
    return _to_days(v, daily)


def weekly_pattern(daily, patterns=PATTERNS, weeks=2):
    import talib
    w = resample(daily, "W")
    o, h, l, c = (w[x].to_numpy(dtype=float) for x in ("Open", "High", "Low", "Close"))
    hit = np.zeros(len(w), bool)
    for p in patterns:
        hit |= getattr(talib, p)(o, h, l, c) > 0
    v = pd.Series(hit.astype(float), index=w.index).rolling(weeks, min_periods=1).max()
    return _to_days(v, daily)


def table(cfg: dict, dailies: dict) -> pd.DataFrame:
    t = cfg["type"]
    parts = {"macd_turn": lambda d: macd_turn(d, cfg.get("timeframe", "M"), cfg.get("macd", (12, 26, 9))),
             "weekly_pattern": lambda d: weekly_pattern(d, cfg.get("patterns", PATTERNS), cfg.get("weeks", 2))}
    if t in parts:
        tab = pd.DataFrame({s: parts[t](d) for s, d in dailies.items()})
    elif t == "macd_pattern":
        tab = pd.DataFrame({s: parts["macd_turn"](d).fillna(0) + parts["weekly_pattern"](d).fillna(0)
                            for s, d in dailies.items()})
    else:
        raise ValueError(f"unknown score {t}")
    if cfg.get("tiebreak") == "mom12":
        c = pd.DataFrame({s: d["Close"] for s, d in dailies.items()}).reindex(tab.index).ffill()
        tab = tab.fillna(0) + 0.9 * (c / c.shift(252) - 1).shift(1).rank(axis=1, pct=True).fillna(0)
    return tab
