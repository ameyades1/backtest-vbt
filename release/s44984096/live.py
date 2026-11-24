"""S44984096 daily assistant. Run after the close; it prints tomorrow's to-do list and saves it as a PDF.
It uses the same rule functions as backtest.py (rules.py), so the orders match the backtest.

    python live.py init --capital 1000000
    python live.py report [--date 2026-11-30] [--refresh]
    python live.py buy  HDFCBANK 1650.5 120 [--date 2026-12-02]   # stop = last completed week's low
    python live.py sell HDFCBANK 1702 [--qty 40] [--why "time stop"]
    python live.py cash 1003250                                    # match your broker's cash

--dir chooses the account folder (default: live/ at the repo root, same files as the research live.py).
No broker connection: you place the orders and record fills with buy / sell.
"""
import argparse, json, sys
from datetime import date as _date
from pathlib import Path
import numpy as np
import pandas as pd
import data, rules
from indicators import to_weekly, to_monthly, sma, supertrend_bullish

ROOT = Path(__file__).resolve().parents[2]
NOT_STOCKS = {"BIRET.NS", "EMBASSY.NS", "BAGMANE.NS"}        # REITs / no Yahoo data in the NIFTY 500 list
COLS = ["symbol", "entry_date", "entry", "stop", "qty", "tstop_done", "ref_close"]


def tradeable(syms):
    return {s for s in syms if s not in NOT_STOCKS and not s.upper().startswith("DUMMY")}


def be_series():
    """NIFTY 500 stocks NSE trades in the BE (trade-for-trade) series: delivery only, tighter bands."""
    c = pd.read_csv(data.CONS / "NIFTY500.csv")
    return {f"{s.strip()}.NS" for s, x in zip(c["Symbol"], c["Series"]) if str(x).strip() != "EQ"}


# ---- account files ---------------------------------------------------------------------------------------------
def files(d):
    d = Path(d); d.mkdir(parents=True, exist_ok=True)
    return d / "state.json", d / "positions.csv", d / "orders.csv", d / "journal.csv"


def load(d):
    sp, pp, op, _ = files(d)
    if not sp.exists():
        sys.exit(f"no account in {d}: run  python live.py init --capital 1000000")
    pos = pd.read_csv(pp, parse_dates=["entry_date"]) if pp.exists() else pd.DataFrame(columns=COLS)
    for c in COLS:
        if c not in pos:
            pos[c] = np.nan
    od = pd.read_csv(op, parse_dates=["setup_month", "valid_until"]) if op.exists() and op.stat().st_size > 2 \
        else pd.DataFrame()
    return json.load(open(sp)), pos, od


def save(d, st, pos, od=None):
    sp, pp, op, _ = files(d)
    json.dump(st, open(sp, "w"), indent=1, default=str)
    pos.to_csv(pp, index=False)
    if od is not None:
        od.to_csv(op, index=False)


def journal(d, day, action, symbol="", price="", qty="", note=""):
    jp = files(d)[3]
    pd.DataFrame([dict(date=str(pd.Timestamp(day).date()), action=action, symbol=symbol, price=price, qty=qty,
                       note=note)]).to_csv(jp, mode="a", header=not jp.exists(), index=False)


def daily(sym, upto):
    return data.load([sym])[sym][:upto]


def stop_for(df, day):
    """Stop for a buy on `day`: low of the last weekly candle that ended before that day."""
    w = to_weekly(df[df.index < day])
    w = w[w.index < day]
    return float(w["Low"].iat[-1]), w.index[-1]


def sym_of(s):
    return s if s.endswith(".NS") else f"{s.upper()}.NS"


# ---- commands --------------------------------------------------------------------------------------------------
def cmd_init(a):
    if files(a.dir)[0].exists() and not a.force:
        sys.exit("account exists; use --force to start over")
    st = {"capital": a.capital, "cash": a.capital, "peak": a.capital, "halved": False, "pause_used": False,
          "pause_left": 0, "last_report": None, "started": a.date or str(_date.today())}
    save(a.dir, st, pd.DataFrame(columns=COLS), pd.DataFrame())
    journal(a.dir, st["started"], "init", note=f"capital {a.capital:,.0f}")
    print(f"account created in {a.dir} with Rs {a.capital:,.0f}")


def cmd_buy(a):
    st, pos, od = load(a.dir)
    sym, day = sym_of(a.symbol), pd.Timestamp(a.date or _date.today())
    df = daily(sym, day)
    stop, wk = stop_for(df, day)
    if stop >= a.price:
        sys.exit(f"stop {stop:.2f} (week ending {wk:%d %b}) is not below the price: the rules skip this trade")
    st["cash"] -= a.qty * a.price * (1 + rules.FEE)                            # your fill price includes slippage
    ref = float(df["Close"].iat[-1]) if len(df) and df.index[-1] == day else np.nan
    pos = pd.concat([pos, pd.DataFrame([{"symbol": sym, "entry_date": day, "entry": a.price, "stop": stop,
                                         "qty": a.qty, "tstop_done": False, "ref_close": ref}])], ignore_index=True)
    if len(od):
        od = od[od.symbol != sym]
    save(a.dir, st, pos, od)
    check = day + pd.Timedelta(days=rules.TIME_STOP_DAYS)
    journal(a.dir, day, "buy", sym, a.price, a.qty, f"stop {stop:.2f}; 25-day check {check:%d %b %Y}")
    print(f"bought {a.qty} {sym} at {a.price}.\n"
          f"  Stop {stop:.2f} (low of week ending {wk:%d %b}). Arm it from the NEXT session: place the GTT after "
          f"today's close.\n  If today closes at or below {stop:.2f}, sell at the close / next open instead.\n"
          f"  Time-stop check: first trading day on or after {check:%a %d %b %Y}.")


def cmd_sell(a):
    st, pos, _ = load(a.dir)
    sym, day = sym_of(a.symbol), pd.Timestamp(a.date or _date.today())
    i = pos.index[pos.symbol == sym]
    if not len(i):
        sys.exit(f"{sym} is not held")
    i = i[0]
    q = a.qty or int(pos.at[i, "qty"])
    p = pos.loc[i]
    r = (a.price - p.entry) / (p.entry - p.stop)
    st["cash"] += q * a.price * (1 - rules.FEE)
    pnl = q * (a.price * (1 - rules.FEE) - p.entry * (1 + rules.FEE))
    if q >= p.qty:
        pos = pos.drop(i).reset_index(drop=True)
    else:
        pos.at[i, "qty"] = p.qty - q
    save(a.dir, st, pos)
    journal(a.dir, day, "sell", sym, a.price, q, f"{a.why or ''}; {r:+.2f}R; net Rs {pnl:,.0f}")
    print(f"sold {q} {sym} at {a.price}: {r:+.2f}R, about Rs {pnl:,.0f} after costs")


def cmd_cash(a):
    st, pos, _ = load(a.dir)
    st["cash"] = a.amount
    save(a.dir, st, pos)
    journal(a.dir, _date.today(), "cash", note=f"set to {a.amount:,.0f}")
    print(f"cash set to Rs {a.amount:,.0f}")


# ---- corporate actions on open positions -------------------------------------------------------------------------
def corporate_actions(pos, day, since=None):
    """Yahoo adjusts history after a split or bonus, so the entry day's close in the data stops matching the one
    recorded at entry. A standard ratio -> adjust entry, stop and quantity. Also flag overnight drops of more than
    30% since the last report (at least the last 5 days) and after entry: demerger or bad news, your decision."""
    notes = []
    for i, p in pos.iterrows():
        df = daily(p.symbol, day)
        if np.isnan(p.ref_close) or p.entry_date not in df.index:
            if p.entry_date in df.index:
                pos.at[i, "ref_close"] = df.at[p.entry_date, "Close"]
            continue
        r = p.ref_close / df.at[p.entry_date, "Close"]
        if r >= 1.15:
            k = min(data.RATIOS, key=lambda x: abs(r / x - 1))
            if abs(r / k - 1) <= 0.06:
                pos.loc[i, ["entry", "stop", "ref_close"]] = [p.entry / k, p.stop / k, p.ref_close / k]
                pos.at[i, "qty"] = int(round(p.qty * k))
                notes.append((p.symbol, "RE-PLACE STOP", f"split/bonus x{k:g}: stop now {p.stop / k:,.2f} for "
                              f"{int(round(p.qty * k))} shares (entry {p.entry / k:,.2f}). Bonus shares may reach your "
                              f"demat a few days later: protect the shares you hold now."))
                continue
            notes.append((p.symbol, "CHECK", f"history changed by x{r:.2f} (not a standard ratio): check the "
                                             f"corporate action and the stop by hand"))
        gap = (df["Open"] / df["Close"].shift() - 1)[df.index > p.entry_date]
        start = min(pd.Timestamp(since), df.index[-5]) if since else df.index[-5]
        gap = gap[gap.index >= start]
        if len(gap) and (gap < -0.30).any():
            notes.append((p.symbol, "DECIDE", f"opened {gap.min() * 100:.0f}% below the previous close on "
                          f"{gap.idxmin():%d %b}: demerger or event? The stop may not apply; decide by hand"))
    return notes


# ---- the daily report ------------------------------------------------------------------------------------------
def cmd_report(a):
    st, pos, od = load(a.dir)
    if a.refresh:
        syms = tradeable(data.members_on(pd.Timestamp.today())) | set(pos.symbol) | {rules.MARKET_INDEX}
        print(f"downloading {len(syms)} symbols from Yahoo ...")
        data.refresh(syms)
    idx = data.load([rules.MARKET_INDEX])[rules.MARKET_INDEX]["Close"]
    td = idx.index
    day = td[td <= pd.Timestamp(a.date)][-1] if a.date else td[-1]
    nxt = td[td > day]
    tomorrow = nxt[0] if len(nxt) else data.next_trading_day(day)
    warn = []
    if not len(nxt) and tomorrow.year not in data.HOLIDAYS:
        warn.append(f"No NSE holiday list for {tomorrow.year} in data.py: add it (next day assumed {tomorrow:%d %b}).")
    week_end = tomorrow.to_period("W-FRI") != day.to_period("W-FRI")
    month_end = tomorrow.month != day.month

    buy_ok = rules.market_ok(idx)
    mk_tomorrow = bool((idx > sma(idx, rules.MARKET_SMA))[:day].iat[-1])           # today's close decides tomorrow
    acts = corporate_actions(pos, day, st.get("last_report"))

    # positions and equity at today's close
    pv = []
    for _, p in pos.iterrows():
        c = float(daily(p.symbol, day)["Close"].iat[-1])
        pv.append({**p, "close": c, "value": p.qty * c, "R": (c - p.entry) / (p.entry - p.stop)})
    pv = pd.DataFrame(pv)
    equity = st["cash"] + (pv.value.sum() if len(pv) else 0.0)

    # drawdown rule, once per trading day (same rule as the backtest, on today's equity)
    if st.get("last_report") != str(day.date()):
        dd = rules.DrawdownRule(st["peak"])
        dd.halved, dd.pause_used = st["halved"], st["pause_used"]
        n = len(td[(td > pd.Timestamp(st["last_report"])) & (td <= day)]) if st.get("last_report") else 1
        dd.pause_left = max(0, st["pause_left"] - (n - 1))
        dd.update(equity)
        st.update(peak=dd.peak, halved=dd.halved, pause_used=dd.pause_used, pause_left=dd.pause_left,
                  last_report=str(day.date()))
    mult = 0.0 if st["pause_left"] > 0 else 0.5 if st["halved"] else 1.0
    ddpct = (1 - equity / st["peak"]) * 100

    # exits for tomorrow
    for i, p in pv.iterrows() if len(pv) else []:
        df = daily(p.symbol, day)
        if not p.tstop_done and (tomorrow - p.entry_date).days >= rules.TIME_STOP_DAYS:
            lvl = p.entry + rules.TIME_STOP_R * (p.entry - p.stop)
            acts.append((p.symbol, "SELL at the open", f"time stop: close {p.close:,.2f} < {lvl:,.2f}")
                        if p.close < lvl else (p.symbol, "keep", f"time stop passed (close ≥ {lvl:,.2f})"))
            pos.loc[pos.symbol == p.symbol, "tstop_done"] = True
        w = to_weekly(df)
        bull = supertrend_bullish(w, *rules.SUPERTREND).to_numpy()
        done = w.index.to_period("W-FRI") <= day.to_period("W-FRI") if week_end else \
            w.index.to_period("W-FRI") < day.to_period("W-FRI")
        flips = [j for j in range(1, len(w)) if done[j] and bull[j - 1] and not bull[j] and w.index[j] >= p.entry_date]
        if flips:
            wk = w.index[flips[-1]]
            last_done = day.to_period("W-FRI") if week_end else day.to_period("W-FRI") - 1
            acts.append((p.symbol, "SELL at the open", f"weekly Supertrend turned bearish, week ending {wk:%d %b}"
                         + (" (OVERDUE)" if wk.to_period("W-FRI") < last_done else "")))
        pv.loc[i, "st"] = "bull" if bull[-1] else "bear"
        if month_end:
            n = rules.trim(int(p.qty), p.close, equity) if p.value > rules.POS_CAP * equity else 0
            if n:
                acts.append((p.symbol, f"SELL {n} shares", f"20% cap: worth {p.value / equity * 100:.0f}% of equity"))

    # month end: new setups
    be = be_series()
    if month_end:
        members = tradeable(data.members_on(day) | data.members_on(day + pd.offsets.MonthEnd(1)))
        stocks = data.load(sorted(members))
        lst = []
        for s, df in sorted(stocks.items()):
            df = df[:day]
            if len(df) < 300 or df.index[-1] != day:
                continue
            m = rules.setups(df)
            if m["setup"].iat[-1] and s not in set(pos.symbol):
                lst.append({"symbol": s, "setup_month": m.index[-1], "buy_stop": m["High"].iat[-1],
                            "valid_until": day + pd.offsets.MonthEnd(0) + pd.offsets.MonthEnd(1),
                            "k": m["K"].iat[-1], "d": m["D"].iat[-1]})
        od = pd.DataFrame(lst)
        journal(a.dir, day, "setups", note=", ".join(x[:-3] for x in od.symbol) if len(od) else "none")
        if day.weekday() != 4:
            warn.append("Month end is not a Friday: in Chartink set the weekly filters to '1 week ago', or use "
                        "this list (the reference).")
    elif len(od):
        od = od[(od.valid_until >= tomorrow) & ~od.symbol.isin(pos.symbol)]

    # buy-stops for tomorrow, sized on today's equity
    orders = []
    for _, o in od.iterrows() if len(od) else []:
        df = daily(o.symbol, day)
        since = df[df.index > pd.Timestamp(o.setup_month)]
        ok = buy_ok.reindex(since.index, method="ffill").fillna(False).to_numpy(dtype=bool)
        hit = since[(since.High > o.buy_stop) & ok]
        note = "BE series: trade-for-trade, check liquidity" if o.symbol in be else ""
        if len(hit):
            h = hit.index[0]
            orders.append({**o, "stop": stop_for(df, h)[0], "pct": np.nan, "qty": 0,
                           "note": f"TRIGGERED {h:%d %b} at {max(o.buy_stop, since.Open[h]):,.2f}: record with 'buy' "
                                   f"if taken, else gone this month"})
            continue
        stop, _ = stop_for(df, tomorrow)
        if stop >= o.buy_stop:
            orders.append({**o, "stop": stop, "pct": np.nan, "qty": 0, "note": "stop above buy-stop: skip"})
            continue
        q = rules.shares(equity, mult, o.buy_stop, stop, np.inf)[0]
        orders.append({**o, "stop": stop, "pct": (o.buy_stop - stop) / o.buy_stop * 100, "qty": q, "note": note})
    orders.sort(key=lambda x: x["pct"] if x["pct"] == x["pct"] else 1e9)
    save(a.dir, st, pos, od)

    # print
    print(f"\n=== S44984096 after the close of {day:%a %d %b %Y} -> for {tomorrow:%a %d %b}"
          f"{'  [WEEK END]' if week_end else ''}{'  [MONTH END]' if month_end else ''}")
    for x in warn:
        print("WARNING:", x)
    print(f"Market filter: NIFTY 500 {idx[:day].iat[-1]:,.0f} vs 200-day {sma(idx, rules.MARKET_SMA)[:day].iat[-1]:,.0f}"
          f" -> {'ON: buy-stops live' if mk_tomorrow else 'OFF: pause all buy-stops'}")
    status = "PAUSED" if mult == 0 else "HALF RISK" if mult == 0.5 else "FULL RISK"
    print(f"Equity Rs {equity:,.0f} (cash {st['cash']:,.0f}) · high {st['peak']:,.0f} · drawdown {ddpct:.1f}% · "
          f"{status} · risk/trade Rs {equity * rules.RISK * mult:,.0f} · free slots {rules.MAX_POSITIONS - len(pos)}")
    for _, p in pv.iterrows() if len(pv) else []:
        print(f"  {p.symbol:14} {int(p.qty):>6} @ {p.entry:,.2f}  stop {p.stop:,.2f}  close {p.close:,.2f}  {p.R:+.2f}R"
              f"  ST {p.get('st', '')}")
    print("Actions:" if acts else "Actions: none")
    for s, w_, why in acts:
        print(f"  {s:14} {w_}  - {why}")
    if orders:
        print(f"Buy-stops ({'live' if mk_tomorrow else 'PAUSED'}), tightest stop first:")
        for r in orders:
            print(f"  {r['symbol']:14} buy-stop {r['buy_stop']:,.2f}  stop {r['stop']:,.2f}  {r['qty']} shares  {r['note']}")
    sheet(a.dir, day, tomorrow, warn, acts, pv, orders)


def sheet(d, day, tomorrow, warn, acts, pv, orders):
    """The same to-do list as a one-page PDF in <dir>/reports/."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table
    ss = getSampleStyleSheet()
    s = [Paragraph(f"S44984096: {day:%a %d %b %Y} -> {tomorrow:%a %d %b}", ss["Title"])]
    s += [Paragraph("WARNING: " + x, ss["Normal"]) for x in warn]
    s += [Paragraph("Actions", ss["Heading2"]),
          Table([["Stock", "Do", "Why"]] + [[x[:-3], w_, Paragraph(why, ss["Normal"])] for x, w_, why in acts],
                colWidths=[70, 100, 330]) if acts else Paragraph("None. Keep GTT stops in place.", ss["Normal"])]
    s += [Paragraph("Positions", ss["Heading2"]),
          Table([["Stock", "Qty", "Entry", "Stop", "Close", "R"]] +
                [[p.symbol[:-3], int(p.qty), f"{p.entry:,.2f}", f"{p.stop:,.2f}", f"{p.close:,.2f}", f"{p.R:+.2f}"]
                 for _, p in pv.iterrows()]) if len(pv) else Paragraph("None.", ss["Normal"])]
    s += [Paragraph("Buy-stops (tightest stop first)", ss["Heading2"]),
          Table([["Stock", "Buy-stop", "Stop", "Shares", "Note"]] +
                [[r["symbol"][:-3], f"{r['buy_stop']:,.2f}", f"{r['stop']:,.2f}", r["qty"], Paragraph(r["note"], ss["Normal"])]
                 for r in orders], colWidths=[70, 60, 60, 50, 260]) if orders else Paragraph("None.", ss["Normal"])]
    out = Path(d) / "reports"; out.mkdir(parents=True, exist_ok=True)
    f = out / f"{day:%Y-%m-%d}.pdf"
    SimpleDocTemplate(str(f), pagesize=A4).build(s)
    print("PDF:", f)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=str(ROOT / "live"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    x = sub.add_parser("init"); x.add_argument("--capital", type=float, required=True); x.add_argument("--date")
    x.add_argument("--force", action="store_true")
    x = sub.add_parser("report"); x.add_argument("--date"); x.add_argument("--refresh", action="store_true")
    x = sub.add_parser("buy"); x.add_argument("symbol"); x.add_argument("price", type=float)
    x.add_argument("qty", type=int); x.add_argument("--date")
    x = sub.add_parser("sell"); x.add_argument("symbol"); x.add_argument("price", type=float)
    x.add_argument("--qty", type=int); x.add_argument("--date"); x.add_argument("--why")
    x = sub.add_parser("cash"); x.add_argument("amount", type=float)
    a = ap.parse_args()
    {"init": cmd_init, "report": cmd_report, "buy": cmd_buy, "sell": cmd_sell, "cash": cmd_cash}[a.cmd](a)


if __name__ == "__main__":
    main()
