"""Daily paper-trading assistant for your strategy S44984096 (strategies/stexit/A_flip_capentry.json).

Run it after the close. It reads your positions and cash, applies the strategy's rules to the latest daily data and
prints (and saves as a PDF) tomorrow's to-do list: buy-stops to keep live or pause, stops to have in place, time-stop
and Supertrend exits, month-end setups and trims, and the risk per trade. No broker connection: you place the orders
yourself and record fills with `buy` / `sell`.

    python live.py init --capital 1000000            # new account (state in live/, git-ignored)
    python live.py report [--date 2026-11-20] [--refresh]
    python live.py buy  HDFCBANK 1650.5 120 [--date 2026-12-02]   # records a fill; stop = last completed week's low
    python live.py sell HDFCBANK 1702 [--qty 40] [--date ...] [--why "time stop"]
    python live.py cash 1003250                       # set cash to your broker's figure (liquid fund included)

--refresh downloads the latest Yahoo data for today's NIFTY 500, the NIFTY 500 index and your holdings first.
--dir lets you keep a separate account (e.g. a historical practice run: use --date on every command).
Rules are those of the backtest (see reports/notes/strategy_guide.pdf); differences from your broker's data can
make a signal or a Supertrend flip differ occasionally.
"""
import argparse, json, sys
from datetime import date as _date
from pathlib import Path
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from lib import data, market, membership, costs, ids
from lib.engine import _signal_mask
from lib.indicators import resample, supertrend, stoch_rsi, rsi, ema

CFG = json.load(open(ROOT / "strategies" / "stexit" / "A_flip_capentry.json"))
SID = ids.short(CFG["id"])
RISK = CFG["sizing"]["risk_pct"] / 100
SLOTS = CFG["sizing"]["max_positions"]
CAP = CFG["sizing"]["pos_cap"]
DD = CFG["sizing"]["dd_rule"]
TS = CFG["exits"]["time_stop"]
STC = CFG["exits"]["supertrend_exit_when_no_target"]
BUY_C, SELL_C = costs.side_costs(CFG["costs"]["broker"], CFG["costs"]["product"])
SLIP = CFG["costs"]["slippage_pct"] / 100
IDX = CFG["entry"]["day_filters"].get("market_index", "^NSEI")
SMA = CFG["entry"]["day_filters"]["market_sma"]
POS_COLS = ["symbol", "entry_date", "entry", "stop", "qty", "tstop_done"]


# ---------------------------------------------------------------- state
def paths(d):
    d = Path(d); d.mkdir(parents=True, exist_ok=True)
    return d / "state.json", d / "positions.csv", d / "orders.csv", d / "journal.csv"


def load_state(d):
    sp, pp, op, jp = paths(d)
    if not sp.exists():
        sys.exit(f"no account in {d}: run  python live.py init --capital 1000000")
    st = json.load(open(sp))
    pos = pd.read_csv(pp, parse_dates=["entry_date"]) if pp.exists() else pd.DataFrame(columns=POS_COLS)
    od = pd.read_csv(op, parse_dates=["setup_month", "valid_until"]) if op.exists() and op.stat().st_size > 2 \
        else pd.DataFrame()
    return st, pos, od


def save_state(d, st, pos, od=None):
    sp, pp, op, _ = paths(d)
    json.dump(st, open(sp, "w"), indent=1, default=str)
    pos.to_csv(pp, index=False)
    if od is not None:
        od.to_csv(op, index=False)


def journal(d, **row):
    jp = paths(d)[3]
    pd.DataFrame([row]).to_csv(jp, mode="a", header=not jp.exists(), index=False)


# ---------------------------------------------------------------- data
def bars(sym, upto):
    d = data.load([sym])
    df = pd.DataFrame({f: d[f][sym] for f in ["Open", "High", "Low", "Close", "Volume"]}).dropna()
    return df[:upto]


def last_completed_week_low(df, day):
    """Low of the last weekly candle that ended before `day` (the backtest's stop for a fill on `day`)."""
    w = resample(df[: day - pd.Timedelta(days=1)], "W")
    w = w[w.index < day]
    return float(w["Low"].iat[-1]), w.index[-1]


def trading_days():
    return data.load(["^NSEI"])["Close"]["^NSEI"].dropna().index


# ---------------------------------------------------------------- commands
def cmd_init(a):
    sp = paths(a.dir)[0]
    if sp.exists() and not a.force:
        sys.exit(f"{sp} exists; use --force to start over")
    st = {"capital": a.capital, "cash": a.capital, "peak": a.capital, "halved": False, "pause_used": False,
          "pause_left": 0, "last_report": None, "started": a.date or str(_date.today())}
    save_state(a.dir, st, pd.DataFrame(columns=POS_COLS), pd.DataFrame())
    journal(a.dir, date=st["started"], action="init", symbol="", price="", qty="", note=f"capital {a.capital:,.0f}")
    print(f"account created in {a.dir} with ₹{a.capital:,.0f}")


def _sym(s):
    return s if s.endswith(".NS") or s.startswith("^") else f"{s.upper()}.NS"


def cmd_buy(a):
    st, pos, od = load_state(a.dir)
    sym, day = _sym(a.symbol), pd.Timestamp(a.date or _date.today())
    stop, wk = last_completed_week_low(bars(sym, day), day)
    if stop >= a.price:
        sys.exit(f"stop {stop:.2f} (week of {wk:%d %b}) is not below the price: the backtest would not take this trade")
    cost = a.qty * a.price * (1 + BUY_C)
    st["cash"] -= cost
    pos = pd.concat([pos, pd.DataFrame([{"symbol": sym, "entry_date": day, "entry": a.price, "stop": stop,
                                         "qty": a.qty, "tstop_done": False}])], ignore_index=True)
    if len(od):
        od = od[od.symbol != sym]
    save_state(a.dir, st, pos, od)
    journal(a.dir, date=day.date(), action="buy", symbol=sym, price=a.price, qty=a.qty,
            note=f"stop {stop:.2f} (low of week ending {wk:%d %b}); 25-day check {day + pd.Timedelta(days=TS['days']):%d %b %Y}")
    print(f"bought {a.qty} {sym} at {a.price}; set a GTT stop at {stop:.2f}; time-stop check on the first trading day on or after "
          f"{day + pd.Timedelta(days=TS['days']):%a %d %b %Y}")


def cmd_sell(a):
    st, pos, od = load_state(a.dir)
    sym, day = _sym(a.symbol), pd.Timestamp(a.date or _date.today())
    i = pos.index[pos.symbol == sym]
    if not len(i):
        sys.exit(f"{sym} is not held")
    i = i[0]; q = a.qty or int(pos.at[i, "qty"])
    r = (a.price - pos.at[i, "entry"]) / (pos.at[i, "entry"] - pos.at[i, "stop"])
    pnl = q * (a.price * (1 - SELL_C) - pos.at[i, "entry"] * (1 + BUY_C))
    st["cash"] += q * a.price * (1 - SELL_C)
    if q >= pos.at[i, "qty"]:
        pos = pos.drop(i).reset_index(drop=True)
    else:
        pos.at[i, "qty"] -= q
    save_state(a.dir, st, pos)
    journal(a.dir, date=day.date(), action="sell", symbol=sym, price=a.price, qty=q,
            note=f"{a.why or ''}; {r:+.2f}R; net ₹{pnl:,.0f}")
    print(f"sold {q} {sym} at {a.price}: {r:+.2f}R, about ₹{pnl:,.0f} after costs")


def cmd_cash(a):
    st, pos, od = load_state(a.dir)
    st["cash"] = a.amount
    save_state(a.dir, st, pos)
    journal(a.dir, date=str(_date.today()), action="cash", symbol="", price="", qty="", note=f"set to {a.amount:,.0f}")
    print(f"cash set to ₹{a.amount:,.0f}")


def refresh(pos):
    syms = membership.members_on(pd.Timestamp.today()) | set(pos.symbol) | {IDX, "^NSEI", "^BSESN"}
    print(f"downloading {len(syms)} symbols from Yahoo ...")
    df = data.download(sorted(syms), start="1995-01-01")
    data.save(data.clean(df) if hasattr(data, "clean") else df)


def cmd_report(a):
    st, pos, od = load_state(a.dir)
    if a.refresh:
        refresh(pos)
    td = trading_days()
    day = pd.Timestamp(a.date) if a.date else td[-1]
    if day not in td:
        day = td[td <= day][-1]
    nxt = td[td > day]
    tomorrow = nxt[0] if len(nxt) else pd.Timestamp(np.busday_offset(day.date(), 1, roll="forward"))
    week_end = a.week_end or tomorrow.to_period("W-FRI") != day.to_period("W-FRI")
    month_end = a.month_end or tomorrow.month != day.month
    out = {"day": day, "tomorrow": tomorrow, "week_end": week_end, "month_end": month_end}

    # market filter (today's close decides tomorrow)
    reg = market.regime(SMA, IDX)
    mk = bool(reg[:day].iat[-1])
    ix = data.load([IDX])["Close"][IDX].dropna()[:day]
    out["mkt"] = (mk, ix.iat[-1], ix.rolling(SMA).mean().iat[-1])

    # positions at today's close
    rows, closes = [], {}
    for i, p in pos.iterrows():
        df = bars(p.symbol, day); c = df["Close"].iat[-1]; closes[p.symbol] = c
        rows.append({**p, "close": c, "value": p.qty * c, "R_now": (c - p.entry) / (p.entry - p.stop)})
    pv = pd.DataFrame(rows)
    invested = pv.value.sum() if len(pv) else 0.0
    equity = st["cash"] + invested

    # drawdown rule (updated once per trading day reported)
    if st.get("last_report") != str(day.date()):
        n = len(td[(td > pd.Timestamp(st["last_report"])) & (td <= day)]) if st.get("last_report") else 1
        st["pause_left"] = max(0, st["pause_left"] - n)
        if equity >= st["peak"]:
            st.update(peak=equity, halved=False, pause_used=False)
        dd = (1 - equity / st["peak"]) * 100
        if dd >= DD["halve"]:
            st["halved"] = True
        if dd >= DD["pause"] and not st["pause_used"]:
            st.update(pause_used=True, pause_left=DD["pause_days"])
        st["last_report"] = str(day.date())
    dd = (1 - equity / st["peak"]) * 100
    mult = 0.0 if st["pause_left"] > 0 else 0.5 if st["halved"] else 1.0
    status = f"PAUSED ({st['pause_left']} trading days left)" if mult == 0 else "HALF RISK" if mult == 0.5 else "FULL RISK"
    out.update(equity=equity, invested=invested, cash=st["cash"], peak=st["peak"], dd=dd, mult=mult, status=status,
               budget=equity * RISK * mult)

    # exits for tomorrow
    acts = []
    for i, p in pv.iterrows() if len(pv) else []:
        df = bars(p.symbol, day)
        if not p.tstop_done and (tomorrow - p.entry_date).days >= TS["days"]:
            lvl = p.entry + TS["min_r"] * (p.entry - p.stop)
            if p.close < lvl:
                acts.append((p.symbol, "SELL at tomorrow's open", f"time stop: close {p.close:,.2f} < entry + "
                                                                   f"{TS['min_r']}R = {lvl:,.2f} at day 25"))
            else:
                acts.append((p.symbol, "keep", f"time stop passed (close {p.close:,.2f} ≥ {lvl:,.2f}); no longer applies"))
            pos.loc[pos.symbol == p.symbol, "tstop_done"] = True
        if week_end:
            w = resample(df, "W")
            bull = supertrend(w, STC.get("period", 10), STC.get("mult", 3.0))
            if len(bull) > 1 and not bull.iat[-1] and bull.iat[-2] and df.index[-1] >= p.entry_date:
                acts.append((p.symbol, "SELL at next open", "weekly Supertrend(10, 3) turned bearish this week"))
            pv.loc[i, "st"] = "bull" if bull.iat[-1] else "bear"
        if month_end and p.value > CAP * equity:
            n = int(p.qty - CAP * equity // p.close)
            acts.append((p.symbol, f"SELL {n} shares at today's close / next open", f"20% cap: worth "
                                                                                 f"{p.value / equity * 100:.0f}% of equity"))
    out["acts"] = acts

    # month end: new setups -> orders for next month
    if month_end:
        lst = []
        members = membership.members_on(day) | membership.members_on(day + pd.offsets.MonthEnd(1))  # joining next month too
        allb = data.load(sorted(members))
        for s in sorted(members):
            if s not in allb["Close"].columns:
                continue
            df = pd.DataFrame({f: allb[f][s] for f in ["Open", "High", "Low", "Close", "Volume"]}).dropna()[:day]
            if len(df) < 300 or df.index[-1] != day:
                continue
            b = resample(df, "M")
            if not _signal_mask(df, b, "M", CFG)[-1]:
                continue
            w = resample(df, "W"); w = w[w.index <= day]
            _, K, D = stoch_rsi(b["Close"])
            lst.append({"symbol": s, "setup_month": b.index[-1], "buy_stop": b["High"].iat[-1],
                        "valid_until": day + pd.offsets.MonthEnd(0) + pd.offsets.MonthEnd(1), "k": K.iat[-1], "d": D.iat[-1],
                        "rsi_m": rsi(b["Close"]).iat[-1]})
        od = pd.DataFrame(lst)
        if len(od) and len(pos):
            od = od[~od.symbol.isin(pos.symbol)]
        journal(a.dir, date=day.date(), action="setups", symbol="", price="", qty="",
                note=", ".join(x.replace(".NS", "") for x in od.symbol) if len(od) else "none")
    elif len(od):
        od = od[(od.valid_until >= tomorrow)]
        if len(pos):
            od = od[~od.symbol.isin(pos.symbol)]

    # buy-stop orders for tomorrow with today's sizing
    orders = []
    free = SLOTS - len(pos)
    for _, o in od.iterrows() if len(od) else []:
        df = bars(o.symbol, day)
        since = df[df.index > pd.Timestamp(o.setup_month)]
        okd = reg.shift(1).reindex(since.index, method="ffill").fillna(False).astype(bool)
        hit = since[(since.High > o.buy_stop) & okd.to_numpy()]
        if len(hit):                                  # it already triggered: you either bought it or missed it
            h = hit.index[0]
            orders.append({**o, "stop": last_completed_week_low(df, h)[0], "pct": np.nan, "qty": 0, "cost": 0,
                           "note": f"TRIGGERED on {h:%d %b} at {max(o.buy_stop, since.Open[h]):,.2f}: record it with "
                                   f"'buy' if you took it, otherwise it is gone (no re-entry this month)"})
            continue
        stop, wk = last_completed_week_low(df, tomorrow)
        dist = o.buy_stop - stop
        if dist <= 0:
            orders.append({**o, "stop": stop, "pct": np.nan, "qty": 0, "cost": 0, "note": "stop above buy-stop: skip"})
            continue
        q_risk = int(out["budget"] // dist)
        q_cap = int(CAP * equity // (o.buy_stop * (1 + SLIP) * (1 + BUY_C)))
        q = min(q_risk, q_cap)
        orders.append({**o, "stop": stop, "pct": dist / o.buy_stop * 100, "qty": q, "cost": q * o.buy_stop,
                       "note": ("capped at 20%" if q_cap < q_risk else "") + ("" if df["Close"].iat[-1] < o.buy_stop
                                                                            else "; already above: may gap-fill at open")})
    out["orders"] = sorted(orders, key=lambda x: x["pct"] if x["pct"] == x["pct"] else 1e9)
    out["free"] = free
    out["pv"] = pv
    save_state(a.dir, st, pos, od)
    text(out); pdf(out, a.dir)


def text(o):
    print(f"\n=== {SID} after the close of {o['day']:%a %d %b %Y} → for {o['tomorrow']:%a %d %b}"
          f"{'  [WEEK END]' if o['week_end'] else ''}{'  [MONTH END]' if o['month_end'] else ''}")
    mk, ix, sm = o["mkt"]
    print(f"Market filter: NIFTY 500 {ix:,.0f} vs 200-day {sm:,.0f} → {'ON: buy-stops live' if mk else 'OFF: pause all buy-stops'}")
    print(f"Equity ₹{o['equity']:,.0f} (cash ₹{o['cash']:,.0f}) · peak ₹{o['peak']:,.0f} · drawdown {o['dd']:.1f}% · "
          f"{o['status']} · risk per trade ₹{o['budget']:,.0f} · free slots {o['free']}")
    for _, p in o["pv"].iterrows() if len(o["pv"]) else []:
        print(f"  {p.symbol:14} {int(p.qty):>6} @ {p.entry:,.2f}  stop {p.stop:,.2f}  close {p.close:,.2f}  {p.R_now:+.2f}R")
    print("Actions:" if o["acts"] else "Actions: none")
    for s, w, why in o["acts"]:
        print(f"  {s:14} {w}  — {why}")
    if o["orders"]:
        print(f"Buy-stops ({'live' if mk else 'PAUSED'}), tightest stop first:")
        for r in o["orders"]:
            print(f"  {r['symbol']:14} buy-stop {r['buy_stop']:,.2f}  stop {r['stop']:,.2f}  {r['qty']} shares  {r['note']}")


def pdf(o, d):
    import lib.pdffont  # noqa: F401
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle
    ss = getSampleStyleSheet(); AMBER, DARK, GREY = "#b45309", "#0f172a", "#64748b"
    H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=16, alignment=0, textColor=colors.HexColor(DARK))
    H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12, textColor=colors.HexColor(AMBER), spaceBefore=8, spaceAfter=3)
    P = ParagraphStyle("P", parent=ss["Normal"], fontSize=9, leading=12.5)
    SM = ParagraphStyle("SM", parent=P, fontSize=7.5, textColor=colors.HexColor(GREY))

    def tb(rows, w):
        t = Table(rows, colWidths=[x * mm for x in w], repeatRows=1)
        t.setStyle(TableStyle([("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8), ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(AMBER)),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fef3c7")]),
            ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
        return t
    mk, ix, sm = o["mkt"]
    s = [Paragraph(f"{SID} daily sheet: {o['day']:%a %d %b %Y} → {o['tomorrow']:%a %d %b}", H1),
         Paragraph(("Week end. " if o["week_end"] else "") + ("Month end. " if o["month_end"] else "") +
                   "Generated by live.py after the close. Research and practice only, not investment advice.", SM),
         Paragraph("Account and market", H2),
         Paragraph(f"Equity <b>₹{o['equity']:,.0f}</b> (cash ₹{o['cash']:,.0f}, invested ₹{o['invested']:,.0f}) · equity high "
                   f"₹{o['peak']:,.0f} · drawdown {o['dd']:.1f}% · <b>{o['status']}</b> · risk per new trade "
                   f"<b>₹{o['budget']:,.0f}</b> · free slots {o['free']} of {SLOTS}", P),
         Paragraph(f"Market filter: NIFTY 500 index {ix:,.0f} vs its 200-day average {sm:,.0f} → "
                   f"<b>{'ON: keep buy-stops live tomorrow' if mk else 'OFF: pause every buy-stop tomorrow'}</b>", P),
         Paragraph("Actions for tomorrow", H2)]
    s.append(tb([["Stock", "Do", "Why"]] + [[x.replace(".NS", ""), w, Paragraph(why, P)] for x, w, why in o["acts"]],
                [28, 50, 100]) if o["acts"] else Paragraph("None. Keep GTT stops in place.", P))
    s.append(Paragraph("Open positions (keep a GTT stop at each stop)", H2))
    if len(o["pv"]):
        rows = [["Stock", "Bought", "Shares", "Entry", "Stop", "Close", "R now", "Value", "25-day check", "Wk ST"]]
        for _, p in o["pv"].iterrows():
            rows.append([p.symbol.replace(".NS", ""), f"{p.entry_date:%d %b %y}", int(p.qty), f"{p.entry:,.2f}", f"{p.stop:,.2f}",
                         f"{p.close:,.2f}", f"{p.R_now:+.2f}", f"₹{p.value:,.0f}",
                         "done" if p.tstop_done else f"{p.entry_date + pd.Timedelta(days=TS['days']):%d %b}",
                         p.get("st", "") if isinstance(p.get("st", ""), str) else ""])
        s.append(tb(rows, [24, 17, 13, 17, 17, 17, 13, 22, 20, 12]))
    else:
        s.append(Paragraph("None.", P))
    s.append(Paragraph(f"Buy-stop orders ({'live' if mk else 'PAUSED'} tomorrow), tightest stop first", H2))
    if o["orders"]:
        rows = [["Stock", "Buy-stop", "Stop", "Stop %", "Shares", "Cost", "Valid until", "Note"]]
        for r in o["orders"]:
            rows.append([r["symbol"].replace(".NS", ""), f"{r['buy_stop']:,.2f}", f"{r['stop']:,.2f}",
                         f"{r['pct']:.1f}" if r["pct"] == r["pct"] else "–", r["qty"], f"₹{r['cost']:,.0f}",
                         f"{pd.Timestamp(r['valid_until']):%d %b}", Paragraph(r["note"].strip("; "), SM)])
        s.append(tb(rows, [26, 20, 20, 14, 15, 22, 18, 43]))
        s.append(Paragraph(f"Only {o['free']} slot(s) free: if more trigger the same day, take the tightest stops first. "
                           "Shares = risk budget ÷ (buy-stop − stop), at most 20% of equity, and within your cash. Stop = low "
                           "of the last completed week before tomorrow.", SM))
    else:
        s.append(Paragraph("None pending.", P))
    out = Path(d) / "reports"; out.mkdir(parents=True, exist_ok=True)
    f = out / f"{o['day']:%Y-%m-%d}.pdf"
    SimpleDocTemplate(str(f), pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm,
                      bottomMargin=12 * mm, title=f"{SID} daily sheet").build(s)
    print("PDF:", f)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=str(ROOT / "live"))
    sub = ap.add_subparsers(dest="cmd", required=True)
    x = sub.add_parser("init"); x.add_argument("--capital", type=float, required=True); x.add_argument("--date")
    x.add_argument("--force", action="store_true")
    x = sub.add_parser("report"); x.add_argument("--date"); x.add_argument("--refresh", action="store_true")
    x.add_argument("--week-end", action="store_true"); x.add_argument("--month-end", action="store_true")
    x = sub.add_parser("buy"); x.add_argument("symbol"); x.add_argument("price", type=float); x.add_argument("qty", type=int)
    x.add_argument("--date")
    x = sub.add_parser("sell"); x.add_argument("symbol"); x.add_argument("price", type=float); x.add_argument("--qty", type=int)
    x.add_argument("--date"); x.add_argument("--why")
    x = sub.add_parser("cash"); x.add_argument("amount", type=float)
    a = ap.parse_args()
    {"init": cmd_init, "report": cmd_report, "buy": cmd_buy, "sell": cmd_sell, "cash": cmd_cash}[a.cmd](a)


if __name__ == "__main__":
    main()
