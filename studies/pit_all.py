"""Run every strategy whose default universe is NIFTY500_PIT (resumable).  python studies/pit_all.py [workers]"""
import glob, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "studies"))
import overnight as O
O.OUT = ROOT / "results" / "studies" / "pit"
O.LOG = O.OUT / "run_all.log"
if __name__ == "__main__":
    jobs = []
    for f in sorted(glob.glob(str(ROOT / "strategies" / "**" / "*.json"), recursive=True)):
        c = json.load(open(f))
        if c.get("universe") == "NIFTY500_PIT":
            jobs.append({"phase": "pit-all", "config": str(Path(f).relative_to(ROOT)), "universe": "NIFTY500_PIT",
                         "name": c["name"]})
    json.dump(jobs, open(O.OUT / "jobs_all.json", "w"), indent=1)
    print(O.run_jobs(jobs, int(sys.argv[1]) if len(sys.argv) > 1 else 5))
