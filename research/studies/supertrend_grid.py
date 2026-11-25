"""Supertrend exit grid for S44984096 vs Sa1f19d11 on the release engine (July 2006+, point-in-time NIFTY 500,
release costs). Only rules.SUPERTREND changes. Walk-forward: fit 2006-16, hold out 2017-26; doubled slippage;
year by year and trade-level checks for (10,3) vs (14,3).

    .venv/bin/python research/studies/supertrend_grid.py
Writes reports/supertrend_grid.csv, reports/supertrend_yearly.csv, reports/supertrend_trades.csv.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "studies"))
from regime_variants import Universe, PERIODS, stats, rules, backtest  # noqa: E402

PERIODS = {**PERIODS, "2006-11": ("2006-07-01", "2011-12-31"), "2012-16": ("2012-01-01", "2016-12-31")}


def run(u, ok, st, slip=0.001):
    rules.SUPERTREND, rules.SLIPPAGE = st, slip
    u._cache = {}                                   # trades depend on SUPERTREND
    tr = u.trades(ok)
    curve, fills, _ = backtest.run(tr, u.closes)
    return curve, fills


def trade_table(fills):
    g = fills.groupby(["symbol", "entry_date"]).agg(cost=("cost", "sum"), proceeds=("proceeds", "sum"),
                                                   exit=("exit_date", "max"), reason=("reason", "last"))
    g["pnl"] = g.proceeds - g.cost
    g["days"] = (pd.to_datetime(g.exit) - pd.to_datetime(g.index.get_level_values(1))).dt.days
    return g


def main():
    u = Universe()
    ok = rules.market_ok(u.index)
    rows, curves, fills_by = [], {}, {}
    for n in (8, 10, 12, 14, 16, 20):
        for m in (2.5, 3.0, 3.5):
            for slip in (0.001, 0.002):
                c, f = run(u, ok, (n, m), slip)
                eq = c["equity"]
                if slip == 0.001:
                    curves[(n, m)], fills_by[(n, m)] = eq, f
                t = trade_table(f)
                for p, (s, e) in PERIODS.items():
                    rows.append({"st": f"({n},{m:g})", "n": n, "m": m, "slip": slip, "period": p,
                                 **stats(eq.loc[s:e]), "trades": len(t),
                                 "win%": (t.pnl > 0).mean() * 100, "avg_days": t.days.mean()})
                print(n, m, slip, round(stats(eq)["CAGR"], 2), round(stats(eq)["MaxDD"], 2), flush=True)
    rules.SUPERTREND, rules.SLIPPAGE = (10, 3.0), 0.001
    df = pd.DataFrame(rows)
    df.to_csv(ROOT / "reports" / "supertrend_grid.csv", index=False)

    # year by year, Rs 10 lakh
    yr = {}
    for st in ((10, 3.0), (14, 3.0)):
        eq = curves[st] * 10
        ye = eq.resample("YE").last()
        prev = np.r_[1e6, ye.values[:-1]]
        yr[f"ST{st}"] = pd.DataFrame({"ret%": (ye.values / prev - 1) * 100, "Rs lakh": ye.values / 1e5,
                                      "worst DD%": (eq / eq.cummax() - 1).resample("YE").min().values * 100},
                                     index=ye.index.year)
    pd.concat(yr, axis=1).to_csv(ROOT / "reports" / "supertrend_yearly.csv")

    # trade-level: where does the difference come from?
    a, b = trade_table(fills_by[(10, 3.0)]), trade_table(fills_by[(14, 3.0)])
    out = []
    for name, t in (("ST(10,3)", a), ("ST(14,3)", b)):
        top = t.pnl.sort_values(ascending=False)
        out.append({"exit": name, "trades": len(t), "win%": (t.pnl > 0).mean() * 100, "avg_days": t.days.mean(),
                    "median_days": t.days.median(), "net_pnl": t.pnl.sum(), "top10_pnl": top.head(10).sum(),
                    "top10_share%": top.head(10).sum() / t.pnl.sum() * 100,
                    "pnl_ex_top5": t.pnl.sum() - top.head(5).sum(),
                    "by_reason": t.groupby("reason").pnl.sum().round(0).to_dict()})
    common = a.index.intersection(b.index)
    pd.DataFrame(out).to_csv(ROOT / "reports" / "supertrend_trades.csv", index=False)
    print(pd.DataFrame(out).to_string(index=False))
    print(f"same entries (symbol, date) in both: {len(common)} of {len(a)} / {len(b)}")
    d = (b.loc[common, "pnl"] - a.loc[common, "pnl"]).sort_values()
    print("biggest per-trade gains for (14,3):", d.tail(8).round(0).to_dict())
    print("biggest per-trade losses for (14,3):", d.head(5).round(0).to_dict())

    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
    base = df[df.slip == 0.001]
    for p in ("Full", "Fit 2006-16", "Hold 2017-26", "2006-11", "2012-16", "2017-19", "2021-26", "Sep24+"):
        print(f"\n== {p}: CAGR ==")
        print(base[base.period == p].pivot(index="n", columns="m", values="CAGR").round(2).to_string())
        print(f"== {p}: MaxDD ==")
        print(base[base.period == p].pivot(index="n", columns="m", values="MaxDD").round(1).to_string())
    s2 = df[(df.slip == 0.002) & (df.period == "Full")]
    print("\n== Full, doubled slippage: CAGR ==")
    print(s2.pivot(index="n", columns="m", values="CAGR").round(2).to_string())
    fit = base[base.period == "Fit 2006-16"].set_index("st")
    best = fit.Calmar.idxmax()
    print(f"\nWalk-forward pick on 2006-16 Calmar: {best}")
    print(base[(base.st.isin([best, "(10,3)", "(14,3)"])) & (base.period == "Hold 2017-26")]
          [["st", "CAGR", "MaxDD", "Calmar", "UW days"]].round(2).to_string(index=False))
    print(pd.concat(yr, axis=1).round(1).to_string())


if __name__ == "__main__":
    main()
