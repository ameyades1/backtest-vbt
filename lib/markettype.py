"""Van Tharp-style market types: direction (bull / sideways / bear) x volatility (quiet / volatile), per day.

Broad market = NIFTY 50 (Sensex scaled in before NIFTY's history, as lib.engine.nifty_close), same series all runs.
  Direction:  13-week (65 trading-day) change of the index: above +5% bull, below -5% bear, otherwise sideways.
  Volatility: 20-day standard deviation of daily returns, against its own rolling 3-year median
              (volatile if above). Rolling, so no future data is used.
A day's type uses closes up to the previous day, so a trade is filed under the type known when it was bought.
"""
import numpy as np
import pandas as pd

TYPES = [f"{d} {v}" for d in ("Bull", "Sideways", "Bear") for v in ("quiet", "volatile")]
_T = None


def types() -> pd.Series:
    global _T
    if _T is None:
        from .engine import nifty_close
        n = nifty_close().dropna()
        ch = n.pct_change(65)
        vol = n.pct_change().rolling(20).std()
        med = vol.rolling(756, min_periods=252).median()
        d = np.where(ch > .05, "Bull", np.where(ch < -.05, "Bear", "Sideways"))
        v = np.where(vol > med, "volatile", "quiet")
        t = pd.Series([f"{a} {b}" for a, b in zip(d, v)], index=n.index)
        _T = t[ch.notna() & med.notna()].shift(1).dropna()
    return _T


def breakdown(equity: pd.Series, trades: pd.DataFrame) -> list[list[str]]:
    """equity: daily equity; trades: closed trades with entry_date, pnl, risk (from lib.metrics.closed)."""
    t = types()
    e = equity.dropna()
    r = e.pct_change().dropna()
    ty = t.reindex(r.index, method="ffill")
    nf = __import__("lib.engine", fromlist=["x"]).nifty_close().reindex(e.index, method="ffill").pct_change().reindex(r.index)
    et = t.reindex(pd.to_datetime(trades.entry_date), method="ffill").to_numpy()
    R = (trades.pnl / trades.risk.replace(0, np.nan)).to_numpy()
    rows = [["Market type", "Days %", "Strategy / yr", "NIFTY / yr", "Trades", "Win %", "Expectancy R", "Share of R"]]
    tot = np.nansum(R)
    for k in TYPES:
        m = (ty == k).to_numpy()
        n = m.sum()
        ann = lambda x: (np.prod(1 + x[m]) ** (252 / n) - 1) * 100 if n else np.nan
        sel = et == k
        rr = R[sel]
        rows.append([k, f"{n / len(r) * 100:.0f}", f"{ann(r.to_numpy()):+.1f}%", f"{ann(nf.fillna(0).to_numpy()):+.1f}%",
                     f"{sel.sum()}", f"{(rr > 0).mean() * 100:.0f}" if len(rr) else "–",
                     f"{np.nanmean(rr):+.2f}" if len(rr) else "–",
                     f"{np.nansum(rr) / tot * 100:.0f}%" if len(rr) and tot else "–"])
    return rows
