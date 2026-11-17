"""Ranking scores for portfolio.run(rank="score" | "score_tightest"). Each returns a day x symbol table
that uses only data known before the entry day (already shifted by one day).

Config: sizing.score = {"type": "macd_turn", "timeframe": "M", "macd": [12, 26, 9]}
  macd_turn  2 = histogram rising while MACD is below zero (turning up from a pullback)
             1 = histogram rising with MACD above zero
             0 = histogram falling
  Value of the last completed candle of `timeframe`.
"""
import numpy as np
import pandas as pd
from .indicators import resample, macd


def macd_turn(daily: pd.DataFrame, tf="M", params=(12, 26, 9)) -> pd.Series:
    b = resample(daily, tf)
    m, _, h = macd(b["Close"], *params)
    v = pd.Series(np.where(h > h.shift(), np.where(m < 0, 2.0, 1.0), 0.0), index=b.index)
    v[h.isna() | h.shift().isna()] = np.nan
    days = daily.index
    done = days[np.searchsorted(days, b.index, side="right") - 1]   # candle complete at its last trading day
    v.index = done
    return v.reindex(days, method="ffill").shift(1)


def table(cfg_score: dict, dailies: dict) -> pd.DataFrame:
    if cfg_score["type"] == "macd_turn":
        return pd.DataFrame({s: macd_turn(d, cfg_score.get("timeframe", "M"), cfg_score.get("macd", (12, 26, 9)))
                             for s, d in dailies.items()})
    raise ValueError(f"unknown score {cfg_score['type']}")
