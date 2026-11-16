"""Monthly StochRSI pullback (lib/stochrsi_mtf.py), candle-low stop, portfolio sizing.

    python examples/stochrsi_pullback_study.py --risk 1 --max-pos 8
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
import pandas as pd
from lib import data, indices, stochrsi_mtf, portfolio
from lib.costs import FEES, SLIPPAGE

p = argparse.ArgumentParser()
p.add_argument("--index", default="NIFTY500")
p.add_argument("--capital", type=float, default=100_000)
p.add_argument("--risk", type=float, default=1.0)
p.add_argument("--max-pos", type=int, default=8)
p.add_argument("--oversold", type=float, default=30.0)
p.add_argument("--stop", default="candle", choices=["candle", "prev_week"])
p.add_argument("--start", default="2000-01-01")
a = p.parse_args()

syms = [s for s in indices.symbols(a.index) if s in data.cached_symbols()]
d = data.load(syms)
closes = d["Close"]
dailies = {s: pd.DataFrame({f: d[f][s] for f in ["Open", "High", "Low", "Close", "Volume"]}).dropna()
           for s in syms}
out = Path("data") / (("" if a.index == "NIFTY500" else f"{a.index.lower()}_") + f"stochrsi_r{a.risk:g}_p{a.max_pos}" + ("" if a.stop == "candle" else f"_{a.stop}"))
out.mkdir(parents=True, exist_ok=True)

rows, curves = {}, {}
for tg in [None, 8, 15, 20, 30]:
    trades = []
    for s, df in dailies.items():
        trades += stochrsi_mtf.simulate(df, s, None if tg is None else tg / 100, a.oversold, a.stop)
    trades = [t for t in trades if t.entry_date >= pd.Timestamp(a.start)]
    label = "No target (close<EMA61)" if tg is None else f"Target {tg}%"
    sd = np.array([(t.entry - t.stop) / t.entry * 100 for t in trades])
    curve, fills, skipped = portfolio.run(trades, closes, a.capital, a.risk / 100, a.max_pos,
                                          FEES, SLIPPAGE, start=a.start)
    rows[label] = {"Signals filled": len(trades), "Median stop %": np.median(sd) if len(sd) else np.nan,
                   **portfolio.summary(curve, fills, skipped, a.capital, a.max_pos)}
    curves[label] = curve["equity"] if "equity" in curve else curve.iloc[:, 0]
    pd.DataFrame([vars(f) for f in fills]).to_csv(out / f"fills_{'none' if tg is None else tg}.csv", index=False)
tab = pd.DataFrame(rows).T
tab.to_csv(out / "summary.csv")
pd.DataFrame(curves).to_csv(out / "equity.csv")
pd.set_option("display.width", 250)
print(f"Rs {a.capital:,.0f} | risk {a.risk}% | max {a.max_pos} | {len(syms)} stocks | from {a.start}\n")
print(tab.T.to_string(float_format=lambda x: f"{x:,.1f}"))
print(f"\nsaved -> {out}")
