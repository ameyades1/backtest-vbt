"""Re-run the main strategies on NIFTY500_PIT (point-in-time membership).  python studies/pit_rerun.py [workers]"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "studies"))
import overnight as O
O.OUT = ROOT / "results" / "studies" / "pit"
O.LOG = O.OUT / "run.log"
SP = "stochrsi_pullback/monthly_prev_week_stop"
MAIN = [SP, SP + "_nifty200", SP + "_nifty200_exit_supertrend", SP + "_nifty200_stop_atr2",
        "ema61_breakout/monthly_candle_stop", "breakout/weekly_donchian55_nifty200",
        SP + "_nifty200_exit_supertrend_c18_stack_compound", SP + "_nifty200_exit_supertrend_c18_stack_rs_compound",
        SP + "_c18_stack_rs_compound", "longshort/L_dd", "longshort/L_cap20_dd", "longshort/L_cap20_dd_r075",
        "longshort/L_cap20_dd_r050", "longshort/L_cap20_dd_r025", "longshort/LS_short_w_st10_2",
        "rotation/momentum_top10", "rotation/momentum_top10_nomkt",
        "longshort/L_cap20_dd_r050_rs", "longshort/L_cap20_dd_rs"]
if __name__ == "__main__":
    jobs = [{"phase": "pit", "config": f"strategies/{n}.json", "universe": "NIFTY500_PIT", "name": n} for n in MAIN]
    json.dump(jobs, open(O.OUT / "jobs.json", "w"), indent=1)
    print(O.run_jobs(jobs, int(sys.argv[1]) if len(sys.argv) > 1 else 5))
