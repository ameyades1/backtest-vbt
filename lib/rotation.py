"""Monthly momentum rotation (portfolio-level strategy, not per-stock signals).
Config: setup {"type": "momentum_rotation", "top": 10, "lookback": 252, "skip": 21, "buffer": 2,
               "sma": 200, "market_sma": 200}
On the first trading day of each month, using closes up to the previous day:
  score = Close[t-skip] / Close[t-lookback] - 1  (12-1 month momentum), only stocks above their `sma`-day SMA
  hold the `top` best; a held stock is kept while its rank <= top x buffer (cuts turnover)
  market_sma: while NIFTY 50 is below its N-day SMA, no new buys (held stocks still exit by rank/SMA)
Trades fill at that day's Open, equal weight = equity / top per new position; costs per side as lib.costs.
Uses current index constituents (survivorship bias, as every run in this repo).
"""
import numpy as np
import pandas as pd
from .portfolio import Fill
from . import engine


def run(cfg, closes, dailies, capital, fee, slip, start, cash_ret=None):
    s = cfg["setup"]
    top, lb, skip, buf = s.get("top", 10), s.get("lookback", 252), s.get("skip", 21), s.get("buffer", 2)
    c = closes.ffill()
    o = pd.DataFrame({k: d["Open"] for k, d in dailies.items()}).reindex(c.index)
    mom = (c.shift(skip) / c.shift(lb) - 1).shift(1)
    above = (c > c.rolling(s.get("sma", 200), min_periods=s.get("sma", 200)).mean()).shift(1, fill_value=False)
    mkt_ok = pd.Series(True, index=c.index)
    if s.get("market_sma"):
        n = engine.nifty_close().reindex(c.index, method="ffill")
        mkt_ok = (n > n.rolling(s["market_sma"]).mean()).shift(1, fill_value=True)
    days = c.index[c.index >= pd.Timestamp(start)]
    month_start = set(days[np.r_[True, days.month[1:] != days.month[:-1]]])
    cr = cash_ret.reindex(days).fillna(0.0) if cash_ret is not None else None
    cash, pos, fills, rows = float(capital), {}, [], []

    def sell(sym, day, px):
        nonlocal cash
        f = pos.pop(sym)
        f.exit, f.exit_date = px, day
        f.proceeds = f.qty * px * (1 - slip) * (1 - fee)
        cash += f.proceeds
        fills.append(f)

    for day in days:
        if cr is not None:
            cash *= 1 + float(cr.at[day])
        if day in month_start:
            m = mom.loc[day].where(above.loc[day]).dropna().sort_values(ascending=False)
            rank = {k: i + 1 for i, k in enumerate(m.index)}
            for sym in list(pos):
                px = o.at[day, sym]
                if rank.get(sym, 10**9) > top * buf and not np.isnan(px):
                    sell(sym, day, px)
            if mkt_ok.loc[day]:
                eq = cash + sum(f.qty * c.at[day, k] for k, f in pos.items())
                for sym in m.index[:top]:
                    if len(pos) >= top:
                        break
                    px = o.at[day, sym]
                    if sym in pos or np.isnan(px):
                        continue
                    unit = px * (1 + slip) * (1 + fee)
                    qty = int(min(eq / top, cash) // unit)
                    if qty < 1:
                        continue
                    cash -= qty * unit
                    pos[sym] = Fill(sym, day, None, qty, px, None, np.nan, qty * unit, 0.0, False)
        inv = sum(f.qty * c.at[day, k] for k, f in pos.items() if not np.isnan(c.at[day, k]))
        rows.append((day, cash, inv, len(pos)))
    for k, f in pos.items():
        f.proceeds = f.qty * c[k].dropna().iloc[-1] * (1 - slip) * (1 - fee)
        fills.append(f)
    curve = pd.DataFrame(rows, columns=["date", "cash", "invested", "positions"]).set_index("date")
    curve["equity"] = curve["cash"] + curve["invested"]
    curve["deployed"] = curve["invested"] / curve["equity"]
    return curve, fills, 0
