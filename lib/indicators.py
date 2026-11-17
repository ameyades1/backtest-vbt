"""Indicators and bar helpers shared by every strategy."""
import pandas as pd

RESAMPLE = {"D": None, "W": "W-FRI", "M": "ME"}


def resample(daily: pd.DataFrame, tf: str) -> pd.DataFrame:
    if tf == "D":
        return daily
    return daily.resample(RESAMPLE[tf]).agg(
        {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
    ).dropna()


def ema(close: pd.Series, span: int) -> pd.Series:
    return close.ewm(span=span, adjust=False, min_periods=span).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    """Wilder RSI."""
    diff = close.diff()
    up = diff.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    dn = (-diff.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return 100 - 100 / (1 + up / dn)


def stoch_rsi(close: pd.Series, n_rsi=14, n_stoch=14, k=3, d=3):
    """Returns (rsi, %K, %D) on a 0-100 scale."""
    r = rsi(close, n_rsi)
    lo, hi = r.rolling(n_stoch).min(), r.rolling(n_stoch).max()
    K = ((r - lo) / (hi - lo) * 100).rolling(k).mean()
    return r, K, K.rolling(d).mean()


def macd(close: pd.Series, fast=12, slow=26, signal=9):
    """Returns (macd line, signal line, histogram)."""
    line = ema(close, fast) - ema(close, slow)
    sig = line.ewm(span=signal, adjust=False, min_periods=signal).mean()
    return line, sig, line - sig
