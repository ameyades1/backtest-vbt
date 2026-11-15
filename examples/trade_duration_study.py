"""Trade duration of winners vs losers, and what happens to trades still open after N days.

    python examples/trade_duration_study.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
import pandas as pd
from lib import data, indices, ema61, ema61_mtf
from lib.costs import FEES, SLIPPAGE

START = pd.Timestamp("2000-01-01")
CHECK = [30, 60, 90, 180, 365]
syms = [s for s in indices.symbols("NIFTY500") if s in data.cached_symbols()]
d = data.load(syms)
dailies = {s: pd.DataFrame({f: d[f][s] for f in ["Open", "High", "Low", "Close", "Volume"]}).dropna()
           for s in syms}
last_day = d["Close"].index[-1]

variants = {
    ("Candle low", "No target"): lambda df, s: ema61.simulate(df, s, "M", stop_at_low=True),
    ("Candle low", "Target 15%"): lambda df, s: ema61.simulate(df, s, "M", stop_at_low=True, target_pct=.15),
    ("Candle low", "Target 30%"): lambda df, s: ema61.simulate(df, s, "M", stop_at_low=True, target_pct=.30),
    ("Week low fixed", "No target"): lambda df, s: ema61_mtf.simulate(df, s, None, "fixed"),
    ("Week low fixed", "Target 15%"): lambda df, s: ema61_mtf.simulate(df, s, .15, "fixed"),
    ("Week low fixed", "Target 30%"): lambda df, s: ema61_mtf.simulate(df, s, .30, "fixed"),
}
dur_rows, cond_rows = [], []
for (stop, exit_), fn in variants.items():
    t = [x for s, df in dailies.items() for x in fn(df, s) if x.entry_date >= START]
    closed = [x for x in t if x.exit_date is not None]
    days = np.array([(x.exit_date - x.entry_date).days for x in closed])
    ret = np.array([x.exit * (1 - SLIPPAGE) * (1 - FEES) / (x.entry * (1 + SLIPPAGE) * (1 + FEES)) - 1
                    for x in closed]) * 100
    win = ret > 0
    for lab, m in [("Winners", win), ("Losers", ~win)]:
        dd = days[m]
        dur_rows.append({"Stop": stop, "Exit": exit_, "Group": lab, "Trades": m.sum(),
                         "Avg days": dd.mean(), "Median days": np.median(dd),
                         "P25 days": np.percentile(dd, 25), "P75 days": np.percentile(dd, 75),
                         "P90 days": np.percentile(dd, 90), "Avg gain %": ret[m].mean(),
                         "Median gain %": np.median(ret[m])})
    for n in CHECK:
        alive = days > n                     # still open after n calendar days
        cond_rows.append({"Stop": stop, "Exit": exit_, "After days": n,
                          "Still open %": alive.mean() * 100,
                          "Win % if still open": win[alive].mean() * 100 if alive.any() else np.nan,
                          "Win % if closed by then": win[~alive].mean() * 100 if (~alive).any() else np.nan,
                          "Winners done by then %": (days[win] <= n).mean() * 100,
                          "Losers done by then %": (days[~win] <= n).mean() * 100,
                          "Avg gain % if still open": ret[alive].mean() if alive.any() else np.nan})
out = Path("data") / "trade_duration"
out.mkdir(parents=True, exist_ok=True)
dur, cond = pd.DataFrame(dur_rows), pd.DataFrame(cond_rows)
dur.to_csv(out / "duration.csv", index=False); cond.to_csv(out / "conditional.csv", index=False)
pd.set_option("display.width", 250)
print(dur.to_string(index=False, float_format=lambda x: f"{x:,.1f}"))
print()
print(cond.to_string(index=False, float_format=lambda x: f"{x:,.1f}"))
