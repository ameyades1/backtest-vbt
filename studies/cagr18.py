"""Runner for the CAGR-18 study: all jobs in results/studies/cagr18/jobs.json, then stage 2 (the 8 best
NIFTY 500 swing variants by 2000-2018 CAGR with in-sample drawdown better than -40%) on 4 more universes.
Resumable; reuses studies/overnight.py's pool.  nohup python studies/cagr18.py --workers 6 &
"""
import argparse, json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "studies"))
import overnight as O
O.OUT = ROOT / "results" / "studies" / "cagr18"
O.LOG = O.OUT / "run.log"


def stage2(jobs, n=8):
    import pandas as pd
    rows = []
    for j in jobs:
        if j["universe"] != "NIFTY500" or j["name"].startswith("rotation/"):
            continue
        d = O.out_dir(j)
        if not (d / "equity.csv").exists():
            continue
        e = pd.read_csv(d / "equity.csv", index_col=0, parse_dates=True).iloc[:, 0].dropna()[:"2018-12-31"]
        cg = ((e.iloc[-1] / e.iloc[0]) ** (365.25 / (e.index[-1] - e.index[0]).days) - 1) * 100
        dd = ((e / e.cummax()) - 1).min() * 100
        if dd > -40:
            rows.append((cg, j))
    top = [j for _, j in sorted(rows, key=lambda x: -x[0])[:n]]
    json.dump([j["name"] for j in top], open(O.OUT / "top8.json", "w"), indent=1)
    O.log("stage 2 (in-sample CAGR, DD > -40%): " + ", ".join(j["name"] for j in top))
    return [{**j, "phase": "S2-universe", "universe": u} for j in top for u in O.UNIS]


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--workers", type=int, default=6); a = ap.parse_args()
    t0 = time.time()
    jobs = json.load(open(O.OUT / "jobs.json"))
    O.log("==== cagr18 run start ====")
    ok, bad = O.run_jobs(jobs, a.workers)
    s2 = stage2(jobs)
    ok2, bad2 = O.run_jobs(s2, a.workers)
    json.dump(jobs + s2, open(O.OUT / "jobs_all.json", "w"), indent=1)
    O.log(f"==== runs finished: {ok + ok2} ok, {bad + bad2} failed, {(time.time() - t0) / 3600:.1f} h ====")
