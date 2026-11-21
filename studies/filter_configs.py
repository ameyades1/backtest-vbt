"""Entry-filter study on Sde394f26 (longshort/L_cap20_dd, 1% risk), point-in-time NIFTY 500, no hedges.
    python studies/filter_configs.py [--stage 2 --index N --breadth B] && python -m lib.ids assign && python studies/filter.py
Stage 1: NIFTY 500 index above its N-day average (50..200) instead of NIFTY 50 above its 200-day; breadth entry
         filters (no new buys below 30..50% of members above their 200-day); NIFTY 50 controls; PIT breadth sizing.
Stage 2: combinations of the best index filter and breadth settings.
"""
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "studies"))
from longshort_configs import write, load
OUT = ROOT / "results" / "studies" / "filter"
OUT.mkdir(parents=True, exist_ok=True)
BASE = "longshort/L_cap20_dd"
U = ("NIFTY500_PIT",)


def var(name, desc, phase, jobs, idx=None, nifty=None, breadth=None):
    c = load(BASE); c.pop("id", None)
    c["name"] = f"filter/{name}"; c["description"] += f" [{desc}]"
    df = c["entry"]["day_filters"]
    if idx:
        df["market_sma"], df["market_index"] = idx, "^CRSLDX"
    if nifty:
        df["market_sma"] = nifty
    if breadth:
        c["sizing"]["risk_rules"] = {"breadth": {"days": 200, "pit": True, **breadth}}
    write(c, phase, U, jobs)


def stage1():
    jobs = []
    for n in (50, 75, 100, 150, 200):
        var(f"F_i{n}", f"Entry filter: NIFTY 500 index above its {n}-day average instead of NIFTY 50 above its 200-day.",
            "1-index", jobs, idx=n)
    for n in (50, 100):
        var(f"F_n{n}", f"Control: NIFTY 50 above its {n}-day average instead of its 200-day.", "1-nifty50", jobs, nifty=n)
    for b in (30, 35, 40, 45, 50):
        var(f"F_b{b}", f"Plus: no new buys while fewer than {b}% of that day's NIFTY 500 members are above their "
            f"200-day average.", "2-breadth", jobs, breadth={"min": b, "mult": 0.0})
    var("F_bh40", "Half risk on new buys while fewer than 40% of that day's NIFTY 500 members are above their 200-day "
        "average (S7a24cbc0 with point-in-time breadth).", "2-breadth", jobs, breadth={"min": 40, "mult": 0.5})
    var("F_steps", "Half risk below 50% breadth, no new buys below 30% (point-in-time members).", "2-breadth", jobs,
        breadth={"steps": [[50, 0.5], [30, 0.0]]})
    return jobs


def stage2(idx, b):
    jobs = []
    var(f"C_i{idx}_b{b}", f"NIFTY 500 index above its {idx}-day average and no new buys below {b}% breadth.", "3-combo",
        jobs, idx=idx, breadth={"min": b, "mult": 0.0})
    var(f"C_i{idx}_bh40", f"NIFTY 500 index above its {idx}-day average; half risk below 40% breadth.", "3-combo",
        jobs, idx=idx, breadth={"min": 40, "mult": 0.5})
    var(f"C_i{idx}_steps", f"NIFTY 500 index above its {idx}-day average; half risk below 50% breadth, none below 30%.",
        "3-combo", jobs, idx=idx, breadth={"steps": [[50, 0.5], [30, 0.0]]})
    return jobs


if __name__ == "__main__":
    a = argparse.ArgumentParser(); a.add_argument("--stage", type=int, default=1)
    a.add_argument("--index", type=int); a.add_argument("--breadth", type=int)
    a = a.parse_args()
    jobs = stage1() if a.stage == 1 else stage2(a.index, a.breadth)
    json.dump(jobs, open(OUT / f"jobs{a.stage}.json", "w"), indent=1)
    print(len(jobs), "jobs")
