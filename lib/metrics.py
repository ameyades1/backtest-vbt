"""Per-trade metrics shared by site.py (HTML scoreboard) and report.py (run PDFs), so both show the same numbers.
Fills are first merged into trades (lib.portfolio.trades): position-cap trims and partial legs count once."""
import numpy as np
import pandas as pd
from . import portfolio


def streak(losses) -> int:
    best = cur = 0
    for x in losses:
        cur = cur + 1 if x else 0
        best = max(best, cur)
    return best


def compute(fills: pd.DataFrame, summary: pd.Series, start: str) -> dict | None:
    """fills: a fills_*.csv frame; summary: that exit's row of summary.csv; start: config period start."""
    f = fills.copy()
    sd = f["side"].fillna(1) if "side" in f else 1
    f["risk"] = f.qty * (f.entry - f.stop).abs() if "stop" in f else np.nan
    f["gross"] = f.qty * (f.exit - f.entry) * sd
    t = portfolio.trades(f)
    g = f.assign(entry_date=pd.to_datetime(f.entry_date), side=sd).groupby(portfolio.TRADE_KEYS, sort=False)
    t["risk"] = g["risk"].sum().to_numpy()
    t["gross"] = g["gross"].sum().to_numpy()
    c = t[~t.open].sort_values("exit_date")
    if c.empty:
        return None
    win, loss = c.ret[c.ret > 0], c.ret[c.ret <= 0]
    yrs = (c.exit_date.max() - pd.Timestamp(start)).days / 365.25
    costs, gsum = (c.gross - c.pnl).sum(), c.gross.sum()
    r = c.pnl / c.risk.replace(0, np.nan)
    rs = r.dropna()
    sqn = rs.mean() / rs.std() * np.sqrt(min(len(rs), 100)) if len(rs) > 1 and rs.std() > 0 else np.nan
    return {"sqn": sqn, "sqn_all": rs.mean() / rs.std() * np.sqrt(len(rs)) if len(rs) > 1 and rs.std() > 0 else np.nan,
            "r_sd": rs.std(), "_closed": c,
            "win": (c.ret > 0).mean() * 100, "avg_ret": c.ret.mean(), "avg_rs": c.pnl.mean(),
            "avg_win": win.mean() if len(win) else np.nan, "avg_loss": loss.mean() if len(loss) else np.nan,
            "payoff": win.mean() / -loss.mean() if len(win) and len(loss) else np.nan,
            "exp_r": r.mean(), "cagr": summary["CAGR %"], "mdd": summary["Max DD %"],
            "mar": summary["CAGR %"] / -summary["Max DD %"] if summary["Max DD %"] else np.nan,
            "trades": len(c), "tpy": len(c) / yrs if yrs > 0 else np.nan, "streak": streak(list(c.pnl <= 0)),
            "hold": float(summary["Median hold days"]), "deployed": summary["Avg deployed %"],
            "skipped": int(summary["Signals skipped"]),
            "cost_pct": costs / gsum * 100 if gsum > 0 else np.inf,
            "gross_win": c.pnl[c.pnl > 0].sum(), "gross_loss": c.pnl[c.pnl <= 0].sum(),
            "pf": c.pnl[c.pnl > 0].sum() / -c.pnl[c.pnl <= 0].sum() if (c.pnl <= 0).any() else np.inf,
            "n_win": int((c.pnl > 0).sum()), "n_loss": int((c.pnl <= 0).sum()), "open": int(t.open.sum())}
