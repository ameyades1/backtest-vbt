"""Ranks 1-5 from reports/Candidate strategies 16 CAGR 30 drawdown.md, all on the release S44984096 engine
(point-in-time NIFTY 500, release costs and slippage, next-open fills, 10 slots, 20% cap, drawdown rule).

  R1 S44984096 + volatility sizing (V1: lb63, floor 0.25, cap 1.0 / lb21 cap 1.5) at 1.0 / 1.25 / 1.4% risk.
  R2 gated low-turnover momentum: quarterly top-N by 12-1 momentum or nearness to the 52-week high, buffer 2N,
     entries only when NIFTY 500 > 200-DMA, chandelier exit k x ATR(14) on the close, risk sized on that stop,
     optional volatility sizing.
  R3 low-vol sleeve: quarterly lowest-volatility N, buffer 2N, all positions sold when NIFTY 500 closes below its
     200-DMA, optional chandelier; alone and as a 50/50 capital split with S44984096 (two accounts, summed).
  R4 breakouts: close above the highest high of the prior L days (liquid member, market filter), next-open entry;
     exit on a close below the prior X-day low or a k x ATR chandelier; initial stop sizes the trade.
  R5 S44984096 with a sector or stock relative-strength filter vs NIFTY 50 at entry (sector = today's NSE industry
     label, equal-weight sector return from cached stocks; stocks with no label are not filtered).

Liquidity for R2-R4: 63-day median traded value >= Rs 2 crore. Walk-forward: fit 2006-16, hold out 2017-26.
    .venv/bin/python research/studies/rank_candidates.py [--slip2]
"""
import argparse, sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "research" / "studies"))
from regime_variants import Universe, PERIODS, stats, vol_extra, wrap_dd, rules, backtest, data  # noqa: E402
from indicators import atr  # noqa: E402  (release path already on sys.path)

LIQ = 2e7


class Lab(Universe):
    def __init__(self):
        super().__init__()
        self.cdays = self.closes.index
        f = lambda k: pd.DataFrame({s: d[k] for s, d in self.stocks.items()}).reindex(self.cdays)
        self.O, self.H, self.L, self.V = f("Open"), f("High"), f("Low"), f("Volume")
        self.C = self.closes.reindex(self.cdays)
        self.ATR = pd.DataFrame({s: atr(d, 14) for s, d in self.stocks.items()}).reindex(self.cdays)
        self.liq = (self.C * self.V).rolling(63, min_periods=40).median() >= LIQ
        sma = rules.sma(self.index, rules.MARKET_SMA)
        above = (self.index > sma)[sma.notna()]
        self.mkt_ok_next = above.reindex(self.cdays, method="ffill").fillna(False).to_numpy()   # signal day s -> buy s+1
        self.mkt_below = (~above).reindex(self.cdays, method="ffill").fillna(False).to_numpy()
        self.mem = self.member.reindex(self.cdays).fillna(False)
        q = self.cdays[self.cdays >= pd.Timestamp(rules.START) - pd.Timedelta(days=100)]
        qe = q[np.r_[q.quarter[1:] != q.quarter[:-1], True]]
        self.reb = np.isin(self.cdays, qe)

    def run_trades(self, trades, extra=lambda i, e: 1.0, capital=100_000.0):
        orig = rules.DrawdownRule
        rules.DrawdownRule = wrap_dd(self.days, extra)
        try:
            curve, fills, _ = backtest.run(trades, self.closes, capital)
        finally:
            rules.DrawdownRule = orig
        return curve["equity"]

    # ---- one stock: enter at the next open after each signal, exit by stop / close rule ------------------------
    def sim(self, sym, signals, stop_fn, close_exit, keep=None, mkt_exit=False):
        o, h, l, c = (x[sym].to_numpy() for x in (self.O, self.H, self.L, self.C))
        days, n, out, free = self.cdays, len(self.cdays), [], 0
        mem = self.mem[sym].to_numpy() if sym in self.mem else np.zeros(n, bool)
        for s in signals:
            k = s + 1
            if k < free or k >= n or np.isnan(o[k]) or not mem[k] or not self.mkt_ok_next[s]:
                continue
            entry = o[k]
            stop = stop_fn(s, entry)
            if not (stop < entry) or np.isnan(stop):
                continue
            ex, px, why, st = None, None, "open", {"peak": c[k]}
            if c[k] <= stop:
                ex, px, why = k, c[k], "stop-entry-day"
            else:
                for j in range(k + 1, n):
                    if np.isnan(o[j]):
                        continue
                    if o[j] <= stop:
                        ex, px, why = j, o[j], "stop-gap"; break
                    if l[j] <= stop:
                        ex, px, why = j, stop, "stop"; break
                    st["peak"] = max(st["peak"], c[j])
                    r = close_exit(j, st)
                    if not r and keep is not None and self.reb[j] and not keep(j):
                        r = "dropped"
                    if not r and mkt_exit and self.mkt_below[j]:
                        r = "market"
                    if r and j + 1 < n and not np.isnan(o[j + 1]):
                        ex, px, why = j + 1, o[j + 1], r; break
            out.append({"symbol": sym, "entry_date": days[k], "entry": entry, "stop": stop,
                        "exit_date": days[ex] if ex is not None else None, "exit": px, "reason": why})
            free = ex + 1 if ex is not None else n
        return [t for t in out if t["entry_date"] >= pd.Timestamp(rules.START)]

    def chand(self, sym, k):
        a = self.ATR[sym].to_numpy(); c = self.C[sym].to_numpy()
        return lambda j, st: "chandelier" if c[j] < st["peak"] - k * a[j] else None

    # ---- R2 / R3 cross-sectional selection --------------------------------------------------------------------
    def rotation(self, score, top, k, mkt_exit=False):
        """score: DataFrame, higher = better. Members, liquid, scored -> rank at quarter ends."""
        elig = self.mem & self.liq & score.notna()
        rank = score.where(elig).rank(axis=1, ascending=False)
        trades = []
        for sym in self.stocks:
            r = rank[sym].to_numpy()
            sig = np.flatnonzero(self.reb & (r <= top))
            if not len(sig):
                continue
            a = self.ATR[sym].to_numpy()
            kk = k if k else 3.0
            stop_fn = lambda s, e, a=a, kk=kk: e - kk * a[s]
            ce = self.chand(sym, k) if k else (lambda j, st: None)
            trades += self.sim(sym, sig, stop_fn, ce, keep=lambda j, r=r: r[j] <= 2 * top, mkt_exit=mkt_exit)
        return trades

    def breakouts(self, L, exit_kind):
        trades = []
        for sym in self.stocks:
            h, l, c = self.H[sym], self.L[sym], self.C[sym]
            hh = h.shift(1).rolling(L, min_periods=L).max().to_numpy()
            cv = c.to_numpy()
            ok = (cv > hh) & self.liq[sym].to_numpy() & self.mem[sym].to_numpy()
            sig = np.flatnonzero(ok & ~np.r_[False, ok[:-1]])                 # first day of a breakout
            if not len(sig):
                continue
            a = self.ATR[sym].to_numpy()
            if exit_kind.startswith("low"):
                X = int(exit_kind[3:])
                ll = l.shift(1).rolling(X, min_periods=X).min().to_numpy()
                stop_fn = lambda s, e, ll=ll, a=a: max(ll[s], e - 6 * a[s])  # initial stop: X-day low, at most 6 ATR
                ce = lambda j, st, ll=ll, cv=cv: "channel" if cv[j] < ll[j] else None
            else:
                kk = float(exit_kind[4:])
                stop_fn = lambda s, e, a=a, kk=kk: e - kk * a[s]
                ce = self.chand(sym, kk)
            trades += self.sim(sym, sig, stop_fn, ce)
        return trades

    def rs_filter(self, kind, lb):
        """Per-stock buy_allowed = market filter & relative strength vs NIFTY 50 over lb days (previous close)."""
        n50 = data.load(["^NSEI"])["^NSEI"]["Close"].reindex(self.cdays).ffill()
        n50r = n50 / n50.shift(lb) - 1
        rets = self.C / self.C.shift(lb) - 1
        base = rules.market_ok(self.index)
        allow = {}
        if kind == "stock":
            ok = rets.sub(n50r, axis=0) > 0
        else:
            ind = pd.read_csv(ROOT / "data" / "nifty500_list.csv").set_index("Symbol")["Industry"]
            lab = {s: ind.get(s.replace(".NS", ""), None) for s in self.stocks}
            dret = self.C.pct_change(fill_method=None).where(self.mem)
            sect = {}
            for g in {v for v in lab.values() if v}:
                cols = [s for s, v in lab.items() if v == g]
                idx = (1 + dret[cols].mean(axis=1).fillna(0)).cumprod()
                sect[g] = idx / idx.shift(lb) - 1
            sect = pd.DataFrame(sect)
            if kind == "sector":
                sok = sect.sub(n50r, axis=0) > 0
            else:                                                            # top half of sectors
                sok = sect.rank(axis=1, pct=True) > 0.5
            ok = pd.DataFrame({s: sok[lab[s]] if lab[s] else True for s in self.stocks}, index=self.cdays)
        ok = ok.shift(1).fillna(False)
        for s in self.stocks:
            allow[s] = (base.reindex(self.cdays).fillna(False).astype(bool) & ok[s].astype(bool))
        return allow

    def filtered_trades(self, allow):
        out = []
        for sym, daily in self.stocks.items():
            for t in rules.stock_trades(daily, allow[sym]):
                if self.member.at[t["entry_date"], sym] and t["entry_date"] >= pd.Timestamp(rules.START):
                    out.append({"symbol": sym, **t})
        return out


def with_risk(risk, fn):
    old = rules.RISK; rules.RISK = risk
    try:
        return fn()
    finally:
        rules.RISK = old


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slip2", action="store_true")
    a = ap.parse_args()
    if a.slip2:
        rules.SLIPPAGE = 0.002
    u = Lab()
    base_ok = rules.market_ok(u.index)
    base_tr = u.trades(base_ok)
    runs = {}
    runs["Baseline S44984096"] = u.run_trades(base_tr)
    # R1
    for risk in (0.01, 0.0125, 0.014):
        runs[f"R1 risk{risk*100:.2f} vol63"] = with_risk(risk, lambda: u.run_trades(base_tr, vol_extra(63, 0.25, 1.0)))
        runs[f"R1 risk{risk*100:.2f} vol21cap1.5"] = with_risk(risk, lambda: u.run_trades(base_tr, vol_extra(21, 0.25, 1.5)))
    runs["R1 risk1.25 no vol"] = with_risk(0.0125, lambda: u.run_trades(base_tr))
    # R2
    mom = u.C.shift(21) / u.C.shift(252) - 1
    h52 = u.C / u.H.rolling(252, min_periods=200).max()
    for name, sc in (("mom12-1", mom), ("52wh", h52)):
        for k in (3.0, 4.0):
            tr = u.rotation(sc, 10, k)
            runs[f"R2 {name} k{k:g}"] = u.run_trades(tr)
            runs[f"R2 {name} k{k:g} vol63"] = u.run_trades(tr, vol_extra(63, 0.25, 1.0))
    # R3
    lowvol = {}
    for lb in (126, 252):
        vol = -u.C.pct_change(fill_method=None).rolling(lb, min_periods=int(lb * .8)).std()
        for k in (None, 4.0):
            tr = u.rotation(vol, 10, k, mkt_exit=True)
            nm = f"R3 lowvol lb{lb} {'k4' if k else 'nochand'}"
            runs[nm] = u.run_trades(tr)
            lowvol[nm] = tr
    for nm, tr in lowvol.items():
        s_half = u.run_trades(base_tr, capital=50_000.0)
        l_half = u.run_trades(tr, capital=50_000.0)
        runs[f"R3 combo 50/50 S44984096 + {nm[3:]}"] = s_half + l_half
        s_half = with_risk(0.0125, lambda: u.run_trades(base_tr, vol_extra(63, 0.25, 1.0), capital=50_000.0))
        l_half = with_risk(0.0125, lambda: u.run_trades(tr, capital=50_000.0))
        runs[f"R3 combo 50/50 @1.25% + vol63 + {nm[3:]}"] = s_half + l_half
    # R4
    for L in (150, 250):
        for ex in ("low50", "low100", "chan4"):
            runs[f"R4 breakout{L} {ex}"] = u.run_trades(u.breakouts(L, ex))
    # R5
    for kind, lb in (("sector", 126), ("sector", 63), ("tophalf", 126), ("stock", 126)):
        runs[f"R5 {kind} RS{lb}"] = u.run_trades(u.filtered_trades(u.rs_filter(kind, lb)))

    base_r = runs["Baseline S44984096"].pct_change()
    rows = []
    for name, eq in runs.items():
        corr = eq.pct_change().corr(base_r)
        for p, (s, e) in PERIODS.items():
            rows.append({"variant": name, "period": p, **stats(eq.loc[s:e]), "corr": corr})
    df = pd.DataFrame(rows)
    out = ROOT / "reports" / ("rank_candidates_slip2.csv" if a.slip2 else "rank_candidates.csv")
    df.to_csv(out, index=False)
    pd.set_option("display.width", 250); pd.set_option("display.max_rows", 500)
    for p in PERIODS:
        print(f"\n== {p} ==")
        print(df[df.period == p].drop(columns="period").set_index("variant").round(2).to_string())
    fit = df[df.period == "Fit 2006-16"].set_index("variant")
    for fam in ("R1", "R2", "R3 lowvol", "R3 combo", "R4", "R5"):
        best = fit[fit.index.str.startswith(fam)].Calmar.idxmax()
        print(f"\nWalk-forward {fam}: picked on 2006-16 -> {best}")
        print(df[(df.variant.isin([best, "Baseline S44984096"])) & (df.period == "Hold 2017-26")].round(2).to_string(index=False))
    print(f"\nwrote {out}")


if __name__ == "__main__":
    main()
