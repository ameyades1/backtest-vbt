"""Runner for the long/short study: python studies/longshort.py jobs12.json  (resumable, 6 workers)."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "studies"))
import overnight as O
O.OUT = ROOT / "results" / "studies" / "longshort"
O.LOG = O.OUT / "run.log"
if __name__ == "__main__":
    print(O.run_jobs(json.load(open(O.OUT / sys.argv[1])), int(sys.argv[2]) if len(sys.argv) > 2 else 6))
