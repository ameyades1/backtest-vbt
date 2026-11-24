"""Runner for the holding-period study: python studies/filter.py [workers=3]  (resumable)."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "studies"))
import overnight as O
O.OUT = ROOT / "results" / "studies" / "hold"
O.LOG = O.OUT / "run.log"
if __name__ == "__main__":
    print(O.run_jobs(json.load(open(O.OUT / "jobs.json")), int(sys.argv[1]) if len(sys.argv) > 1 else 3))
