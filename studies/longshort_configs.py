"""Configs for the long/short study. Idempotent; keeps IDs.
    python studies/longshort_configs.py [--stage 3 --long NAME --short NAME [--short2 NAME]] && python -m lib.ids assign
Part 1: harden Sa15d9d9c (L) - position cap, drawdown rule, risk, sector cap      (5 universes)
Part 2: short versions (stock futures; traded only in NIFTY 200 names)            (NIFTY100, NIFTY200, NIFTY500)
Part 3: combined books and the NIFTY-futures hedge                                 (5 universes)
"""
import argparse, copy, json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "results" / "studies" / "longshort"
OUT.mkdir(parents=True, exist_ok=True)
L = "stochrsi_pullback/monthly_prev_week_stop_nifty200_exit_supertrend_c18_stack_compound"    # Sa15d9d9c
UNI5 = ("NIFTY500", "NIFTY50", "NIFTY100", "MIDCAP150", "SMALLCAP250")
UNI_S = ("NIFTY100", "NIFTY200", "NIFTY500")
load = lambda n: json.load(open(ROOT / "strategies" / f"{n}.json"))


def write(c, phase, unis, jobs):
    c = copy.deepcopy(c); c.pop("id", None)
    p = ROOT / "strategies" / f"{c['name']}.json"
    if p.exists() and "id" in json.load(open(p)):
        c = {"id": json.load(open(p))["id"], **c}
    p.parent.mkdir(parents=True, exist_ok=True)
    json.dump(c, open(p, "w"), indent=2); open(p, "a").write("\n")
    jobs += [{"phase": phase, "config": f"strategies/{c['name']}.json", "universe": u, "name": c["name"]} for u in unis]


def lvar(suffix, desc, **siz):
    c = load(L); c["name"] = f"longshort/L_{suffix}"; c["description"] = load(L)["description"] + f" [{desc}]"
    c["sizing"].update(siz)
    return c


def part12():
    jobs = []
    DD = {"halve": 10, "pause": 15, "pause_days": 21}
    for suf, d, kw in [
            ("base", "Sa15d9d9c unchanged (reference).", {}),
            ("cap15", "Positions capped at 15% of equity, trimmed at month end.", {"pos_cap": 0.15}),
            ("cap20", "Positions capped at 20% of equity, trimmed at month end.", {"pos_cap": 0.20}),
            ("cap25", "Positions capped at 25% of equity, trimmed at month end.", {"pos_cap": 0.25}),
            ("dd", "Half risk after a 10% drawdown, 21-day pause at 15%.", {"dd_rule": DD}),
            ("r075", "0.75% of equity per trade.", {"risk_pct": 0.75}),
            ("cap20_dd", "20% position cap + drawdown rule.", {"pos_cap": 0.20, "dd_rule": DD}),
            ("cap20_dd_r075", "20% cap + drawdown rule + 0.75% risk.", {"pos_cap": 0.20, "dd_rule": DD, "risk_pct": 0.75}),
            ("cap20_sec2", "20% cap + at most 2 positions per sector.", {"pos_cap": 0.20, "sector_cap": 2}),
            ("cap20_dd_sec2", "20% cap + drawdown rule + sector cap 2.", {"pos_cap": 0.20, "dd_rule": DD, "sector_cap": 2})]:
        write(lvar(suf, d, **kw), "1-harden", UNI5, jobs)

    base = load(L)
    def svar(suf, desc, tf="M", ob=30, ema=61, tfs=("M", "W", "D"), targets=(None,), max_days=None, rank=None,
             mkt=True, st=(10, 3)):
        c = copy.deepcopy(base); c.pop("id", None)
        c["name"] = f"longshort/S_{suf}"; c["side"] = "short"; c["symbols_from"] = "NIFTY200"
        c["description"] = (f"SHORT (stock futures, NIFTY 200 names): {'monthly' if tf == 'M' else 'weekly'} StochRSI "
                            f"%K crosses below %D with %D above {100 - ob}; close below EMA{ema} on {', '.join(tfs)}; "
                            f"RSI < 50; sell-stop below the signal low; stop at the previous week's high; cover when "
                            f"the weekly Supertrend{st} turns bullish." + (" New shorts only while NIFTY 50 is below "
                            "its 200-day average." if mkt else "") + f" [{desc}]")
        c["timeframe"] = tf
        c["setup"]["oversold"] = ob
        c["filters"]["trend_ema"] = {"span": ema, "timeframes": list(tfs)}
        c["entry"] = {"valid_bars": 1, "day_filters": {"market_below_sma": 200} if mkt else {}}
        c["exits"] = {"targets_pct": list(targets), "ema_close_when_no_target": None, "max_days": max_days,
                      "supertrend_exit_when_no_target": {"timeframe": "W", "period": st[0], "mult": st[1]},
                      "time_stop": {"days": 25, "min_r": 0.5}}
        c["sizing"] = {"capital": 100000, "risk_pct": 1.0, "max_positions": 6, "rank": "tightest", "compound": True,
                       "cash": {"type": "liquid", "rate": 6.5}, "short": {"margin": 0.25, "roll": 0.001, "max": 6}}
        if rank:
            c["sizing"].update(rank="score_tightest", score={"type": "weak", "months": 6})
        c["costs"]["short_product"] = "futures"
        write(c, "2-short", UNI_S, jobs)
    svar("m_mirror", "Exact mirror of the long rules (monthly).")
    svar("m_ob60", "Monthly, overbought 60.", ob=40)
    svar("m_ob50", "Monthly, %D above 50.", ob=50)
    svar("m_mw", "Monthly, trend filter on monthly + weekly only.", tfs=("M", "W"))
    svar("w_mirror", "Weekly signals, same rules.", tf="W")
    svar("w_ob60", "Weekly, overbought 60.", tf="W", ob=40)
    svar("w_wd", "Weekly, trend filter on weekly + daily only.", tf="W", tfs=("W", "D"))
    for e in (34, 55, 89):
        svar(f"w_ema{e}", f"Weekly, EMA{e}.", tf="W", ema=e)
    svar("w_2r", "Weekly, 2R target.", tf="W", targets=("2R",))
    svar("w_max90", "Weekly, covered after 90 days at most.", tf="W", max_days=90)
    svar("w_weak", "Weekly, weakest 6-month return first.", tf="W", rank=True)
    svar("w_nomkt", "Weekly, no NIFTY filter (shorts in any market).", tf="W", mkt=False)
    svar("w_st10_2", "Weekly, tighter Supertrend(10,2) cover.", tf="W", st=(10, 2))
    json.dump(jobs, open(OUT / "jobs12.json", "w"), indent=1)
    print(len(jobs), "jobs")


def part3(long, shorts):
    jobs = []
    lc = load(long)
    def comb(suf, desc, combine=(), **siz):
        c = copy.deepcopy(lc); c.pop("id", None)
        c["name"] = f"longshort/LS_{suf}"; c["description"] = lc["description"] + f" [{desc}]"
        c["combine"] = [{"config": f"strategies/{s}.json", "universe": "NIFTY200"} for s in combine]
        c["sizing"].update(siz)
        c["sizing"].setdefault("short", {"margin": 0.25, "roll": 0.001, "max": 6})
        c["costs"]["short_product"] = "futures"
        write(c, "3-combined", UNI5, jobs)
    comb("hedge100", "Short NIFTY futures = 100% of the long book while NIFTY is below its 200-DMA.", hedge={"ratio": 1.0})
    comb("hedge50", "Short NIFTY futures = 50% of the long book while NIFTY is below its 200-DMA.", hedge={"ratio": 0.5})
    for i, s in enumerate(shorts):
        tag = s.split("/S_")[-1]
        comb(f"short_{tag}", f"Plus {s.split('/')[-1]} shorts sharing the capital; 12 slots, at most 6 shorts.",
             [s], max_positions=12)
        comb(f"short_{tag}_risk8", f"As short_{tag} with total open risk capped at 8% of equity.", [s],
             max_positions=12, max_open_risk=0.08)
        comb(f"short_{tag}_hedge50", f"Shorts + 50% NIFTY hedge below the 200-DMA.", [s], max_positions=12,
             hedge={"ratio": 0.5})
    if len(shorts) > 1:
        comb("short_both", "Both short versions sharing the capital, 12 slots.", shorts, max_positions=12)
    json.dump(jobs, open(OUT / "jobs3.json", "w"), indent=1)
    print(len(jobs), "jobs")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--stage", type=int, default=12)
    ap.add_argument("--long"); ap.add_argument("--short", nargs="*")
    a = ap.parse_args()
    part12() if a.stage == 12 else part3(a.long, a.short)
