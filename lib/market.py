"""Market regime: is the broad market above its N-day simple moving average?

NIFTY 50 (^NSEI) is used wherever its N-day average exists (Yahoo history starts Sept 2007, so from
mid-2008 for N=200). Before that the BSE Sensex (^BSESN, history from 1997) stands in; the two agree
on 97.6% of days since 2008. Value on day t uses the close of day t; callers shift it so the
decision for a day uses the previous close.
"""
import pandas as pd
from . import data


def regime(days: int = 200) -> pd.Series:
    c = data.load(["^NSEI", "^BSESN"])["Close"]
    out = None
    for sym in ["^BSESN", "^NSEI"]:
        s = c[sym].dropna()
        sma = s.rolling(days).mean()
        r = (s > sma)[sma.notna()]
        out = r if out is None else pd.concat([out[out.index < r.index[0]], r])
    return out.rename(f"above_{days}dma")


def source(days: int = 200) -> pd.Series:
    """Which index decided the regime on each day."""
    c = data.load(["^NSEI"])["Close"]["^NSEI"].dropna()
    first = c.rolling(days).mean().dropna().index[0]
    r = regime(days)
    return pd.Series(["Sensex" if d < first else "NIFTY 50" for d in r.index], index=r.index)
