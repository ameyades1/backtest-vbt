"""Holding-period study on S1704ed9f (filter/F_i200: Sde394f26 with the NIFTY 500 index market filter), 1% risk.
    python studies/hold_configs.py && python -m lib.ids assign && python studies/hold.py
Test 1: time-stop check day (10..50, none) x required gain at the check (0, 0.25R, 0.5R, 1R)
Test 3: trailing exit: weekly Supertrend(10, 2.5 / 4), monthly Supertrend(10, 3), 3 x ATR trailing stop
Test 4: holding caps: sell after 90 / 180 / 365 calendar days
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "studies"))
from longshort_configs import write, load
OUT = ROOT / "results" / "studies" / "hold"
OUT.mkdir(parents=True, exist_ok=True)
BASE = "filter/F_i200"
U = ("NIFTY500_PIT",)
jobs = []


def var(name, desc, phase, ex=None, stop=None):
    c = load(BASE); c.pop("id", None)
    c["name"] = f"hold/{name}"; c["description"] += f" [{desc}]"
    for k, v in (ex or {}).items():
        c["exits"][k] = v
    c["stop"].update(stop or {})
    write(c, phase, U, jobs)


for d in (10, 15, 20, 25, 35, 50):
    for r in (0, 0.25, 0.5, 1.0):
        if (d, r) == (25, 0.5):
            continue                                              # = S1704ed9f itself
        var(f"T{d}_r{str(r).replace('.', '')}", f"Time stop: sell if not {r:g}R up after {d} days (instead of 0.5R / 25).",
            "1-timestop", ex={"time_stop": {"days": d, "min_r": r}})
var("T_none", "No time stop.", "1-timestop", ex={"time_stop": None})
var("X_st25", "Exit: weekly Supertrend(10, 2.5) instead of (10, 3): tighter trail.", "3-trail",
    ex={"supertrend_exit_when_no_target": {"timeframe": "W", "period": 10, "mult": 2.5}})
var("X_st4", "Exit: weekly Supertrend(10, 4) instead of (10, 3): looser trail.", "3-trail",
    ex={"supertrend_exit_when_no_target": {"timeframe": "W", "period": 10, "mult": 4}})
var("X_mst3", "Exit: monthly Supertrend(10, 3) instead of weekly: much looser trail.", "3-trail",
    ex={"supertrend_exit_when_no_target": {"timeframe": "M", "period": 10, "mult": 3}})
var("X_atr3", "Plus a trailing stop at the highest high since entry minus 3 x ATR(14).", "3-trail",
    stop={"trail": "atr", "trail_mult": 3.0, "period": 14})
for m in (90, 180, 365):
    var(f"Cap{m}", f"Holding cap: sell at the next open {m} days after entry.", "4-cap", ex={"max_days": m})
json.dump(jobs, open(OUT / "jobs.json", "w"), indent=1)
print(len(jobs), "jobs")
