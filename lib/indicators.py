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


# ---- additional indicators (all causal: value at bar t uses bars <= t) ----
def sma(close: pd.Series, n: int) -> pd.Series:
    return close.rolling(n, min_periods=n).mean()


def atr(bars: pd.DataFrame, n: int = 14) -> pd.Series:
    """Wilder ATR."""
    pc = bars["Close"].shift()
    tr = pd.concat([bars["High"] - bars["Low"], (bars["High"] - pc).abs(), (bars["Low"] - pc).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False, min_periods=n).mean()


def adx(bars: pd.DataFrame, n: int = 14):
    """Returns (ADX, +DI, -DI), Wilder smoothing."""
    up, dn = bars["High"].diff(), -bars["Low"].diff()
    pdm = up.where((up > dn) & (up > 0), 0.0)
    mdm = dn.where((dn > up) & (dn > 0), 0.0)
    a = atr(bars, n)
    pdi = 100 * pdm.ewm(alpha=1 / n, adjust=False, min_periods=n).mean() / a
    mdi = 100 * mdm.ewm(alpha=1 / n, adjust=False, min_periods=n).mean() / a
    dx = 100 * (pdi - mdi).abs() / (pdi + mdi)
    return dx.ewm(alpha=1 / n, adjust=False, min_periods=n).mean(), pdi, mdi


def supertrend(bars: pd.DataFrame, n: int = 10, mult: float = 3.0) -> pd.Series:
    """True while the Supertrend is bullish."""
    import numpy as np
    a = atr(bars, n).to_numpy()
    hl2 = ((bars["High"] + bars["Low"]) / 2).to_numpy()
    c = bars["Close"].to_numpy()
    ub, lb = hl2 + mult * a, hl2 - mult * a
    bull = np.zeros(len(c), bool)
    fu, fl = ub.copy(), lb.copy()
    for i in range(1, len(c)):
        if np.isnan(a[i]):
            continue
        fu[i] = ub[i] if (np.isnan(fu[i - 1]) or ub[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lb[i] if (np.isnan(fl[i - 1]) or lb[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        bull[i] = (c[i] > fu[i - 1]) if not bull[i - 1] else not (c[i] < fl[i - 1])
    s = pd.Series(bull, index=bars.index)
    s[pd.isna(a)] = False
    return s


def williams_r(bars: pd.DataFrame, n: int = 14) -> pd.Series:
    hh, ll = bars["High"].rolling(n).max(), bars["Low"].rolling(n).min()
    return -100 * (hh - bars["Close"]) / (hh - ll)


def cci(bars: pd.DataFrame, n: int = 20) -> pd.Series:
    tp = (bars["High"] + bars["Low"] + bars["Close"]) / 3
    m = tp.rolling(n).mean()
    md = tp.rolling(n).apply(lambda x: abs(x - x.mean()).mean(), raw=True)
    return (tp - m) / (0.015 * md)


def ichimoku_above_cloud(bars: pd.DataFrame) -> pd.Series:
    """Close above both spans of the cloud plotted at the current bar (spans computed 26 bars earlier)."""
    h, l = bars["High"], bars["Low"]
    tenkan = (h.rolling(9).max() + l.rolling(9).min()) / 2
    kijun = (h.rolling(26).max() + l.rolling(26).min()) / 2
    a = ((tenkan + kijun) / 2).shift(26)
    b = ((h.rolling(52).max() + l.rolling(52).min()) / 2).shift(26)
    return (bars["Close"] > a) & (bars["Close"] > b)


def obv(bars: pd.DataFrame) -> pd.Series:
    import numpy as np
    return (np.sign(bars["Close"].diff()).fillna(0) * bars["Volume"]).cumsum()


def bollinger(close: pd.Series, n: int = 20, k: float = 2.0):
    m, sd = close.rolling(n).mean(), close.rolling(n).std()
    return m - k * sd, m, m + k * sd
