"""Shared-capital portfolio simulation with fixed-risk position sizing.

Takes per-stock trades (from ema61.simulate with stop_at_low=True) and replays them on one
capital pool:
  qty = floor(risk_amount / (entry - stop)),   risk_amount = risk_pct * initial capital
  capped by available cash (qty reduced if the position costs more than the cash left)
  at most `max_positions` open trades; extra signals are skipped
Same-day order: exits first (frees cash/slots), then entries ranked by `rank`
('tightest' = smallest stop distance first, i.e. the largest positions).
Costs: fee + slippage per side, as in lib.costs.
"""
from dataclasses import dataclass
import numpy as np
import pandas as pd


@dataclass
class Fill:
    symbol: str
    entry_date: pd.Timestamp
    exit_date: pd.Timestamp | None
    qty: int
    entry: float
    exit: float | None
    stop: float
    cost: float          # cash paid incl. costs
    proceeds: float      # cash received incl. costs (or MTM at end)
    capped: bool         # qty reduced by cash
    side: int = 1        # 1 long, -1 short (stock futures)


def run(trades, closes: pd.DataFrame, capital=100_000.0, risk_pct=0.02, max_positions=4,
        fee=0.0, slip=0.0, rank="tightest", start=None, score: pd.DataFrame | None = None,
        seed: int | None = None, sector_of: dict | None = None, sector_cap: int | None = None,
        risk_mult: pd.Series | None = None, dd_rule: dict | None = None,
        cash_ret: pd.Series | None = None, compound: bool = False, pos_cap: float | None = None,
        pos_cap_entry: bool = False,
        short: dict | None = None, max_open_risk: float | None = None, hedge: dict | None = None, slip_of: dict | None = None,
        skip_log: list | None = None):
    """rank: order of same-day signals when slots are scarce.
         'tightest' smallest stop % first (default) | 'widest' largest stop % first
         'random'   shuffled with `seed`
         'score_tightest' highest score first, ties by smallest stop %
         'score'    highest value of score.at[entry day, symbol] first (NaN last); the score table
                    must only use data known before the entry day (shift it by one day)
       risk_mult: day -> multiplier of the risk per new trade (market/breadth/VIX sizing; known before the day)
       dd_rule:   {"halve": 10, "pause": 15, "pause_days": 21}: after a 10% fall from the equity high, new trades
                  at half risk until a new high; on reaching a 15% fall, no new trades for 21 trading days (once per
                  drawdown; re-armed at a new high). Uses the previous day's equity.
       Trades with weight < 1 (partial-exit legs) get that share of the risk; legs of one stock share a slot.
       cash_ret:  day -> return earned that day by uninvested cash (liquid fund / index ETF); applied to the
                  previous day's cash before the day's trades
       compound:  risk per trade = risk_pct x the previous day's equity (default: x the starting capital)
       pos_cap_entry: also limit a new long position to pos_cap x yesterday's equity when it is bought.
       pos_cap:   a long position worth more than this share of equity at a month's last close is trimmed back to
                  it at that close (the trimmed shares are booked as a separate fill)
       short:     settings for trades with side -1 (stock futures): {"fee": per side, "margin": 0.25 (share of
                  notional blocked as cash), "roll": 0.001 (per month held, of entry notional), "max": 6 (open
                  shorts)}. P&L = qty x (entry - exit); margin returns at exit.
       max_open_risk: skip a new trade if the open initial risk (sum of qty x |entry - stop|) would exceed this
                  share of equity
       hedge:     {"ratio": 1.0, "fee": per side, "regime": bool day series (True = hedge on, known before the day)}:
                  short NIFTY futures worth ratio x the long book while on; daily P&L = -notional x NIFTY return
       slip_of:   symbol -> slippage per side, overriding `slip` (e.g. heavier for microcaps)
       skip_log:  if a list, (day, trade, reason) is appended for every signal: taken, or skipped as held (same
                  stock already open), slots, short-max, paused (drawdown pause / zero risk), sector, open-risk, cash, too-small (risk buys < 1 share)
       sector_cap: at most this many open positions per sector (sector_of: symbol -> sector);
                   signals over the cap count as skipped."""
    risk_amt = capital * risk_pct
    sl = (lambda sym: slip_of.get(sym, slip)) if slip_of else (lambda sym: slip)
    # value open positions at the last known close: the combined table has dates on which
    # some stocks have no row (holidays/suspensions/data gaps); NaN must not count as 0
    closes = closes.ffill()
    sh = {"fee": fee, "margin": 0.25, "roll": 0.001, "max": 6, **(short or {})}
    side = lambda t: getattr(t, "side", 1)
    dist = lambda t: abs(t.entry - t.stop)
    trades = [t for t in trades if t.stop is not None and (t.entry - t.stop) * side(t) > 0
              and (start is None or t.entry_date >= pd.Timestamp(start))]
    by_entry: dict = {}
    for t in trades:
        by_entry.setdefault(t.entry_date, []).append(t)
    days = closes.index[closes.index >= (pd.Timestamp(start) if start else closes.index[0])]
    month_end = set(days[np.r_[days.month[1:] != days.month[:-1], True]])
    rng = np.random.default_rng(seed)
    cash, open_, fills, skipped = capital, {}, [], 0
    rows = []
    rm = risk_mult.reindex(days, method="ffill").fillna(1.0) if risk_mult is not None else None
    cr = cash_ret.reindex(days).fillna(0.0) if cash_ret is not None else None
    if hedge:
        from .engine import nifty_close
        nret = nifty_close().reindex(days, method="ffill").pct_change().fillna(0.0)
        hon = hedge["regime"].reindex(days, method="ffill").fillna(False).astype(bool)
        h_was = False
    peak, halved, prev_eq, pause_used, paused_left = capital, False, capital, False, 0
    prev_long = 0.0

    def close_out(t, f, day, px):
        nonlocal cash
        f.exit, f.exit_date = px, day
        if side(t) > 0:
            f.proceeds = f.qty * px * (1 - sl(t.symbol)) * (1 - fee)
        else:
            months = max((day - f.entry_date).days / 30.4, 0)
            pnl = f.qty * (f.entry * (1 - sl(t.symbol)) * (1 - sh["fee"]) - px * (1 + sl(t.symbol)) * (1 + sh["fee"])) \
                - f.qty * f.entry * sh["roll"] * np.ceil(months)
            f.proceeds = f.cost + pnl
        cash += f.proceeds
        fills.append(f)

    def value(t, f, px):
        if side(t) > 0:
            return f.qty * px
        return f.cost + f.qty * (f.entry - px)

    for day in days:
        if cr is not None:
            cash *= 1 + float(cr.at[day])
        if hedge:                                        # NIFTY short hedge on yesterday's long book
            if hon.at[day]:
                n = hedge.get("ratio", 1.0) * prev_long
                cash -= n * float(nret.at[day])
                if not h_was:
                    cash -= n * hedge.get("fee", 0.0003)
                if day in month_end:
                    cash -= n * 0.0005                   # monthly roll: slippage + fees
            h_was = bool(hon.at[day])
        # exits
        for key in [s for s, (t, f) in open_.items() if t.exit_date == day]:
            t, f = open_.pop(key)
            close_out(t, f, day, t.exit)
        # entries
        cands = by_entry.get(day, [])
        if rank == "tightest":
            cands = sorted(cands, key=lambda t: dist(t) / t.entry)
        elif rank == "widest":
            cands = sorted(cands, key=lambda t: -dist(t) / t.entry)
        elif rank == "random" and cands:
            cands = [cands[i] for i in rng.permutation(len(cands))]
        elif rank == "score":
            def _k(t):
                v = score.at[day, t.symbol] if t.symbol in score.columns and day in score.index else np.nan
                return np.inf if np.isnan(v) else -v
            cands = sorted(cands, key=_k)
        elif rank == "score_tightest":
            def _k2(t):
                v = score.at[day, t.symbol] if t.symbol in score.columns and day in score.index else np.nan
                return (np.inf if np.isnan(v) else -v, dist(t) / t.entry)
            cands = sorted(cands, key=_k2)
        mult = 1.0 if rm is None else float(rm.at[day])
        if dd_rule:
            peak = max(peak, prev_eq)
            dd = (1 - prev_eq / peak) * 100
            if prev_eq >= peak:
                halved, pause_used = False, False
            if dd >= dd_rule.get("halve", 10):
                halved = True
            if dd >= dd_rule.get("pause", 15) and not pause_used:
                pause_used, paused_left = True, dd_rule.get("pause_days", 21)
            if paused_left > 0:
                mult, paused_left = 0.0, paused_left - 1
            elif halved:
                mult *= 0.5
        held = {k.split("|")[0] for k in open_}
        open_risk = sum(f.qty * abs(f.entry - f.stop) for _, f in open_.values())
        for t in cands:
            key = f"{t.symbol}|{t.leg}"
            note = (lambda why: skip_log.append((day, t, why))) if skip_log is not None else (lambda why: None)
            if key in open_:
                note("held"); continue
            if t.symbol not in held and len(held) >= max_positions:
                skipped += 1; note("slots")
                continue
            if side(t) < 0 and t.symbol not in held and \
                    sum(1 for tt, _ in open_.values() if side(tt) < 0) >= sh["max"]:
                skipped += 1; note("short-max")
                continue
            if mult <= 0:
                skipped += 1; note("paused")
                continue
            if sector_cap is not None:
                sec = sector_of.get(t.symbol)
                if sec is not None and sum(sector_of.get(s) == sec for s in held) >= sector_cap:
                    skipped += 1; note("sector")
                    continue
            base = prev_eq * risk_pct if compound else risk_amt
            if side(t) < 0 and sh.get("risk_mult"):          # shorts sized smaller, e.g. 0.5 x the long risk
                base *= sh["risk_mult"]
            qty = int(base * mult * t.weight // dist(t))
            risk_cut = False
            if max_open_risk is not None:
                room = max_open_risk * prev_eq - open_risk
                q2 = min(qty, int(max(room, 0) // dist(t)))
                risk_cut, qty = q2 < qty, q2
            capped = False
            if side(t) > 0:
                px = t.entry * (1 + sl(t.symbol)) * (1 + fee)
                if pos_cap and pos_cap_entry:            # also cap the position at entry (not only at month end)
                    qty = min(qty, int(pos_cap * prev_eq // px))
                if qty * px > cash:
                    qty, capped = int(cash // px), True
                unit = px
            else:
                unit = t.entry * sh["margin"]
                if qty * unit > cash:
                    qty, capped = int(cash // unit), True
            if qty < 1:
                skipped += 1; note("open-risk" if risk_cut else "cash" if capped else "too-small")
                continue
            cost = qty * unit
            cash -= cost
            f = Fill(t.symbol, day, None, qty, t.entry, None, t.stop, cost, 0.0, capped)
            f.side = side(t)
            open_[key] = (t, f)
            note("taken")
            held.add(t.symbol)
            open_risk += qty * dist(t)
            if t.exit_date == day:                       # same-day stop/target
                del open_[key]
                close_out(t, f, day, t.exit)
                held = {k.split("|")[0] for k in open_}
        vals = {k: value(t, f, closes.at[day, t.symbol]) for k, (t, f) in open_.items()
                if not np.isnan(closes.at[day, t.symbol])}
        invested = sum(vals.values())
        eq = cash + invested
        if pos_cap and day in month_end:                 # trim oversized longs at the month's close
            for k, (t, f) in list(open_.items()):
                if side(t) > 0 and k in vals and vals[k] > pos_cap * eq:
                    px = closes.at[day, t.symbol]
                    n = f.qty - int(pos_cap * eq // px)
                    if 0 < n < f.qty:
                        part = Fill(t.symbol, f.entry_date, day, n, f.entry, px, f.stop, f.cost * n / f.qty,
                                    n * px * (1 - sl(t.symbol)) * (1 - fee), False)
                        part.side = 1
                        f.cost -= part.cost
                        f.qty -= n
                        cash += part.proceeds
                        fills.append(part)
            vals = {k: value(t, f, closes.at[day, t.symbol]) for k, (t, f) in open_.items()
                    if not np.isnan(closes.at[day, t.symbol])}
            invested = sum(vals.values())
        prev_eq = cash + invested
        prev_long = sum(v for k, v in vals.items() if side(open_[k][0]) > 0)
        rows.append((day, cash, invested, len({k.split("|")[0] for k in open_})))
    for key, (t, f) in open_.items():                   # mark open trades to market
        last = closes[t.symbol].dropna().iloc[-1]
        if side(t) > 0:
            f.proceeds = f.qty * last * (1 - sl(t.symbol)) * (1 - fee)
        else:
            f.proceeds = f.cost + f.qty * (f.entry - last)
        fills.append(f)
    curve = pd.DataFrame(rows, columns=["date", "cash", "invested", "positions"]).set_index("date")
    curve["equity"] = curve["cash"] + curve["invested"]
    curve["deployed"] = curve["invested"] / curve["equity"]
    return curve, fills, skipped


def summary(curve: pd.DataFrame, fills: list[Fill], skipped: int, capital: float,
            max_positions: int) -> dict:
    eq = curve["equity"]
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    fdf = pd.DataFrame([{"symbol": f.symbol, "entry_date": f.entry_date, "exit_date": f.exit_date, "cost": f.cost,
                         "proceeds": f.proceeds, "side": getattr(f, "side", 1)} for f in fills])
    ts = trade_stats(fdf, eq)
    return {
        "Final equity (Rs)": eq.iloc[-1],
        "CAGR %": ((eq.iloc[-1] / capital) ** (1 / yrs) - 1) * 100,
        "Max DD %": (eq / eq.cummax() - 1).min() * 100,
        "Trades taken": ts["Trades taken"],
        "Signals skipped": skipped,
        "Win %": ts["Win %"],
        "Avg trade %": ts["Avg trade %"],
        "Median trade %": ts["Median trade %"],
        "Avg hold days": ts["Avg hold days"],
        "Median hold days": ts["Median hold days"],
        "Avg position (Rs)": ts["Avg position (Rs)"],
        "Avg deployed %": curve["deployed"].mean() * 100,
        "Median deployed %": curve["deployed"].median() * 100,
        "Max deployed %": curve["deployed"].max() * 100,
        "Days with 0 positions %": (curve["positions"] == 0).mean() * 100,
        "Days all slots full %": (curve["positions"] >= max_positions).mean() * 100,
        "Avg open positions": curve["positions"].mean(),
        "Cash-capped entries %": np.mean([f.capped for f in fills]) * 100,
        "Worst trade (Rs)": ts["Worst trade (Rs)"],
        "Worst trade % of equity": ts["Worst trade % of equity"],
    }


TRADE_KEYS = ["symbol", "entry_date", "side"]


def trades(fdf: pd.DataFrame) -> pd.DataFrame:
    """One row per trade from fill rows: month-end position-cap trims and partial-profit legs of the same entry are
    summed back into their trade (they are booked as separate fills). Open trades are marked to market."""
    f = fdf.copy()
    if "side" not in f:
        f["side"] = 1
    f["side"] = f["side"].fillna(1)
    f["entry_date"] = pd.to_datetime(f["entry_date"])
    f["exit_date"] = pd.to_datetime(f["exit_date"])
    g = f.groupby(TRADE_KEYS, sort=False)
    t = g.agg(cost=("cost", "sum"), proceeds=("proceeds", "sum"), exit_date=("exit_date", "max"),
              legs=("cost", "size")).reset_index()
    t["open"] = g["exit_date"].apply(lambda x: x.isna().any()).to_numpy()
    t.loc[t.open, "exit_date"] = pd.NaT
    t["pnl"] = t.proceeds - t.cost
    t["ret"] = (t.proceeds / t.cost - 1) * 100
    return t


def trade_stats(fdf: pd.DataFrame, equity: pd.Series) -> dict:
    """Per-trade statistics (not per fill row). Worst trade is shown against equity on its entry day."""
    t = trades(fdf)
    last = equity.index[-1]
    held = (t.exit_date.fillna(last) - t.entry_date).dt.days
    i = t.pnl.idxmin()
    eq_in = equity[:t.entry_date[i]]
    eq_in = eq_in.iloc[-1] if len(eq_in) else equity.iloc[0]
    closed = t[~t.open]                       # Win % on closed trades only (as site/PDFs); open ones are not decided
    return {"Trades taken": len(t), "Win %": (closed.pnl > 0).mean() * 100 if len(closed) else np.nan, "Avg trade %": t.ret.mean(),
            "Median trade %": float(t.ret.median()), "Avg hold days": held.mean(),
            "Median hold days": float(held.median()), "Avg position (Rs)": t.cost.mean(),
            "Worst trade (Rs)": t.pnl[i], "Worst trade % of equity": t.pnl[i] / eq_in * 100}


def merge_fills(fdf: pd.DataFrame) -> pd.DataFrame:
    """Fill rows -> one row per trade with the same columns (qty, cost and proceeds summed; exit = quantity-weighted
    exit price; exit_date = last exit, or empty while any part is still open)."""
    if fdf.empty:
        return fdf
    f = fdf.copy()
    if "side" not in f:
        f["side"] = 1
    f["side"] = f["side"].fillna(1)
    keys = [k for k in TRADE_KEYS if k in f]
    f["_xq"] = f["exit"] * f["qty"]
    f["_open"] = f["exit_date"].isna()
    agg = {c: "first" for c in f.columns if c not in keys}
    agg.update(qty="sum", cost="sum", proceeds="sum", _xq="sum", _open="any", exit_date="max")
    if "capped" in f:
        agg["capped"] = "any"
    out = f.groupby(keys, sort=False, as_index=False).agg(agg)
    out["exit"] = out["_xq"] / out["qty"]
    out.loc[out["_open"], "exit_date"] = pd.NaT if pd.api.types.is_datetime64_any_dtype(out["exit_date"]) else None
    return out[[c for c in fdf.columns] + (["side"] if "side" not in fdf else [])].drop(columns=[], errors="ignore")


def read_fills(path, **kw) -> pd.DataFrame:
    """pd.read_csv of a fills_*.csv, merged to one row per trade (see merge_fills)."""
    return merge_fills(pd.read_csv(path, **kw))
