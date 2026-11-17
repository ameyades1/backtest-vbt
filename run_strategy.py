"""Run one or more strategy configs and save results.

    python run_strategy.py strategies/stochrsi_pullback/weekly_candle_stop.json
    python run_strategy.py strategies/*/*.json --universe NIFTY50

Writes results/<strategy name>/<universe>/: config.json, summary.csv, equity.csv, fills_<target>.csv
(target 'none' = no fixed target). Re-running replaces that folder.
"""
import argparse, copy, json, sys
from pathlib import Path
import numpy as np
import pandas as pd
from lib import data, indices, engine, portfolio, market
from lib.costs import fee_per_side

ROOT = Path(__file__).resolve().parent


def load_dailies(universe):
    syms = [s for s in indices.symbols(universe) if s in data.cached_symbols()]
    d = data.load(syms)
    return d["Close"], {s: pd.DataFrame({f: d[f][s] for f in ["Open", "High", "Low", "Close", "Volume"]}).dropna()
                        for s in syms}


def engine_cfg(cfg, target):
    """Turn a strategy config plus one target (percent or None) into an engine config."""
    e = {k: cfg[k] for k in ("timeframe", "setup", "filters", "entry", "stop") if k in cfg}
    ex = cfg["exits"]
    e["exits"] = {"target_pct": None if target is None else target / 100,
                  "ema_close": ex.get("ema_close_when_no_target") if target is None else None,
                  "max_days": ex.get("max_days")}
    return e


def run(cfg, closes, dailies, out):
    siz, costs = cfg["sizing"], cfg["costs"]
    fee, slip = fee_per_side(costs["broker"], costs["product"]), costs["slippage_pct"] / 100
    start = cfg["period"]["start"]
    end = cfg["period"].get("end")
    if end:
        closes = closes[:end]
        dailies = {s: df[:end] for s, df in dailies.items()}
    out.mkdir(parents=True, exist_ok=True)
    for f in out.glob("fills_*.csv"):
        f.unlink()
    rows, curves = {}, {}
    for tg in cfg["exits"]["targets_pct"]:
        ec = engine_cfg(cfg, tg)
        mk = market.regime(ec["entry"]["day_filters"]["market_sma"]) \
            if "market_sma" in ec.get("entry", {}).get("day_filters", {}) else None
        trades = [t for s, df in dailies.items() for t in engine.simulate(df, s, ec, mk)]
        trades = [t for t in trades if t.entry_date >= pd.Timestamp(start)]
        label = "No target" if tg is None else f"Target {tg:g}%"
        sd = np.array([(t.entry - t.stop) / t.entry * 100 for t in trades if t.stop is not None])
        curve, fills, skipped = portfolio.run(trades, closes, siz["capital"], siz["risk_pct"] / 100,
                                              siz["max_positions"], fee, slip, siz.get("rank", "tightest"), start)
        rows[label] = {"Signals filled": len(trades), "Median stop %": np.median(sd) if len(sd) else np.nan,
                       **portfolio.summary(curve, fills, skipped, siz["capital"], siz["max_positions"])}
        curves[label] = curve["equity"]
        pd.DataFrame([vars(f) for f in fills]).to_csv(out / f"fills_{'none' if tg is None else f'{tg:g}'}.csv",
                                                      index=False)
    tab = pd.DataFrame(rows).T
    tab.to_csv(out / "summary.csv")
    pd.DataFrame(curves).to_csv(out / "equity.csv")
    json.dump(cfg, open(out / "config.json", "w"), indent=2)
    return tab


def main():
    p = argparse.ArgumentParser()
    p.add_argument("configs", nargs="+")
    p.add_argument("--universe", help="override the config's universe")
    a = p.parse_args()
    cache = {}
    for path in a.configs:
        cfg = json.load(open(path))
        if a.universe:
            cfg = copy.deepcopy(cfg); cfg["universe"] = a.universe
        u = cfg["universe"]
        if u not in cache:
            cache[u] = load_dailies(u)
        out = ROOT / "results" / cfg["name"] / u.lower()
        tab = run(cfg, *cache[u], out)
        print(f"\n== {cfg['name']} | {u} | {len(cache[u][1])} stocks -> {out.relative_to(ROOT)}")
        print(tab[["CAGR %", "Max DD %", "Win %", "Trades taken"]].to_string(float_format=lambda x: f"{x:,.1f}"))


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT))
    main()
