"""Slot ranking study: which signals should fill the 8 slots when there are more signals than slots?

    python studies/slot_ranking.py [--random 300]

For three no-target strategies (1% risk, 8 slots, NIFTY 500, from 2000) runs:
  rules   tightest stop (current), widest stop, 6- and 12-month return (relative strength), trend strength
          (% above monthly EMA61), liquidity (20-day traded value), low volatility (ATR %),
          each with and without a cap of 2 positions per sector
  random  the same trades with random ranking, N seeds: the spread that luck alone produces
All scores use data up to the day before entry. Writes results/studies/slot_ranking/.
"""
import argparse, json, sys, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from lib import data, indices, engine, portfolio
from lib.costs import fee_per_side
from run_strategy import engine_cfg

p = argparse.ArgumentParser()
p.add_argument("--random", type=int, default=300)
a = p.parse_args()
OUT = ROOT / "results" / "studies" / "slot_ranking"
OUT.mkdir(parents=True, exist_ok=True)
STRATS = {"StochRSI pullback, prev-week stop": "stochrsi_pullback/monthly_prev_week_stop",
          "StochRSI pullback, candle-low stop": "stochrsi_pullback/monthly_candle_stop",
          "EMA61 breakout, candle-low stop": "ema61_breakout/monthly_candle_stop"}
MAIN = "StochRSI pullback, prev-week stop"

syms = [s for s in indices.symbols("NIFTY500") if s in data.cached_symbols()]
d = data.load(syms)
closes = d["Close"]
dailies = {s: pd.DataFrame({f: d[f][s] for f in ["Open", "High", "Low", "Close", "Volume"]}).dropna() for s in syms}
fee, slip = fee_per_side("sharekhan", "delivery"), 0.001
START = "2000-01-01"

# --- ranking scores (higher = preferred), known before the entry day ---
c = closes.ffill()
hi, lo = d["High"].ffill(), d["Low"].ffill()
tr = pd.concat([hi - lo, (hi - c.shift()).abs(), (lo - c.shift()).abs()]).groupby(level=0).max()
ema_m = {}
for s in syms:
    m = dailies[s]["Close"].resample("ME").last().dropna()
    ema_m[s] = m.ewm(span=61, adjust=False, min_periods=61).mean()
ema_m = pd.DataFrame(ema_m).reindex(c.index, method="ffill")
SCORES = {
    "6-month return": (c / c.shift(126) - 1).shift(1),
    "12-month return": (c / c.shift(252) - 1).shift(1),
    "Trend strength": (c / ema_m - 1).shift(1),
    "Liquidity": (c * d["Volume"]).rolling(20, min_periods=10).mean().shift(1),
    "Low volatility": -(tr.reindex(c.index).rolling(14).mean() / c).shift(1),
}
ind = pd.read_csv(ROOT / "data" / "constituents" / "NIFTY500.csv")
SECTOR = {f"{r.Symbol}.NS": r.Industry for r in ind.itertuples()}

RULES = ["Tightest stop (current)", "Widest stop", "6-month return", "12-month return", "Trend strength",
         "Liquidity", "Low volatility"]


def run(trades, rule, cap=None, seed=None):
    kw = dict(start=START, sector_of=SECTOR, sector_cap=cap)
    if rule == "Tightest stop (current)":
        kw["rank"] = "tightest"
    elif rule == "Widest stop":
        kw["rank"] = "widest"
    elif rule == "Random":
        kw.update(rank="random", seed=seed)
    else:
        kw.update(rank="score", score=SCORES[rule])
    curve, fills, sk = portfolio.run(trades, closes, 100_000, 0.01, 8, fee, slip, **kw)
    sm = portfolio.summary(curve, fills, sk, 100_000, 8)
    eq = curve["equity"]
    pnl = np.array([f.proceeds - f.cost for f in fills])
    sec = pd.Series([SECTOR.get(f.symbol, "?") for f in fills])
    return {"CAGR %": sm["CAGR %"], "Max DD %": sm["Max DD %"], "CAGR/DD": sm["CAGR %"] / -sm["Max DD %"],
            "Win %": sm["Win %"], "Trades": sm["Trades taken"], "Skipped": sm["Signals skipped"],
            "Final equity (Rs)": sm["Final equity (Rs)"], "Avg trade %": sm["Avg trade %"],
            "Median hold days": sm["Median hold days"], "Avg deployed %": sm["Avg deployed %"],
            "Top sector share %": sec.value_counts(normalize=True).iloc[0] * 100 if len(sec) else np.nan,
            "Top sector": sec.value_counts().index[0] if len(sec) else "",
            "Best trade share of P&L %": pnl.max() / pnl.sum() * 100 if pnl.sum() > 0 else np.nan}, eq, fills


rule_rows, rand_rows, curves = [], [], {}
for name, cfgp in STRATS.items():
    cfg = json.load(open(ROOT / "strategies" / f"{cfgp}.json"))
    ec = engine_cfg(cfg, None)
    trades = [t for s, df in dailies.items() for t in engine.simulate(df, s, ec) if t.entry_date >= pd.Timestamp(START)]
    t0 = time.time()
    for rule in RULES:
        for cap in [None, 2]:
            r, eq, fills = run(trades, rule, cap)
            rule_rows.append({"Strategy": name, "Rule": rule, "Sector cap": "2 per sector" if cap else "none", **r})
            if name == MAIN:
                curves[f"{rule}{' + cap' if cap else ''}"] = eq
                if rule == "Tightest stop (current)" and cap is None or rule == "12-month return" and cap is None:
                    pd.DataFrame([vars(f) for f in fills]).to_csv(OUT / f"fills_main_{rule.split()[0].lower()}.csv", index=False)
            print(f"{name:36s} {rule:24s} cap={cap}  CAGR {r['CAGR %']:5.1f}  DD {r['Max DD %']:6.1f}", flush=True)
    n = a.random if name == MAIN else max(1, a.random // 3)
    for seed in range(n):
        r, _, _ = run(trades, "Random", None, seed)
        rand_rows.append({"Strategy": name, "Seed": seed, **r})
    print(f"  {n} random runs in {time.time() - t0:.0f}s", flush=True)
    pd.DataFrame(rule_rows).to_csv(OUT / "rules.csv", index=False)
    pd.DataFrame(rand_rows).to_csv(OUT / "random.csv", index=False)
pd.DataFrame(curves).to_csv(OUT / "equity_main.csv")
print("saved ->", OUT.relative_to(ROOT))
