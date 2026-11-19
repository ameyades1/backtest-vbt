"""Generate the strategy configs for the overnight study (phases 1-4). Idempotent: rewrites the same files.

    python studies/overnight_configs.py        -> strategies/**.json + results/studies/overnight/jobs.json

Each config gets a permanent ID afterwards (python -m lib.ids assign). Jobs = (config, universe).
"""
import copy, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "studies" / "overnight"
OUT.mkdir(parents=True, exist_ok=True)

load = lambda n: json.load(open(ROOT / "strategies" / f"{n}.json"))
MAIN = "stochrsi_pullback/monthly_prev_week_stop"
EMA = "ema61_breakout/monthly_weekly_stop"
HIWIN = "ema61_breakout/monthly_candle_stop"                       # Se32915a5, the 74% win-rate strategy
MKT = " No new entries while NIFTY 50 is below its 200-day average (Sensex before mid-2008)."
jobs, made = [], []


def write(c, phase, universes=("NIFTY500",)):
    c = copy.deepcopy(c)
    old = ROOT / "strategies" / f"{c['name']}.json"
    if old.exists() and "id" in json.load(open(old)):
        c = {"id": json.load(open(old))["id"], **{k: v for k, v in c.items() if k != "id"}}
    else:
        c.pop("id", None)
    old.parent.mkdir(parents=True, exist_ok=True)
    json.dump(c, open(old, "w"), indent=2); open(old, "a").write("\n")
    made.append(c["name"])
    for u in universes:
        jobs.append({"phase": phase, "config": f"strategies/{c['name']}.json", "universe": u, "name": c["name"]})


def variant(base, suffix, desc, **changes):
    c = copy.deepcopy(load(base))
    c["name"] = f"{base}_{suffix}"
    c["description"] = c["description"].rstrip() + " " + desc
    for k, v in changes.items():
        c[k] = v
    return c


# ---------------- phase 1: robustness of the main strategy ----------------
for b in [MAIN, MAIN + "_nifty200"]:
    for u in ["NIFTY50", "NIFTY100", "MIDCAP150", "SMALLCAP250"]:
        jobs.append({"phase": "1-universe", "config": f"strategies/{b}.json", "universe": u, "name": b})
    c0 = load(b)
    for span in [34, 55, 89, 144]:                                   # Fibonacci EMA spans (61 = current)
        f = copy.deepcopy(c0["filters"]); f["trend_ema"]["span"] = span
        ex = copy.deepcopy(c0["exits"]); ex["ema_close_when_no_target"]["span"] = span
        write(variant(b, f"ema{span}", f"[Sensitivity: EMA{span} instead of EMA61 for the trend filter and the exit.]",
                      filters=f, exits=ex), "1-ema")
    for os_ in [20, 40]:
        s = copy.deepcopy(c0["setup"]); s["oversold"] = os_
        write(variant(b, f"os{os_}", f"[Sensitivity: StochRSI oversold level {os_} instead of 30.]", setup=s), "1-params")
    for rv in [40, 60]:
        f = copy.deepcopy(c0["filters"]); f["rsi_min"]["value"] = rv
        write(variant(b, f"rsi{rv}", f"[Sensitivity: monthly RSI > {rv} instead of 50.]", filters=f), "1-params")
    for dl in [1, 2]:
        e = copy.deepcopy(c0["entry"]); e["delay_days"] = dl
        write(variant(b, f"delay{dl}", f"[Sensitivity: entry {dl} trading day(s) later than the signal allows.]",
                      entry=e), "1-params")

# ---------------- phase 2: sizing rules ----------------
SIZE = {"dd": ({"dd_rule": {"halve": 10, "pause": 15, "pause_days": 21}},
               "Sizing: half risk after a 10% fall from the equity high until a new high; no new trades for 21 trading days on reaching 15%."),
        "mkt": ({"risk_rules": {"market_sma": {"days": 200, "mult": 0.5}}},
                "Sizing: half risk while NIFTY 50 is below its 200-day average."),
        "breadth": ({"risk_rules": {"breadth": {"days": 200, "min": 40, "mult": 0.5}}},
                    "Sizing: half risk while fewer than 40% of the universe trade above their 200-day average."),
        "vix": ({"risk_rules": {"vix": {"max": 25, "mult": 0.5}}},
                "Sizing: half risk while India VIX is above 25 (VIX from 2008)."),
        "ddmkt": ({"dd_rule": {"halve": 10, "pause": 15, "pause_days": 21}, "risk_rules": {"market_sma": {"days": 200, "mult": 0.5}}},
                  "Sizing: drawdown rule (half at 10%, 21-day pause at 15%) and half risk below the NIFTY 200-day average.")}
for b in [MAIN, MAIN + "_nifty200", EMA, EMA + "_nifty200"]:
    for k, (sz, txt) in SIZE.items():
        s = {**load(b)["sizing"], **sz}
        write(variant(b, f"size_{k}", txt, sizing=s), "2-sizing")
for b in [MAIN, MAIN + "_nifty200"]:
    for r in [0.75, 1.5, 2.0]:
        s = {**load(b)["sizing"], "risk_pct": r}
        write(variant(b, f"risk{str(r).replace('.', 'p')}", f"Sizing: {r:g}% risk per trade.", sizing=s), "2-risk")

# ---------------- phase 3: the high win-rate strategy (Se32915a5) ----------------
RT = [None, "1R", "1.5R", "2R", "3R", "P1.5R"]
for b in [HIWIN, HIWIN + "_nifty200"]:
    c0 = load(b)
    for n in [12, 16, 20, 24]:
        write(variant(b, f"slots{n}", f"Sizing: {n} slots.", sizing={**c0["sizing"], "max_positions": n}), "3-slots")
    for m in [8, 10, 12, 15]:
        write(variant(b, f"maxstop{m}", f"Only signals with a stop within {m}% of entry.",
                      sizing={**c0["sizing"], "max_stop_pct": m}), "3-stopwidth")
    write(variant(b, "rtargets", "Targets set as multiples of the initial risk (1R-3R); P1.5R = half at 1.5R, rest by "
                  "the trend exit.", exits={**c0["exits"], "targets_pct": RT}), "3-rtargets")
    write(variant(b, "combo", "16 slots, stops within 12%, R-multiple targets.",
                  sizing={**c0["sizing"], "max_positions": 16, "max_stop_pct": 12},
                  exits={**c0["exits"], "targets_pct": RT}), "3-combo")

# ---------------- phase 4: new indicators ----------------
T4 = [None, "2R", "P1.5R"]
m200 = load(MAIN + "_nifty200")
for nm, flt, txt in [
        ("trend_adx", {"adx": {"timeframe": "W", "period": 14, "min": 20}}, "weekly ADX(14) >= 20 with +DI > -DI"),
        ("trend_supertrend", {"supertrend": {"timeframe": "W", "period": 10, "mult": 3}}, "weekly Supertrend(10,3) bullish"),
        ("trend_sma40", {"sma_rising": {"timeframe": "W", "period": 40, "slope_bars": 4}},
         "close above a rising 40-week average"),
        ("trend_ichimoku", {"ichimoku": {"timeframe": "M"}}, "monthly close above the Ichimoku cloud")]:
    f = {**flt, "rsi_min": m200["filters"]["rsi_min"]}
    write(variant(MAIN + "_nifty200", nm, f"[Trend filter swapped: {txt} instead of EMA61 on M/W/D.]", filters=f,
                  exits={**m200["exits"], "targets_pct": T4}), "4-trend")

UP = {"trend_ema": {"span": 61, "timeframes": ["M", "W", "D"]}, "rsi_min": {"period": 14, "value": 50, "timeframe": "M"}}
EXIT_M = {"targets_pct": T4, "ema_close_when_no_target": {"span": 61, "timeframe": "M"}, "max_days": None}
SIZ = m200["sizing"]
COST = m200["costs"]


def fresh(name, desc, tf, setup, filters, stop, mkt=True):
    return {"name": name, "description": desc + (MKT if mkt else ""), "universe": "NIFTY500",
            "period": {"start": "2000-01-01"}, "timeframe": tf, "setup": setup, "filters": filters,
            "entry": {"valid_bars": 1, **({"day_filters": {"market_sma": 200}} if mkt else {})},
            "stop": stop, "exits": EXIT_M, "sizing": SIZ, "costs": COST}


PULL = [("weekly_williams_r", "W", {"type": "williams_r", "period": 14, "level": -80},
         "Weekly Williams %R(14) crosses back above -80"),
        ("weekly_cci", "W", {"type": "cci_cross", "period": 20, "level": -100}, "Weekly CCI(20) crosses back above -100"),
        ("weekly_ema21_touch", "W", {"type": "ema_touch", "span": 21}, "Weekly low touches EMA21 and closes above it"),
        ("daily_rsi2", "D", {"type": "rsi_pullback", "period": 2, "level": 10}, "Daily RSI(2) below 10")]
for nm, tf, st, txt in PULL:
    stop = {"type": "atr", "mult": 2.0, "period": 14} if tf == "D" else {"type": "prev_week_low"}
    for mkt in [False, True]:
        write(fresh(f"pullback/{nm}{'_nifty200' if mkt else ''}", f"{txt}, in an uptrend (EMA61 on M/W/D, monthly RSI "
                    f"> 50). Buy above the signal candle's high; stop {'2 x ATR' if tf == 'D' else 'previous week low'}; "
                    f"no-target exit on a monthly close below EMA61.", tf, st, UP, stop, mkt), "4-pullback")

BRK = [("weekly_donchian20", {"type": "donchian", "period": 20}, "First weekly close above the prior 20-week high"),
       ("weekly_donchian55", {"type": "donchian", "period": 55}, "First weekly close above the prior 55-week high"),
       ("weekly_52w_high", {"type": "donchian", "period": 52}, "First weekly close at a new 52-week high"),
       ("weekly_bb_squeeze", {"type": "bb_squeeze", "period": 20, "k": 2.0, "lookback": 26, "recent": 4},
        "Weekly close above the upper Bollinger band (20,2) within 4 weeks of a 26-week band-width low"),
       ("weekly_rs_high", {"type": "rs_high", "period": 26}, "Stock/NIFTY 50 ratio makes a new 26-week high")]
UPM = {"trend_ema": {"span": 61, "timeframes": ["M"]}}
for nm, st, txt in BRK:
    for mkt in [False, True]:
        write(fresh(f"breakout/{nm}{'_nifty200' if mkt else ''}", f"{txt}, with the monthly close above EMA61. Buy "
                    f"above the signal week's high; stop previous week low; no-target exit on a monthly close below "
                    f"EMA61.", "W", st, UPM, {"type": "prev_week_low"}, mkt), "4-breakout")
for nm, st, txt in BRK[:3]:
    for cname, cf, ctxt in [("vol", {"volume": {"timeframe": "W", "mult": 1.5, "period": 20}},
                             "breakout-week volume above 1.5 x its 20-week average"),
                            ("obv", {"obv_high": {"timeframe": "W", "period": 26}}, "OBV at a 26-week high")]:
        write(fresh(f"breakout/{nm}_{cname}_nifty200", f"{txt}, with the monthly close above EMA61 and {ctxt}. Buy "
                    f"above the signal week's high; stop previous week low; no-target exit on a monthly close below "
                    f"EMA61.", "W", st, {**UPM, **cf}, {"type": "prev_week_low"}, True), "4-confirm")

for nm, stop, txt in [("stop_atr2", {"type": "atr", "mult": 2.0, "period": 14}, "2 x daily ATR(14) below entry"),
                      ("stop_atr3", {"type": "atr", "mult": 3.0, "period": 14}, "3 x daily ATR(14) below entry"),
                      ("stop_chandelier3", {"type": "prev_week_low", "trail": "atr", "trail_mult": 3.0, "period": 14},
                       "previous week low, trailed at the highest high since entry - 3 x ATR")]:
    write(variant(MAIN + "_nifty200", nm, f"[Stop swapped: {txt}.]", stop={**stop, **({} if "market_sma" not in
                  m200["stop"] else {})}, exits={**m200["exits"], "targets_pct": T4}), "4-stop")
for nm, ex, txt in [("exit_wema40", {"ema_close_when_no_target": {"span": 40, "timeframe": "W"}},
                     "weekly close below EMA40"),
                    ("exit_supertrend", {"ema_close_when_no_target": None,
                                         "supertrend_exit_when_no_target": {"timeframe": "W", "period": 10, "mult": 3}},
                     "weekly Supertrend(10,3) turns bearish")]:
    write(variant(MAIN + "_nifty200", nm, f"[Trend exit swapped: {txt} instead of a monthly close below EMA61.]",
                  exits={**m200["exits"], **ex, "targets_pct": T4}), "4-exit")

json.dump(jobs, open(OUT / "jobs.json", "w"), indent=1)
print(f"{len(made)} configs, {len(jobs)} jobs")
for ph in sorted({j['phase'] for j in jobs}):
    print(f"  {ph:12s} {sum(j['phase'] == ph for j in jobs)}")
