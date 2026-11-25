"""Variants 1 and 2 from reports/Regime filters and trailing exits.md, run on the release S44984096 backtest
(point-in-time NIFTY 500, same costs, fills and rules; only the per-day risk multiplier changes).

  V1 volatility sizing: risk per trade x clip(target / realised vol of the strategy's own daily equity returns,
     floor, cap). Target = expanding median of that realised vol (needs 252 days; scale 1 before), so no look-ahead.
  V2 graded market filter: NIFTY 500 above its 200-day SMA AND the SMA rising over N days -> full size; one of the
     two -> half size; neither -> no new entries. Optional band b: "above" flips on above SMA*(1+b), off below
     SMA*(1-b). Uses the index close of the previous index day, like the release filter.
  V6 slow EMA exit (--ema): the weekly Supertrend exit is replaced by "weekly close turns from above to below its
     N-week EMA -> sell at the next open". Entries, stop, time stop and sizing unchanged.

Both multiply the release drawdown rule's multiplier. Walk-forward: parameters picked on 2006-07..2016 by Calmar,
then read on 2017..2026 (holdout). Writes reports/regime_variants.csv and prints the tables.

    .venv/bin/python research/studies/regime_variants.py [--slip2]
"""
import argparse, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
REL = ROOT / "release" / "s44984096"
sys.path.insert(0, str(REL))
import rules, backtest, data  # noqa: E402

PERIODS = {"Full": ("2006-07-01", None), "Fit 2006-16": ("2006-07-01", "2016-12-31"),
           "Hold 2017-26": ("2017-01-01", None), "2017-19": ("2017-01-01", "2019-12-31"),
           "2020": ("2020-01-01", "2020-12-31"), "2021-26": ("2021-01-01", None), "Sep24+": ("2024-09-01", None)}


def stats(eq):
    r = eq.pct_change().dropna()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = ((eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1) * 100
    dd = eq / eq.cummax() - 1
    under = (dd < 0).astype(int)
    longest = under.groupby((under == 0).cumsum()).sum().max()
    return {"CAGR": cagr, "MaxDD": dd.min() * 100, "Calmar": cagr / -dd.min() / 100 if dd.min() < 0 else np.nan,
            "Vol": r.std() * np.sqrt(252) * 100, "UW days": int(longest)}


def wrap_dd(days, extra):
    """A DrawdownRule whose multiplier is also scaled by extra(i, prev_eq) on the i-th backtest day."""
    class Rule(rules.DrawdownRule):
        def __init__(self, capital):
            super().__init__(capital); self.i = 0

        def update(self, prev_equity):
            m = super().update(prev_equity) * extra(self.i, prev_equity)
            self.i += 1; self.mult = m
            return m
    return Rule


class Universe:
    def __init__(self):
        self.stocks = data.load([s for s in data.ever_members() if s in data.cached_symbols()])
        self.closes = pd.DataFrame({s: d["Close"] for s, d in self.stocks.items()}).sort_index()
        self.index = data.load([rules.MARKET_INDEX])[rules.MARKET_INDEX]["Close"]
        self.member = data.member_table(self.closes.index, list(self.stocks))
        self.days = self.closes.index[self.closes.index >= pd.Timestamp(rules.START)]
        self._cache = {}

    def trades(self, buy_ok):
        key = (hash(tuple(buy_ok.fillna(False).astype(bool).to_numpy())), rules.supertrend_bullish)
        if key not in self._cache:
            out = []
            for sym, daily in self.stocks.items():
                for t in rules.stock_trades(daily, buy_ok):
                    if self.member.at[t["entry_date"], sym] and t["entry_date"] >= pd.Timestamp(rules.START):
                        out.append({"symbol": sym, **t})
            self._cache[key] = out
        return self._cache[key]

    def run(self, buy_ok, extra=lambda i, e: 1.0):
        orig = rules.DrawdownRule
        rules.DrawdownRule = wrap_dd(self.days, extra)
        try:
            curve, fills, _ = backtest.run(self.trades(buy_ok), self.closes)
        finally:
            rules.DrawdownRule = orig
        return curve["equity"]


def vol_extra(lookback, floor, cap):
    eqs, vols = [], []

    def f(i, prev_eq):
        eqs.append(prev_eq)
        if len(eqs) <= lookback + 1:
            return 1.0
        r = np.diff(np.log(eqs[-lookback - 1:]))
        v = r.std()
        vols.append(v)
        if len(vols) < 252 or v <= 0:
            return 1.0
        return float(np.clip(np.median(vols) / v, floor, cap))
    return f


def graded(index, slope_days, band):
    sma = rules.sma(index, rules.MARKET_SMA)
    ok = sma.notna()
    up_thr, dn_thr = sma * (1 + band), sma * (1 - band)
    above, state = [], False
    for c, u, d in zip(index, up_thr, dn_thr):
        if np.isnan(u):
            state = False
        elif c > u:
            state = True
        elif c < d:
            state = False
        above.append(state)
    above = pd.Series(above, index=index.index)
    rising = sma > sma.shift(slope_days)
    mult = (above.astype(float) + rising.astype(float)) / 2          # 1, 0.5 or 0
    return mult[ok].shift(1)


def ema_exit(span):
    def bullish(w, *_):
        return w["Close"] > rules.ema(w["Close"], span)
    return bullish


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ema", action="store_true", help="run the weekly EMA exit variants (V6) instead of V1/V2")
    ap.add_argument("--slip2", action="store_true", help="double slippage to 0.2%% per side")
    a = ap.parse_args()
    if a.slip2:
        rules.SLIPPAGE = 0.002
    u = Universe()
    base_ok = rules.market_ok(u.index)
    runs = {"Baseline": u.run(base_ok)}
    if a.ema:
        orig = rules.supertrend_bullish
        for span in (10, 21, 30):
            rules.supertrend_bullish = ema_exit(span)
            runs[f"V6 weekly EMA{span} exit"] = u.run(base_ok)
        rules.supertrend_bullish = orig
    for lb in (() if a.ema else (21, 63, 126)):
        for floor in (0.25, 0.5):
            for cap in (1.0, 1.5):
                runs[f"V1 vol lb{lb} floor{floor} cap{cap}"] = u.run(base_ok, vol_extra(lb, floor, cap))
    for sd in (() if a.ema else (10, 20, 40)):
        for band in (0.0, 0.02):
            g = graded(u.index, sd, band)
            gd = g.reindex(u.days, method="ffill").fillna(0).to_numpy()
            runs[f"V2 graded slope{sd} band{band}"] = u.run(g > 0, lambda i, e, gd=gd: gd[i])
    rows = []
    for name, eq in runs.items():
        for p, (s, e) in PERIODS.items():
            seg = eq.loc[s:e]
            rows.append({"variant": name, "period": p, **stats(seg)})
    df = pd.DataFrame(rows)
    out = ROOT / "reports" / f"regime_variants{'_ema' if a.ema else ''}{'_slip2' if a.slip2 else ''}.csv"
    df.to_csv(out, index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
    for p in PERIODS:
        print(f"\n== {p} ==")
        print(df[df.period == p].drop(columns="period").set_index("variant").round(2).to_string())
    fit = df[df.period == "Fit 2006-16"].set_index("variant")
    for fam in (("V6",) if a.ema else ("V1", "V2")):
        best = fit[fit.index.str.startswith(fam)].Calmar.idxmax()
        print(f"\nWalk-forward {fam}: picked on 2006-16 -> {best}")
        print(df[(df.variant.isin([best, "Baseline"])) & (df.period == "Hold 2017-26")].round(2).to_string(index=False))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
