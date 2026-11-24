"""S44984096 backtest: point-in-time NIFTY 500, July 2006 to the latest data, costs included.

    python backtest.py                 -> out/trades.csv, out/equity.csv and a summary on screen
    python backtest.py --capital 1000000

Each day, in this order: idle cash earns the liquid-fund rate; trades due to exit today are sold; new trades are
bought (tightest stop first) while slots, the drawdown rule and cash allow; positions are valued at the close;
at a month's last close any position above 20% of equity is trimmed.
"""
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
import data
import rules

OUT = Path(__file__).resolve().parent / "out"


def all_trades():
    """(trades the rules give on every stock while it was in NIFTY 500, closes table of all those stocks)."""
    stocks = data.load([s for s in data.ever_members() if s in data.cached_symbols()])
    closes = pd.DataFrame({s: d["Close"] for s, d in stocks.items()}).sort_index()
    index = data.load([rules.MARKET_INDEX])[rules.MARKET_INDEX]["Close"]
    buy_ok = rules.market_ok(index)
    member = data.member_table(closes.index, list(stocks))
    trades = []
    for sym, daily in stocks.items():
        for t in rules.stock_trades(daily, buy_ok):
            if member.at[t["entry_date"], sym] and t["entry_date"] >= pd.Timestamp(rules.START):
                trades.append({"symbol": sym, **t})
    return trades, closes


def run(trades, closes, capital=100_000.0):
    closes = closes.ffill()
    days = closes.index[closes.index >= pd.Timestamp(rules.START)]
    month_end = set(days[np.r_[days.month[1:] != days.month[:-1], True]])
    by_day = {}
    for t in trades:
        by_day.setdefault(t["entry_date"], []).append(t)
    daily_rate = (1 + rules.LIQUID_RATE / 100) ** (1 / 252) - 1
    dd = rules.DrawdownRule(capital)
    cash, prev_eq, skipped = capital, capital, 0
    open_, fills, curve = {}, [], []          # open_: symbol -> position dict

    def sell(p, day, px, qty=None):
        nonlocal cash
        q = p["qty"] if qty is None else qty
        f = {**p, "qty": q, "exit_date": day, "exit": px, "proceeds": rules.sell_value(q, px),
             "cost": p["cost"] * q / p["qty"]}
        cash += f["proceeds"]
        fills.append(f)
        return f

    for day in days:
        cash *= 1 + daily_rate
        for sym in [s for s, p in open_.items() if p["t"]["exit_date"] == day]:      # exits first
            p = open_.pop(sym)
            sell(p, day, p["t"]["exit"])
        mult = dd.update(prev_eq)
        for t in sorted(by_day.get(day, []), key=lambda t: (t["entry"] - t["stop"]) / t["entry"]):
            if t["symbol"] in open_:
                continue
            if len(open_) >= rules.MAX_POSITIONS or mult <= 0:
                skipped += 1; continue
            qty, capped = rules.shares(prev_eq, mult, t["entry"], t["stop"], cash)
            if qty < 1:
                skipped += 1; continue
            cost = qty * rules.buy_price(t["entry"])
            cash -= cost
            p = {"symbol": t["symbol"], "entry_date": day, "qty": qty, "entry": t["entry"], "stop": t["stop"],
                 "cost": cost, "capped": capped, "reason": t["reason"], "t": t}
            if t["exit_date"] == day:                                                 # closed below the stop
                sell(p, day, t["exit"])
            else:
                open_[t["symbol"]] = p
        value = lambda: sum(p["qty"] * closes.at[day, s] for s, p in open_.items() if not np.isnan(closes.at[day, s]))
        equity = cash + value()
        if day in month_end:                                                          # 20% cap at month end
            for s, p in open_.items():
                px = closes.at[day, s]
                n = rules.trim(p["qty"], px, equity) if not np.isnan(px) and p["qty"] * px > rules.POS_CAP * equity else 0
                if n:
                    f = sell(p, day, px, n)
                    f["reason"] = "trim 20%"
                    p["cost"] -= f["cost"]
                    p["qty"] -= n
            equity = cash + value()
        prev_eq = equity
        curve.append((day, cash, equity, len(open_)))
    for s, p in open_.items():                                                        # still open: at last close
        f = {**p, "exit_date": None, "exit": None, "proceeds": rules.sell_value(p["qty"], closes[s].dropna().iloc[-1])}
        fills.append(f)
    curve = pd.DataFrame(curve, columns=["date", "cash", "equity", "positions"]).set_index("date")
    fills = pd.DataFrame(fills).drop(columns="t")
    return curve, fills, skipped


def summary(curve, fills, capital):
    eq = curve["equity"]
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    by_trade = fills.groupby(["symbol", "entry_date"]).agg(cost=("cost", "sum"), proceeds=("proceeds", "sum"),
                                                          open=("exit_date", lambda x: x.isna().any()))
    closed = by_trade[~by_trade.open]
    return {"CAGR %": ((eq.iloc[-1] / capital) ** (1 / years) - 1) * 100,
            "Max DD %": (eq / eq.cummax() - 1).min() * 100,
            "Trades": len(by_trade), "Open": int(by_trade.open.sum()),
            "Win % (closed)": (closed.proceeds > closed.cost).mean() * 100,
            "Final equity": eq.iloc[-1]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--capital", type=float, default=100_000.0)
    a = ap.parse_args()
    trades, closes = all_trades()
    curve, fills, skipped = run(trades, closes, a.capital)
    OUT.mkdir(exist_ok=True)
    fills.to_csv(OUT / "trades.csv", index=False)
    curve.to_csv(OUT / "equity.csv")
    s = summary(curve, fills, a.capital)
    print(f"S44984096 {curve.index[0]:%d %b %Y} to {curve.index[-1]:%d %b %Y}: signals {len(trades)}, "
          f"skipped {skipped}")
    for k, v in s.items():
        print(f"  {k:16} {v:,.2f}")


if __name__ == "__main__":
    main()
