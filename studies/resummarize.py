"""Recompute per-trade summary fields in every results/*/*/*/summary.csv from saved fills + equity (no reruns)."""
import sys, glob
from pathlib import Path
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
import pandas as pd
from lib import portfolio
n = 0
for sp in glob.glob(str(__import__("pathlib").Path(__file__).resolve().parents[1] / "results" / "**" / "summary.csv"), recursive=True):
    d = Path(sp).parent
    if not (d / "equity.csv").exists():
        continue
    S = pd.read_csv(sp, index_col=0)
    if "Trades taken" not in S.columns or "Worst trade (Rs)" not in S.columns:
        continue
    EQ = pd.read_csv(d / "equity.csv", index_col=0, parse_dates=True)
    ok = True
    for col in S.index:
        tag = "none" if col == "No target" else col.split()[1].rstrip("%")
        fp = d / f"fills_{tag}.csv"
        if not fp.exists() or col not in EQ:
            ok = False; continue
        fd = pd.read_csv(fp)
        if fd.empty:
            continue
        for k, v in portfolio.trade_stats(fd, EQ[col].dropna()).items():
            S.loc[col, k] = v
    S = S.drop(columns=["Worst trade % of capital"], errors="ignore")
    S.to_csv(sp); n += 1
    if not ok:
        print("partial", d)
print("updated", n)
