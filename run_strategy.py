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
from lib import data, indices, engine, portfolio, market, scores, ids, rotation
from lib.costs import fee_per_side

ROOT = Path(__file__).resolve().parent


def load_dailies(universe):
    if universe == "NIFTY500_PIT":                      # every stock ever in NIFTY 500 (trades filtered by date)
        from lib import membership
        syms = [s for s in membership.ever_members() if s in data.cached_symbols()]
    else:
        syms = [s for s in indices.symbols(universe) if s in data.cached_symbols()]
    d = data.load(syms)
    return d["Close"], {s: pd.DataFrame({f: d[f][s] for f in ["Open", "High", "Low", "Close", "Volume"]}).dropna()
                        for s in syms}


def engine_cfg(cfg, target):
    """Turn a strategy config plus one target into an engine config. target: None (no target: trend exit),
    a percent (8), "2R" (2 x initial risk) or "P1.5R" (sell half at 1.5R, the rest by the no-target exits)."""
    e = {k: cfg[k] for k in ("timeframe", "setup", "filters", "entry", "stop", "side") if k in cfg}
    ex = cfg["exits"]
    trend = target is None or (isinstance(target, str) and target.startswith("P"))
    e["exits"] = {"target_pct": target / 100 if isinstance(target, (int, float)) else None,
                  "ema_close": ex.get("ema_close_when_no_target") if trend else None,
                  "max_days": ex.get("max_days")}
    for k in ("time_stop", "pyramid"):
        if ex.get(k):
            e["exits"][k] = ex[k]
    if trend and ex.get("supertrend_exit_when_no_target"):
        e["exits"]["supertrend_exit"] = ex["supertrend_exit_when_no_target"]
    if isinstance(target, str) and target.startswith("P"):
        e["exits"]["partial"] = {"frac": ex.get("partial_frac", 0.5), "at_r": float(target[1:-1])}
    elif isinstance(target, str):
        e["exits"]["target_r"] = float(target[:-1])
    return e


def label(tg):
    return "No target" if tg is None else f"Target {tg:g}%" if isinstance(tg, (int, float)) else f"Target {tg}"


def fid(tg):
    return "none" if tg is None else f"{tg:g}" if isinstance(tg, (int, float)) else tg


_BREADTH = {}


def risk_mult(rules, closes):
    """Day -> risk multiplier from sizing.risk_rules (market_sma, breadth, vix); uses data known before the day."""
    m = pd.Series(1.0, index=closes.index)
    if "market_sma" in rules:
        r = rules["market_sma"]
        ok = market.regime(r.get("days", 200)).astype(float).reindex(closes.index, method="ffill").fillna(1) > 0
        m[~ok.shift(1, fill_value=True)] *= r.get("mult", 0.5)
    if "breadth" in rules:
        r = rules["breadth"]
        k = (tuple(closes.columns), r.get("days", 200))
        if k not in _BREADTH:
            c = closes.ffill()
            sm = c.rolling(r.get("days", 200), min_periods=r.get("days", 200)).mean()
            valid = sm.notna()
            _BREADTH[k] = ((c > sm) & valid).sum(axis=1) / valid.sum(axis=1).replace(0, np.nan) * 100
        b = _BREADTH[k].shift(1)
        m[(b < r.get("min", 40)).fillna(False)] *= r.get("mult", 0.5)
    if "vix" in rules:
        r = rules["vix"]
        v = data.load(["^INDIAVIX"])["Close"]["^INDIAVIX"].reindex(closes.index, method="ffill").shift(1)
        m[(v > r.get("max", 25)).fillna(False)] *= r.get("mult", 0.5)
    return m


_TRADES = {}      # engine config + market filter + universe size -> trades; ranking variants reuse them


def cash_return(spec, closes):
    """sizing.cash: {"type": "liquid", "rate": 6.5} (annual %, daily accrual) or {"type": "nifty", "cost": 0.1}
    (idle cash in a NIFTY 50 ETF: price return, less an annual cost %)."""
    if spec["type"] == "liquid":
        return pd.Series((1 + spec.get("rate", 6.5) / 100) ** (1 / 252) - 1, index=closes.index)
    n = engine.nifty_close().reindex(closes.index, method="ffill")
    return n.pct_change().fillna(0) - spec.get("cost", 0.1) / 100 / 252


INV_C = 1e4


def invert(df):
    """Reciprocal price series for shorts: C/price, with High and Low swapped (a fall becomes a rise)."""
    return pd.DataFrame({"Open": INV_C / df["Open"], "High": INV_C / df["Low"], "Low": INV_C / df["High"],
                         "Close": INV_C / df["Close"], "Volume": df["Volume"]}, index=df.index)


def _sim(ec, dailies, end):
    df_ = ec.get("entry", {}).get("day_filters", {})
    mdays = df_.get("market_sma") or df_.get("market_below_sma") or ec["stop"].get("market_sma")
    mk = market.regime(mdays) if mdays else None
    st_ = ec.get("stop", {})
    mkt_t = market.regime(st_["market_tighten_sma"], st_.get("market_tighten_index")) \
        if st_.get("market_tighten") and st_.get("market_tighten_sma") else None
    key = (json.dumps(ec, sort_keys=True), tuple(dailies), end)
    if key not in _TRADES:
        if ec.get("side") == "short":
            out = []
            for s, df in dailies.items():
                for t in engine.simulate(invert(df), s, ec, mk, mkt_t):
                    t.entry = INV_C / t.entry
                    t.exit = INV_C / t.exit if t.exit is not None else None
                    t.stop = INV_C / t.stop if t.stop is not None else None
                    t.side = -1
                    out.append(t)
            _TRADES[key] = out
        else:
            _TRADES[key] = [t for s, df in dailies.items() for t in engine.simulate(df, s, ec, mk, mkt_t)]
    return _TRADES[key]


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
    score = scores.table(siz["score"], dailies) if "score" in siz else None
    rm = risk_mult(siz["risk_rules"], closes) if siz.get("risk_rules") else None
    cr = cash_return(siz["cash"], closes) if siz.get("cash") else None
    if siz.get("sector_top"):
        top_sectors_tab = scores.top_sectors(dailies, siz["sector_top"].get("n", 4), siz["sector_top"].get("months", 6))
    sec_of = scores.sector_map() if siz.get("sector_cap") else None
    if siz.get("liq_top_pct"):
        liq_rank = pd.DataFrame({s: (d["Close"] * d["Volume"]).rolling(60, min_periods=20).median().shift(1)
                                 for s, d in dailies.items()}).rank(axis=1, pct=True)
    if siz.get("min_turnover_cr"):
        turnover = pd.DataFrame({s: (d["Close"] * d["Volume"]).rolling(60, min_periods=20).median().shift(1)
                                 for s, d in dailies.items()})
    slip_of = None
    if costs.get("slippage_extra"):                     # {"universe": "MICROCAP250", "pct": 0.5}
        x = costs["slippage_extra"]
        slip_of = {s: x["pct"] / 100 for s in indices.symbols(x["universe"])}
    sfee = fee_per_side(costs["broker"], costs.get("short_product", "futures"))
    short_spec = {"fee": sfee, **siz.get("short", {})}
    hedge_spec = None
    if siz.get("hedge"):                                 # {"ratio": 1.0, "sma": 200}: short NIFTY futures below the SMA
        h = siz["hedge"]
        hedge_spec = {"ratio": h.get("ratio", 1.0), "fee": sfee,
                      "regime": ~market.regime(h.get("sma", 200), h.get("index")).shift(1, fill_value=True).astype(bool)}
    if cfg.get("universe") == "NIFTY500_PIT":
        from lib import membership
        pit = membership.membership_table(closes.index, list(dailies))
    if cfg["setup"]["type"] == "momentum_rotation":
        curve, fills, skipped = rotation.run(cfg, closes, dailies, siz["capital"], fee, slip, start, cr,
                                             pit if cfg.get("universe") == "NIFTY500_PIT" else None)
        tab = pd.DataFrame({"No target": {"Signals filled": len(fills), "Median stop %": np.nan,
                            **portfolio.summary(curve, fills, skipped, siz["capital"], cfg["setup"].get("top", 10))}}).T
        tab.to_csv(out / "summary.csv")
        pd.DataFrame({"No target": curve["equity"]}).to_csv(out / "equity.csv")
        pd.DataFrame([vars(f) for f in fills]).to_csv(out / "fills_none.csv", index=False)
        json.dump(cfg, open(out / "config.json", "w"), indent=2)
        return tab
    for tg in cfg["exits"]["targets_pct"]:
        ec = engine_cfg(cfg, tg)
        trades = list(_sim(ec, dailies, end))
        if cfg.get("universe") == "NIFTY500_PIT":       # point in time: only stocks in the index on the entry day
            trades = [t for t in trades if bool(pit.at[t.entry_date, t.symbol])]
        if cfg.get("symbols_from"):                     # e.g. shorts only in an F&O-like list (NIFTY 200)
            keep = set(indices.symbols(cfg["symbols_from"]))
            trades = [t for t in trades if t.symbol in keep]
        for sub in cfg.get("combine", []):              # another strategy's trades share this portfolio
            sc = json.load(open(ROOT / sub["config"]))
            keep = set(indices.symbols(sub["universe"])) if sub.get("universe") else None
            trades += [t for t in _sim(engine_cfg(sc, sub.get("target")), dailies, end)
                       if keep is None or t.symbol in keep]
        if siz.get("min_turnover_cr"):                  # liquidity: median daily traded value, last 60 days
            tv = turnover
            trades = [t for t in trades if t.entry_date in tv.index and t.symbol in tv.columns
                      and tv.at[t.entry_date, t.symbol] >= siz["min_turnover_cr"] * 1e7]
        if siz.get("liq_top_pct"):                      # liquidity relative to the universe that day
            lr = liq_rank
            trades = [t for t in trades if t.entry_date in lr.index and t.symbol in lr.columns
                      and lr.at[t.entry_date, t.symbol] >= 1 - siz["liq_top_pct"] / 100]
        if siz.get("sector_top"):
            ok = top_sectors_tab
            trades = [t for t in trades if t.entry_date in ok.index and t.symbol in ok.columns
                      and bool(ok.at[t.entry_date, t.symbol])]
        trades = [t for t in trades if t.entry_date >= pd.Timestamp(start)]
        if siz.get("max_stop_pct"):
            trades = [t for t in trades if abs(t.entry - t.stop) / t.entry * 100 <= siz["max_stop_pct"]]
        lbl = label(tg)
        sd = np.array([abs(t.entry - t.stop) / t.entry * 100 for t in trades if t.stop is not None])
        curve, fills, skipped = portfolio.run(trades, closes, siz["capital"], siz["risk_pct"] / 100,
                                              siz["max_positions"], fee, slip, siz.get("rank", "tightest"), start,
                                              score=score, risk_mult=rm, dd_rule=siz.get("dd_rule"),
                                              cash_ret=cr, compound=siz.get("compound", False),
                                              pos_cap=siz.get("pos_cap"), max_open_risk=siz.get("max_open_risk"),
                                              short=short_spec, hedge=hedge_spec, slip_of=slip_of, sector_of=sec_of, sector_cap=siz.get("sector_cap"))
        rows[lbl] = {"Signals filled": len(trades), "Median stop %": np.median(sd) if len(sd) else np.nan,
                       **portfolio.summary(curve, fills, skipped, siz["capital"], siz["max_positions"])}
        curves[lbl] = curve["equity"]
        pd.DataFrame([vars(f) for f in fills]).to_csv(out / f"fills_{fid(tg)}.csv",
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
    if not ids.check():
        sys.exit("fix strategy ids first: python -m lib.ids assign")
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
