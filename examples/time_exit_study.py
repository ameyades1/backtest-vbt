"""Do time exits (90/180/365 days) recycle slots and improve portfolio CAGR?

    python examples/time_exit_study.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd
from lib import data, indices, ema61, ema61_mtf, portfolio
from lib.costs import FEES, SLIPPAGE

CAPITAL, START = 100_000, "2000-01-01"
syms = [s for s in indices.symbols("NIFTY500") if s in data.cached_symbols()]
d = data.load(syms)
closes = d["Close"]
dailies = {s: pd.DataFrame({f: d[f][s] for f in ["Open", "High", "Low", "Close", "Volume"]}).dropna()
           for s in syms}
out = Path("data") / "time_exit"
out.mkdir(parents=True, exist_ok=True)


def sim(stop, tg, md, df, s):
    if stop == "Candle low":
        return ema61.simulate(df, s, "M", stop_at_low=True, target_pct=tg, max_days=md)
    return ema61_mtf.simulate(df, s, tg, "fixed", max_days=md)


rows = []
for stop in ["Candle low", "Week low fixed"]:
    for tg in [None, 0.15, 0.30]:
        for md in [None, 90, 180, 365]:
            trades = [x for s, df in dailies.items() for x in sim(stop, tg, md, df, s)]
            for risk, mp in [(2, 4), (1, 8)]:
                curve, fills, skipped = portfolio.run(trades, closes, CAPITAL, risk / 100, mp,
                                                      FEES, SLIPPAGE, start=START)
                sm = portfolio.summary(curve, fills, skipped, CAPITAL, mp)
                rows.append({"Stop": stop, "Exit": "No target" if tg is None else f"Target {tg * 100:.0f}%",
                             "Time exit": "None" if md is None else f"{md} days",
                             "Sizing": f"{risk}%/{mp}", **sm})
            print(stop, tg, md, "done", flush=True)
tab = pd.DataFrame(rows)
tab.to_csv(out / "summary.csv", index=False)
pd.set_option("display.width", 250)
cols = ["Stop", "Exit", "Time exit", "Sizing", "CAGR %", "Max DD %", "Trades taken", "Signals skipped",
        "Win %", "Avg trade %", "Median trade %", "Avg hold days", "Median hold days", "Avg deployed %"]
print(tab[cols].to_string(index=False, float_format=lambda x: f"{x:,.1f}"))
