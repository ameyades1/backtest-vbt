"""Variations of your choice S44984096 (stexit/A_flip_capentry) -> strategies/variants/*.json + results/studies/variants/jobs.json
    python studies/variants_configs.py && python -m lib.ids assign
"""
import copy, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
BASE = json.load(open(ROOT / "strategies" / "stexit" / "A_flip_capentry.json"))
OUT = ROOT / "strategies" / "variants"; OUT.mkdir(parents=True, exist_ok=True)
J = ROOT / "results" / "studies" / "variants"; J.mkdir(parents=True, exist_ok=True)
jobs = []


def var(name, group, desc, fn):
    c = copy.deepcopy(BASE); c.pop("id", None)
    c["name"] = f"variants/{name}"; c["description"] += f" [{desc}]"
    fn(c)
    p = OUT / f"{name}.json"
    old = json.load(open(p)) if p.exists() else {}
    if old.get("id"):
        c["id"] = old["id"]
    json.dump(c, open(p, "w"), indent=2, ensure_ascii=False)
    jobs.append({"name": c["name"], "group": group, "desc": desc, "config": str(p.relative_to(ROOT))})


for r in (0.75, 1.0, 1.5, 2.0):
    for k in (5, 7, 10):
        if (r, k) == (1.0, 10):
            continue
        var(f"r{r:g}_s{k}".replace(".", "p"), "1-grid", f"{r:g}% risk, {k} slots",
            lambda c, r=r, k=k: c["sizing"].update(risk_pct=r, max_positions=k))
var("cash0", "2-cash", "Idle cash earns nothing (no liquid fund)", lambda c: c["sizing"].pop("cash"))
var("zerodha", "3-costs", "Zerodha costs: zero delivery brokerage (statutory charges + 0.1% slippage)",
    lambda c: c["costs"].update(broker="discount"))
for t in (5, 10):
    var(f"liq{t}", "4-liquidity", f"Only stocks trading at least Rs {t} crore a day (60-day median)",
        lambda c, t=t: c["sizing"].update(min_turnover_cr=t))
for n, m in ((10, 2), (10, 4), (14, 3)):
    var(f"st{n}_{m}", "5-supertrend", f"Weekly Supertrend({n}, {m}) for the exit instead of (10, 3)",
        lambda c, n=n, m=m: c["exits"]["supertrend_exit_when_no_target"].update(period=n, mult=m))
var("rank_rs", "6-ranking", "Same-day signals ranked by 6-month relative strength instead of tightest stop",
    lambda c: c["sizing"].update(rank="score", score={"type": "mom", "months": 6}))
json.dump(jobs, open(J / "jobs.json", "w"), indent=1)
print(len(jobs), "configs")
