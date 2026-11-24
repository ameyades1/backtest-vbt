"""The five indicators S44984096 uses. Each value at bar t uses only bars up to t."""
import numpy as np
import pandas as pd


def to_weekly(daily: pd.DataFrame) -> pd.DataFrame:
    """Weekly candles ending Friday (weeks without trading are dropped)."""
    return _bars(daily, "W-FRI")


def to_monthly(daily: pd.DataFrame) -> pd.DataFrame:
    """Monthly candles, labelled with the calendar month-end date."""
    return _bars(daily, "ME")


def _bars(daily, rule):
    agg = {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
    return daily.resample(rule).agg(agg).dropna()


def ema(close: pd.Series, span: int) -> pd.Series:
    """Exponential average; empty until `span` bars exist."""
    return close.ewm(span=span, adjust=False, min_periods=span).mean()


def sma(close: pd.Series, n: int) -> pd.Series:
    return close.rolling(n, min_periods=n).mean()


def rsi(close: pd.Series, n: int = 14) -> pd.Series:
    """Wilder RSI (as TradingView, Chartink, Zerodha)."""
    diff = close.diff()
    up = diff.clip(lower=0).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    down = (-diff.clip(upper=0)).ewm(alpha=1 / n, adjust=False, min_periods=n).mean()
    return 100 - 100 / (1 + up / down)


def stoch_rsi(close: pd.Series, n_rsi=14, n_stoch=14, k=3, d=3):
    """Stochastic RSI (14, 14, 3, 3) on a 0-100 scale -> (%K, %D)."""
    r = rsi(close, n_rsi)
    low, high = r.rolling(n_stoch).min(), r.rolling(n_stoch).max()
    K = ((r - low) / (high - low) * 100).rolling(k).mean()
    return K, K.rolling(d).mean()


def atr(bars: pd.DataFrame, n: int) -> pd.Series:
    """Wilder average true range."""
    prev = bars["Close"].shift()
    tr = pd.concat([bars["High"] - bars["Low"], (bars["High"] - prev).abs(), (bars["Low"] - prev).abs()],
                   axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def supertrend_bullish(bars: pd.DataFrame, n: int = 10, mult: float = 3.0) -> pd.Series:
    """True while Supertrend(n, mult) is bullish (False until ATR exists)."""
    a = atr(bars, n).to_numpy()
    mid = ((bars["High"] + bars["Low"]) / 2).to_numpy()
    c = bars["Close"].to_numpy()
    upper, lower = mid + mult * a, mid - mult * a
    bull = np.zeros(len(c), bool)
    fu, fl = upper.copy(), lower.copy()
    for i in range(1, len(c)):
        if np.isnan(a[i]):
            continue
        fu[i] = upper[i] if (np.isnan(fu[i - 1]) or upper[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lower[i] if (np.isnan(fl[i - 1]) or lower[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        bull[i] = (c[i] > fu[i - 1]) if not bull[i - 1] else not (c[i] < fl[i - 1])
    s = pd.Series(bull, index=bars.index)
    s[np.isnan(a)] = False
    return s
