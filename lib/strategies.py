"""Strategies: take wide price frames, return (entries, exits) boolean frames."""
import pandas as pd
import vectorbt as vbt


def sma_cross(close: pd.DataFrame, fast: int = 50, slow: int = 200):
    f = vbt.MA.run(close, fast, short_name="fast")
    s = vbt.MA.run(close, slow, short_name="slow")
    return f.ma_crossed_above(s), f.ma_crossed_below(s)


def donchian_breakout(close: pd.DataFrame, high: pd.DataFrame, low: pd.DataFrame,
                      entry_n: int = 55, exit_n: int = 20):
    upper = high.rolling(entry_n).max().shift(1)
    lower = low.rolling(exit_n).min().shift(1)
    return close > upper, close < lower
