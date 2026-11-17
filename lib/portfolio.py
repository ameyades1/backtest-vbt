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


def run(trades, closes: pd.DataFrame, capital=100_000.0, risk_pct=0.02, max_positions=4,
        fee=0.0, slip=0.0, rank="tightest", start=None, score: pd.DataFrame | None = None,
        seed: int | None = None, sector_of: dict | None = None, sector_cap: int | None = None):
    """rank: order of same-day signals when slots are scarce.
         'tightest' smallest stop % first (default) | 'widest' largest stop % first
         'random'   shuffled with `seed`
         'score_tightest' highest score first, ties by smallest stop %
         'score'    highest value of score.at[entry day, symbol] first (NaN last); the score table
                    must only use data known before the entry day (shift it by one day)
       sector_cap: at most this many open positions per sector (sector_of: symbol -> sector);
                   signals over the cap count as skipped."""
    risk_amt = capital * risk_pct
    # value open positions at the last known close: the combined table has dates on which
    # some stocks have no row (holidays/suspensions/data gaps); NaN must not count as 0
    closes = closes.ffill()
    trades = [t for t in trades if t.stop is not None and t.entry > t.stop
              and (start is None or t.entry_date >= pd.Timestamp(start))]
    by_entry: dict = {}
    for t in trades:
        by_entry.setdefault(t.entry_date, []).append(t)
    days = closes.index[closes.index >= (pd.Timestamp(start) if start else closes.index[0])]
    rng = np.random.default_rng(seed)
    cash, open_, fills, skipped = capital, {}, [], 0
    rows = []
    for day in days:
        # exits
        for sym in [s for s, (t, f) in open_.items() if t.exit_date == day]:
            t, f = open_.pop(sym)
            f.exit, f.exit_date = t.exit, day
            f.proceeds = f.qty * t.exit * (1 - slip) * (1 - fee)
            cash += f.proceeds
            fills.append(f)
        # entries
        cands = by_entry.get(day, [])
        if rank == "tightest":
            cands = sorted(cands, key=lambda t: (t.entry - t.stop) / t.entry)
        elif rank == "widest":
            cands = sorted(cands, key=lambda t: -(t.entry - t.stop) / t.entry)
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
                return (np.inf if np.isnan(v) else -v, (t.entry - t.stop) / t.entry)
            cands = sorted(cands, key=_k2)
        for t in cands:
            if t.symbol in open_:
                continue
            if len(open_) >= max_positions:
                skipped += 1
                continue
            if sector_cap is not None:
                sec = sector_of.get(t.symbol)
                if sec is not None and sum(sector_of.get(s) == sec for s in open_) >= sector_cap:
                    skipped += 1
                    continue
            px = t.entry * (1 + slip) * (1 + fee)
            qty = int(risk_amt // (t.entry - t.stop))
            capped = False
            if qty * px > cash:
                qty, capped = int(cash // px), True
            if qty < 1:
                skipped += 1
                continue
            cost = qty * px
            cash -= cost
            f = Fill(t.symbol, day, None, qty, t.entry, None, t.stop, cost, 0.0, capped)
            open_[t.symbol] = (t, f)
            if t.exit_date == day:                       # same-day stop/target
                f.exit, f.exit_date = t.exit, day
                f.proceeds = qty * t.exit * (1 - slip) * (1 - fee)
                cash += f.proceeds
                fills.append(f)
                del open_[t.symbol]
        invested = sum(f.qty * closes.at[day, s] for s, (t, f) in open_.items()
                       if not np.isnan(closes.at[day, s]))
        rows.append((day, cash, invested, len(open_)))
    for sym, (t, f) in open_.items():                   # mark open trades to market
        last = closes[sym].dropna().iloc[-1]
        f.proceeds = f.qty * last * (1 - slip) * (1 - fee)
        fills.append(f)
    curve = pd.DataFrame(rows, columns=["date", "cash", "invested", "positions"]).set_index("date")
    curve["equity"] = curve["cash"] + curve["invested"]
    curve["deployed"] = curve["invested"] / curve["equity"]
    return curve, fills, skipped


def summary(curve: pd.DataFrame, fills: list[Fill], skipped: int, capital: float,
            max_positions: int) -> dict:
    eq = curve["equity"]
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    pnl = np.array([f.proceeds - f.cost for f in fills])
    ret = np.array([f.proceeds / f.cost - 1 for f in fills]) * 100
    last = curve.index[-1]
    held = np.array([((f.exit_date or last) - f.entry_date).days for f in fills])
    val = np.array([f.cost for f in fills])
    return {
        "Final equity (Rs)": eq.iloc[-1],
        "CAGR %": ((eq.iloc[-1] / capital) ** (1 / yrs) - 1) * 100,
        "Max DD %": (eq / eq.cummax() - 1).min() * 100,
        "Trades taken": len(fills),
        "Signals skipped": skipped,
        "Win %": (pnl > 0).mean() * 100,
        "Avg trade %": ret.mean(),
        "Median trade %": float(np.median(ret)),
        "Avg hold days": held.mean(),
        "Median hold days": float(np.median(held)),
        "Avg position (Rs)": val.mean(),
        "Avg deployed %": curve["deployed"].mean() * 100,
        "Median deployed %": curve["deployed"].median() * 100,
        "Max deployed %": curve["deployed"].max() * 100,
        "Days with 0 positions %": (curve["positions"] == 0).mean() * 100,
        "Days all slots full %": (curve["positions"] >= max_positions).mean() * 100,
        "Avg open positions": curve["positions"].mean(),
        "Cash-capped entries %": np.mean([f.capped for f in fills]) * 100,
        "Worst trade (Rs)": pnl.min(),
        "Worst trade % of capital": pnl.min() / capital * 100,
    }
