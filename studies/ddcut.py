"""Runner for the drawdown-cutting study: python studies/ddcut.py [workers=3]  (resumable)."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "studies"))
import overnight as O
O.OUT = ROOT / "results" / "studies" / "ddcut"
O.LOG = O.OUT / "run.log"
if __name__ == "__main__":
    jobs = json.load(open(O.OUT / "jobs.json"))
    w = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    legs = [j for j in jobs if j["phase"] == "3-short-leg"]
    print(O.run_jobs(legs, w), O.run_jobs([j for j in jobs if j not in legs], w))
