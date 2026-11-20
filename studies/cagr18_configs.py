"""Configs for the "CAGR 18%" study (blocks A-G). Idempotent; keeps existing IDs.

    python studies/cagr18_configs.py && python -m lib.ids assign
    -> strategies/**/*_c18_*.json, strategies/rotation/*.json, results/studies/cagr18/jobs.json

Bases: MAIN = S7c315ace (monthly StochRSI pullback, EMA61 exit)
       ST   = S3f9854aa (same, NIFTY 200-DMA entry filter, weekly Supertrend exit)
"""
import copy, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "studies" / "cagr18"
OUT.mkdir(parents=True, exist_ok=True)
load = lambda n: json.load(open(ROOT / "strategies" / f"{n}.json"))
MAIN = "stochrsi_pullback/monthly_prev_week_stop"
ST = "stochrsi_pullback/monthly_prev_week_stop_nifty200_exit_supertrend"
BRK = "breakout/weekly_donchian55_nifty200"
jobs = []


def write(c, block, universes=("NIFTY500",)):
    c = copy.deepcopy(c)
    p = ROOT / "strategies" / f"{c['name']}.json"
    c.pop("id", None)
    if p.exists() and "id" in json.load(open(p)):
        c = {"id": json.load(open(p))["id"], **c}
    p.parent.mkdir(parents=True, exist_ok=True)
    json.dump(c, open(p, "w"), indent=2); open(p, "a").write("\n")
    for u in universes:
        jobs.append({"phase": block, "config": f"strategies/{c['name']}.json", "universe": u, "name": c["name"]})


def var(base, suffix, desc, fn):
    c = copy.deepcopy(load(base))
    c["name"] = f"{base}_c18_{suffix}"
    c["description"] = c["description"].rstrip() + f" [{desc}]"
    c["exits"]["targets_pct"] = [None]
    fn(c)
    return c


def upd(path, **kw):
    """fn that sets c[path...] keys: upd('sizing', risk_pct=1.5)."""
    def f(c):
        c.setdefault(path, {}).update(copy.deepcopy(kw))
    return f


def chain(*fs):
    def f(c):
        for g in fs:
            g(c)
    return f


BASES = {"main": MAIN, "st": ST}

# ---- baselines (targets trimmed to none, same as every variant) ----
for k, b in BASES.items():
    write(var(b, "base", "Baseline for the CAGR-18 study: no fixed target.", lambda c: None), "0-base")

# ---- A: 2xATR stop + Supertrend exit grid (on ST: market filter + Supertrend exit) ----
for m in [1.5, 2, 2.5, 3]:
    for per, mu in [(10, 2), (10, 3), (14, 3)]:
        def f(c, m=m, per=per, mu=mu):
            c["stop"] = {"type": "atr", "mult": m, "period": 14}
            c["exits"]["supertrend_exit_when_no_target"] = {"timeframe": "W", "period": per, "mult": mu}
        write(var(ST, f"atr{m:g}_st{per}_{mu}", f"Stop {m:g} x ATR(14) below entry; exit on weekly Supertrend({per},{mu}).", f),
              "A-combo")

# ---- B: more capital at work ----
for k, b in BASES.items():
    for slots, risk in [(6, 1.0), (10, 1.0), (8, 1.5), (10, 1.5), (12, 1.0)]:
        write(var(b, f"slots{slots}_r{risk:g}", f"{slots} slots, {risk:g}% risk per trade.",
                  upd("sizing", max_positions=slots, risk_pct=risk)), "B-slots")
    write(var(b, "cash_liquid", "Idle cash earns 6.5% a year (liquid fund).", upd("sizing", cash={"type": "liquid", "rate": 6.5})),
          "B-cash")
    write(var(b, "cash_nifty", "Idle cash held in a NIFTY 50 ETF (price return less 0.1% a year).",
              upd("sizing", cash={"type": "nifty", "cost": 0.1})), "B-cash")
    for at_r in [1, 2]:
        write(var(b, f"pyr{at_r}r", f"Add half a position at +{at_r}R; stop to break-even first.",
                  upd("exits", pyramid={"at_r": at_r, "weight": 0.5})), "B-pyramid")

# ---- C: let winners run / recycle capital ----
for k, b in BASES.items():
    write(var(b, "chandelier3", "Chandelier trail: highest high - 3 x ATR(14).",
              upd("stop", trail="atr", trail_mult=3.0, period=14)), "C-exit")
    for days in [15, 25, 40]:
        write(var(b, f"tstop{days}", f"Time stop: out at the next open if not +0.5R after {days} calendar days.",
                  upd("exits", time_stop={"days": days, "min_r": 0.5})), "C-time")
write(var(ST, "p2r", "Sell half at 2R; the rest by the Supertrend exit.",
          lambda c: c["exits"].update(targets_pct=["P2R"])), "C-exit")

# ---- D: better selection ----
for k, b in BASES.items():
    for t, mo in [("mom", 6), ("mom", 12), ("rs_sector", 6)]:
        write(var(b, f"rank_{t}{mo}", f"Rank same-day signals by {t} ({mo} months), then tightest stop.",
                  upd("sizing", rank="score_tightest", score={"type": t, "months": mo})), "D-rank")
    write(var(b, "sectop4", "Only stocks in the 4 strongest sectors (median 6-month return).",
              upd("sizing", sector_top={"n": 4, "months": 6})), "D-sector")
    write(var(b, "seccap2", "At most 2 open positions per sector.", upd("sizing", sector_cap=2)), "D-sector")
    write(var(b, "near_high10", "Signal only within 10% of the 52-week high.",
              upd("filters", near_high={"timeframe": "D", "pct": 10, "period": 252})), "D-filter")
    write(var(b, "vol12", "Signal month volume above 1.2 x the 12-month average.",
              upd("filters", volume={"timeframe": "M", "mult": 1.2, "period": 12})), "D-filter")

# ---- E: regime sizing ----
for k, b in BASES.items():
    write(var(b, "reg_sma50", "Half risk while NIFTY is below its 50-day average.",
              upd("sizing", risk_rules={"market_sma": {"days": 50, "mult": 0.5}})), "E-regime")
    write(var(b, "reg_breadth50", "Half risk while under 50% of the universe is above its 200-day average.",
              upd("sizing", risk_rules={"breadth": {"days": 200, "min": 50, "mult": 0.5}})), "E-regime")
    write(var(b, "reg_vix25", "No new trades while India VIX > 25.",
              upd("sizing", risk_rules={"vix": {"max": 25, "mult": 0.0}})), "E-regime")

# ---- F1: second engine in the same portfolio ----
for k, b in BASES.items():
    write(var(b, "plus_brk2r", "Shares capital with the weekly Donchian-55 breakout (2R target, 200-DMA filter); 10 slots.",
              chain(lambda c: c.update(combine=[{"config": f"strategies/{BRK}.json", "target": "2R"}]),
                    upd("sizing", max_positions=10))), "F-combine")
write(var(MAIN, "plus_st", "Shares capital with the Supertrend-exit version (S3f9854aa); 10 slots.",
          chain(lambda c: c.update(combine=[{"config": f"strategies/{ST}.json"}]), upd("sizing", max_positions=10))),
      "F-combine")

# ---- F2: momentum rotation ----
ROT = {"name": "rotation/momentum_top10", "universe": "NIFTY200", "period": {"start": "2000-01-01"}, "timeframe": "M",
       "exits": {"targets_pct": [None]},
       "sizing": {"capital": 100000, "risk_pct": 0, "max_positions": 10, "rank": "tightest"},
       "costs": {"broker": "sharekhan", "product": "delivery", "slippage_pct": 0.1}}
SET = {"type": "momentum_rotation", "top": 10, "lookback": 252, "skip": 21, "buffer": 2, "sma": 200, "market_sma": 200}
for nm, chg, d in [("momentum_top10", {}, "Monthly rotation into the 10 strongest stocks by 12-1 month return, above their "
                   "200-day average; held while in the top 20; no new buys while NIFTY 50 is below its 200-day average."),
                   ("momentum_top20", {"top": 20}, "As momentum_top10 with 20 stocks."),
                   ("momentum_top10_6m", {"lookback": 126}, "As momentum_top10 with 6-1 month momentum."),
                   ("momentum_top10_nomkt", {"market_sma": None}, "As momentum_top10 without the NIFTY 200-DMA filter.")]:
    c = copy.deepcopy(ROT); c["name"] = f"rotation/{nm}"; c["description"] = d
    c["setup"] = {**SET, **chg}
    write(c, "F-rotation", ("NIFTY50", "NIFTY100", "NIFTY200", "NIFTY500"))

# ---- G: stack the capital levers ----
for k, b in BASES.items():
    write(var(b, "stack", "Stack: 10 slots at 1% risk, idle cash in a liquid fund at 6.5%, 25-day time stop.",
              chain(upd("sizing", max_positions=10, risk_pct=1.0, cash={"type": "liquid", "rate": 6.5}),
                    upd("exits", time_stop={"days": 25, "min_r": 0.5}))), "G-stack")
    write(var(b, "stack_rs", "Stack + rank by stock/sector relative strength (6 months).",
              chain(upd("sizing", max_positions=10, risk_pct=1.0, cash={"type": "liquid", "rate": 6.5},
                        rank="score_tightest", score={"type": "rs_sector", "months": 6}),
                    upd("exits", time_stop={"days": 25, "min_r": 0.5}))), "G-stack")
    write(var(b, "stack_brk", "Stack + the Donchian-55 breakout (2R) sharing capital, 12 slots.",
              chain(upd("sizing", max_positions=12, risk_pct=1.0, cash={"type": "liquid", "rate": 6.5}),
                    upd("exits", time_stop={"days": 25, "min_r": 0.5}),
                    lambda c: c.update(combine=[{"config": f"strategies/{BRK}.json", "target": "2R"}]))), "G-stack")

# ---- H: compound the risk (x current equity instead of starting capital) ----
for k, b in BASES.items():
    write(var(b, "compound", "Risk per trade = 1% of current equity (compounding).", upd("sizing", compound=True)),
          "H-compound", ("NIFTY500", "NIFTY50", "NIFTY100", "MIDCAP150", "SMALLCAP250"))
    write(var(b, "stack_compound", "Stack (10 slots, liquid-fund cash, 25-day time stop) with compounding risk.",
              chain(upd("sizing", max_positions=10, risk_pct=1.0, cash={"type": "liquid", "rate": 6.5}, compound=True),
                    upd("exits", time_stop={"days": 25, "min_r": 0.5}))),
          "H-compound", ("NIFTY500", "NIFTY50", "NIFTY100", "MIDCAP150", "SMALLCAP250"))
    write(var(b, "stack_rs_compound", "Stack + RS ranking with compounding risk.",
              chain(upd("sizing", max_positions=10, risk_pct=1.0, cash={"type": "liquid", "rate": 6.5}, compound=True,
                        rank="score_tightest", score={"type": "rs_sector", "months": 6}),
                    upd("exits", time_stop={"days": 25, "min_r": 0.5}))),
          "H-compound", ("NIFTY500", "NIFTY50", "NIFTY100", "MIDCAP150", "SMALLCAP250"))
    write(var(b, "compound_r1.5", "1.5% of current equity per trade, 10 slots.",
              upd("sizing", compound=True, risk_pct=1.5, max_positions=10)),
          "H-compound", ("NIFTY500", "NIFTY50", "NIFTY100", "MIDCAP150", "SMALLCAP250"))

json.dump(jobs, open(OUT / "jobs.json", "w"), indent=1)
print(f"{len({j['name'] for j in jobs})} configs, {len(jobs)} jobs")
