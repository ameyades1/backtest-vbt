"""Overnight runner: every job in results/studies/overnight/jobs.json, in parallel, resumable.

    python studies/overnight_configs.py && python -m lib.ids assign
    nohup python studies/overnight.py --workers 5 --commit &

Steps: 1) all jobs (skips finished ones: results/<name>/<universe>/summary.csv newer than the config)
2) stage 2: the 5 best new-indicator strategies (2000-2018 CAGR / max drawdown, >= 50 trades) on 4 more universes
3) per-run PDFs, comparison table, scoreboard, overnight report  4) optional git commit + push.
Progress: results/studies/overnight/run.log
"""
import argparse, json, subprocess, sys, time, traceback
from collections import defaultdict
from multiprocessing import Pool
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "results" / "studies" / "overnight"
LOG = OUT / "run.log"
UNIS = ["NIFTY50", "NIFTY100", "MIDCAP150", "SMALLCAP250"]


def log(msg):
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')}  {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")


def out_dir(job):
    return ROOT / "results" / job["name"] / job["universe"].lower()


def done(job):
    s = out_dir(job) / "summary.csv"
    return s.exists() and s.stat().st_mtime > (ROOT / job["config"]).stat().st_mtime


_CACHE = {}


def work(group):
    import copy
    import run_strategy as R
    res = []
    for job in group:
        t0 = time.time()
        try:
            u = job["universe"]
            if u not in _CACHE:
                _CACHE[u] = R.load_dailies(u)
            cfg = json.load(open(ROOT / job["config"]))
            cfg = copy.deepcopy(cfg); cfg["universe"] = u
            tab = R.run(cfg, *_CACHE[u], out_dir(job))
            r = tab.loc["No target"] if "No target" in tab.index else tab.iloc[0]
            res.append((job, True, f"{time.time() - t0:5.0f}s  CAGR {r['CAGR %']:5.1f}  DD {r['Max DD %']:6.1f}  "
                                   f"trades {int(r['Trades taken'])}"))
        except Exception:
            res.append((job, False, traceback.format_exc().strip().splitlines()[-1]))
    return res


def run_jobs(jobs, workers):
    todo = [j for j in jobs if not done(j)]
    log(f"{len(jobs)} jobs, {len(jobs) - len(todo)} already done, {len(todo)} to run on {workers} workers")
    groups = defaultdict(list)                       # same base config + universe -> same worker (trade cache)
    for j in todo:
        base = j["name"].split("_size_")[0].split("_risk")[0].split("_slots")[0].split("_maxstop")[0]
        groups[(j["universe"], base)].append(j)
    groups = sorted(groups.values(), key=len, reverse=True)
    ok = bad = 0
    with Pool(workers) as pool:
        for res in pool.imap_unordered(work, groups):
            for job, good, msg in res:
                ok += good; bad += not good
                log(f"{'OK ' if good else 'ERR'} [{job['phase']}] {job['name']} @{job['universe']}  {msg}  "
                    f"({ok + bad}/{len(todo)})")
    return ok, bad


def stage2(jobs):
    import pandas as pd
    rows = []
    for j in jobs:
        if not j["phase"].startswith("4") or j["universe"] != "NIFTY500":
            continue
        d = out_dir(j)
        if not (d / "equity.csv").exists():
            continue
        e = pd.read_csv(d / "equity.csv", index_col=0, parse_dates=True)["No target"].dropna()[:"2018-12-31"]
        f = pd.read_csv(d / "fills_none.csv", parse_dates=["entry_date"])
        if len(f[f.entry_date <= "2018-12-31"]) < 50 or len(e) < 500:
            continue
        cg = ((e.iloc[-1] / e.iloc[0]) ** (365.25 / (e.index[-1] - e.index[0]).days) - 1) * 100
        dd = -((e / e.cummax()) - 1).min() * 100
        rows.append((cg / dd if dd > 0 else 0, j))
    top = [j for _, j in sorted(rows, key=lambda x: -x[0])[:5]]
    json.dump([j["name"] for j in top], open(OUT / "top5.json", "w"), indent=1)
    log("stage 2 top 5 (in-sample CAGR/DD): " + ", ".join(j["name"] for j in top))
    return [{**j, "phase": "5-universe", "universe": u} for j in top for u in UNIS]


def sh(cmd):
    log("$ " + cmd)
    r = subprocess.run(cmd, shell=True, cwd=ROOT, capture_output=True, text=True)
    tail = (r.stdout + r.stderr).strip().splitlines()[-3:]
    log(f"  exit {r.returncode}: " + " | ".join(tail))
    return r.returncode == 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--commit", action="store_true")
    a = ap.parse_args()
    t0 = time.time()
    jobs = json.load(open(OUT / "jobs.json"))
    log("==== overnight run start ====")
    ok, bad = run_jobs(jobs, a.workers)
    s2 = stage2(jobs)
    ok2, bad2 = run_jobs(s2, a.workers)
    json.dump(jobs + s2, open(OUT / "jobs_all.json", "w"), indent=1)
    log(f"runs finished: {ok + ok2} ok, {bad + bad2} failed, {(time.time() - t0) / 3600:.1f} h")
    dirs = sorted({str(out_dir(j).relative_to(ROOT)) for j in jobs + s2 if (out_dir(j) / "summary.csv").exists()})
    sh(".venv/bin/python report.py " + " ".join(dirs))
    sh(".venv/bin/python compare.py")
    sh(".venv/bin/python site.py")
    sh(".venv/bin/python studies/overnight_report.py")
    sh(".venv/bin/python -m lib.ids check")
    if a.commit:
        sh("git add -A lib studies strategies results docs report.py site.py run_strategy.py compare.py README.md "
           "requirements.txt")
        sh("git commit -q -m 'Overnight study: robustness, sizing, high win-rate fixes, new indicators' "
           "-m 'Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>'")
        sh("git push -q")
    log(f"==== done in {(time.time() - t0) / 3600:.1f} h ====")


if __name__ == "__main__":
    main()
