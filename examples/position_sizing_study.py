"""Capital deployment study: EMA61 monthly breakout, fixed 2% risk per trade, max 4 positions.

    python examples/position_sizing_study.py --capital 100000 --risk 2 --max-pos 4
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd
from lib import data, indices, ema61, portfolio
from lib.costs import FEES, SLIPPAGE

p = argparse.ArgumentParser()
p.add_argument("--index", default="NIFTY500")
p.add_argument("--capital", type=float, default=100_000)
p.add_argument("--risk", type=float, default=2.0, help="%% of initial capital risked per trade")
p.add_argument("--max-pos", type=int, default=4)
p.add_argument("--start", default="2000-01-01")
p.add_argument("--targets", nargs="*", type=float, default=[8, 15, 20, 30])
a = p.parse_args()

syms = [s for s in indices.symbols(a.index) if s in data.cached_symbols()]
d = data.load(syms)
closes = d["Close"]
dailies = {s: pd.DataFrame({f: d[f][s] for f in ["Open", "High", "Low", "Close", "Volume"]}).dropna()
           for s in syms}

out = Path("data") / f"sizing_r{a.risk:g}_p{a.max_pos}"
out.mkdir(parents=True, exist_ok=True)
rows, curves = {}, {}
for tg in [None] + a.targets:
    trades = []
    for s, df in dailies.items():
        trades += ema61.simulate(df, s, "M", stop_at_low=True,
                                 target_pct=None if tg is None else tg / 100)
    curve, fills, skipped = portfolio.run(trades, closes, a.capital, a.risk / 100, a.max_pos,
                                          FEES, SLIPPAGE, start=a.start)
    label = "No target (close<EMA61)" if tg is None else f"Target {tg:g}%"
    rows[label] = portfolio.summary(curve, fills, skipped, a.capital, a.max_pos)
    curves[label] = curve
    pd.DataFrame([vars(f) for f in fills]).to_csv(
        out / f"fills_{'none' if tg is None else int(tg)}.csv", index=False)

tab = pd.DataFrame(rows).T
tab.to_csv(out / "summary.csv")
pd.concat({k: v["deployed"] for k, v in curves.items()}, axis=1).to_csv(out / "deployed.csv")
pd.concat({k: v["equity"] for k, v in curves.items()}, axis=1).to_csv(out / "equity.csv")
pd.set_option("display.width", 250)
print(f"Capital Rs {a.capital:,.0f} | risk {a.risk}% = Rs {a.capital * a.risk / 100:,.0f}/trade | "
      f"max {a.max_pos} positions | {len(syms)} stocks | from {a.start}\n")
print(f"saved -> {out}")
print(tab.T.to_string(float_format=lambda x: f"{x:,.1f}"))
