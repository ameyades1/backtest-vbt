"""Runner for the entry-filter study: python studies/filter.py jobs1.json [workers=3]  (resumable)."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "studies"))
import overnight as O
O.OUT = ROOT / "results" / "studies" / "filter"
O.LOG = O.OUT / "run.log"
if __name__ == "__main__":
    print(O.run_jobs(json.load(open(O.OUT / sys.argv[1])), int(sys.argv[2]) if len(sys.argv) > 2 else 3))
