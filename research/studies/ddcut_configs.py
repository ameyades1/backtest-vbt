"""Configs for the drawdown-cutting study on Sde394f26 (longshort/L_cap20_dd), point-in-time NIFTY 500.
    python studies/ddcut_configs.py && python -m lib.ids assign && python studies/ddcut.py
Test 1: NIFTY futures hedge on faster regimes (50/100-DMA, NIFTY 500 index)
Test 2: tighten or exit the longs when the market weakens (stops to weekly low, exit, half risk)
Test 3: bear-specific stock shorts (failed rally to a falling EMA, breakdowns; quick profits, 10-day time stop)
Test 4: gold for part of the capital (computed in studies/ddcut_report.py from the equity curve)
"""
import copy, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "studies"))
from longshort_configs import write, load
OUT = ROOT / "results" / "studies" / "ddcut"
OUT.mkdir(parents=True, exist_ok=True)
BASE = "longshort/L_cap20_dd"
U = ("NIFTY500_PIT",)
jobs = []
TG = {}                                               # short leg -> its target ("P1.5R" or None)


def var(name, desc, test, siz=None, stop=None, combine=None):
    c = load(BASE); c.pop("id", None)
    c["name"] = f"ddcut/{name}"; c["description"] = c["description"] + f" [{desc}]"
    c["sizing"].update(siz or {}); c["stop"].update(stop or {})
    if combine:
        c["combine"] = [{"config": f"strategies/ddcut/{s}.json", "universe": "NIFTY200", "target": TG[s]} for s in combine]
        c["sizing"]["max_positions"] = 12
        c["sizing"]["short"] = {"margin": 0.25, "roll": 0.001, "max": 4, "risk_mult": 0.5}
        c["costs"]["short_product"] = "futures"
    write(c, test, U, jobs)


# ---- test 1: faster hedges ----
for sma, ix, tag, where in [(50, None, "n50", "NIFTY below its 50-DMA"), (100, None, "n100", "NIFTY below its 100-DMA"),
                            (50, "^CRSLDX", "i50", "the NIFTY 500 index below its 50-DMA")]:
    for r in (0.5, 1.0):
        h = {"ratio": r, "sma": sma, **({"index": ix} if ix else {})}
        var(f"H_{tag}_r{int(r * 100)}", f"Short NIFTY futures = {r * 100:g}% of the long book while {where}.", "1-hedge",
            siz={"hedge": h})

# ---- test 2: tighten / exit the longs ----
for mode, sma, ix, tag, what in [("weekly_low", 50, None, "wl_n50", "stops raised to last week's low while NIFTY < 50-DMA"),
                                 ("weekly_low", 50, "^CRSLDX", "wl_i50", "stops raised to last week's low while NIFTY 500 < 50-DMA"),
                                 ("exit", 50, None, "exit_n50", "all longs sold when NIFTY closes below its 50-DMA"),
                                 ("exit", 100, "^CRSLDX", "exit_i100", "all longs sold when NIFTY 500 closes below its 100-DMA")]:
    var(f"T_{tag}", what.capitalize() + ".", "2-tighten",
        stop={"market_tighten": mode, "market_tighten_sma": sma, **({"market_tighten_index": ix} if ix else {})})
var("T_halfrisk_n50", "Half risk on new longs while NIFTY is below its 50-DMA.", "2-tighten",
    siz={"risk_rules": {"market_sma": {"days": 50, "mult": 0.5}}})
var("T_halfrisk_i50", "Half risk on new longs while NIFTY 500 breadth is weak (< 40% of stocks above 200-DMA).",
    "2-tighten", siz={"risk_rules": {"breadth": {"days": 200, "min": 40, "mult": 0.5}}})

# ---- test 3: bear-specific short legs (NIFTY 200 names, stock futures) ----
SH = load("longshort/S_w_st10_2")


def short(name, desc, setup, tf="W", regime=200, partial=True, tstop=10, st_mult=2):
    c = copy.deepcopy(SH); c.pop("id", None)
    c["name"] = f"ddcut/{name}"
    c["description"] = ("SHORT (stock futures, NIFTY 200 names), bear-market rules: " + desc +
                        f" Close below EMA61 on W and D; RSI < 50; new shorts only while NIFTY is below its "
                        f"{regime}-day average; stop at the previous week's high; "
                        + ("cover half at 1.5R; " if partial else "") +
                        f"cover if not 0.5R up after {tstop} days; cover when weekly Supertrend(10,{st_mult}) turns bullish.")
    c["timeframe"], c["setup"] = tf, setup
    c["filters"] = {"trend_ema": {"span": 61, "timeframes": ["W", "D"]}, "rsi_min": {"period": 14, "value": 50}}
    c["entry"]["day_filters"] = {"market_below_sma": regime}
    c["exits"]["targets_pct"] = ["P1.5R"] if partial else [None]
    c["exits"]["time_stop"] = {"days": tstop, "min_r": 0.5}
    c["exits"]["supertrend_exit_when_no_target"] = {"timeframe": "W", "period": 10, "mult": st_mult}
    c["sizing"]["max_positions"] = 4
    c["sizing"]["short"] = {"margin": 0.25, "roll": 0.001, "max": 4}
    write(c, "3-short-leg", ("NIFTY200",), jobs)
    TG[name] = c["exits"]["targets_pct"][0]
    return name


rally = {"type": "ema_touch", "span": 21}
brk = {"type": "donchian", "period": 10}
legs = [short("S_rally21", "weekly rally to a falling 21 EMA that fails (high reaches it, close back below).", rally),
        short("S_rally21_r50", "as S_rally21, but shorts allowed below the 50-DMA.", rally, regime=50),
        short("S_break10", "weekly close below the prior 10-week low.", brk),
        short("S_rally21_trail", "as S_rally21 without the half cover; 25-day time stop.", rally, partial=False, tstop=25)]
for s in legs:
    var(f"LS_{s[2:]}", f"Plus {s} shorts: 12 slots, at most 4 shorts, each at half the long risk.", "3-longshort",
        combine=[s])
var("LS_rally21_break10", "Plus S_rally21 and S_break10 shorts: 12 slots, at most 4 shorts at half risk.",
    "3-longshort", combine=["S_rally21", "S_break10"])
# ---- best of 1 + 2 together (gold is added in the report) ----
var("C_hedge_i50_breadth", "Short NIFTY futures = 100% of the long book while the NIFTY 500 index is below its 50-DMA; "
    "half risk on new longs while fewer than 40% of NIFTY 500 stocks are above their 200-DMA.", "5-combined",
    siz={"hedge": {"ratio": 1.0, "sma": 50, "index": "^CRSLDX"},
         "risk_rules": {"breadth": {"days": 200, "min": 40, "mult": 0.5}}})
json.dump(jobs, open(OUT / "jobs.json", "w"), indent=1)
print(len(jobs), "jobs")
