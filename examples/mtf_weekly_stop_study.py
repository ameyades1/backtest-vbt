"""Triple-timeframe EMA61 breakout with previous-week-low stop, portfolio sizing.

    python examples/mtf_weekly_stop_study.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
import pandas as pd
from lib import data, indices, ema61_mtf, portfolio
from lib.costs import FEES, SLIPPAGE

CAPITAL, START = 100_000, "2000-01-01"
syms = [s for s in indices.symbols("NIFTY500") if s in data.cached_symbols()]
d = data.load(syms)
closes = d["Close"]
dailies = {s: pd.DataFrame({f: d[f][s] for f in ["Open", "High", "Low", "Close", "Volume"]}).dropna()
           for s in syms}
out = Path("data") / "mtf_weekly_stop"
out.mkdir(parents=True, exist_ok=True)

rows = []
for stop_mode in ["fixed", "trail"]:
    for tg in [None, 8, 15, 20, 30]:
        trades = []
        for s, df in dailies.items():
            trades += ema61_mtf.simulate(df, s, None if tg is None else tg / 100, stop_mode)
        trades = [t for t in trades if t.entry_date >= pd.Timestamp(START)]
        sd = np.array([(t.entry - t.stop) / t.entry * 100 for t in trades])
        rets = np.array([(t.exit or closes[t.symbol].dropna().iloc[-1]) * (1 - SLIPPAGE) * (1 - FEES)
                         / (t.entry * (1 + SLIPPAGE) * (1 + FEES)) - 1 for t in trades]) * 100
        base = {"Stop": stop_mode, "Exit": "No target" if tg is None else f"Target {tg}%",
                "Signals": len(trades), "Win %": (rets > 0).mean() * 100,
                "Avg trade %": rets.mean(), "Median trade %": np.median(rets),
                "Median stop %": np.median(sd)}
        for risk, mp in [(2, 4), (1, 8)]:
            curve, fills, skipped = portfolio.run(trades, closes, CAPITAL, risk / 100, mp,
                                                  FEES, SLIPPAGE, start=START)
            sm = portfolio.summary(curve, fills, skipped, CAPITAL, mp)
            rows.append({**base, "Sizing": f"{risk}%/{mp}", **sm})
tab = pd.DataFrame(rows)
tab.to_csv(out / "summary.csv", index=False)
pd.set_option("display.width", 250)
cols = ["Stop", "Exit", "Sizing", "Signals", "Median stop %", "Win %", "Avg trade %", "Median trade %",
        "CAGR %", "Max DD %", "Trades taken", "Avg position (Rs)", "Avg deployed %",
        "Days all slots full %", "Cash-capped entries %", "Worst trade % of capital"]
print(tab[cols].to_string(index=False, float_format=lambda x: f"{x:,.1f}"))
