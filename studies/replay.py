"""Month-by-month replay workbook for S44984096 (your choice), for paper-trading practice.

    python studies/replay.py 2016                 # workbook for 2016 (runs the backtest from 2016 once, cached)
    python studies/replay.py 2017 --start 2016    # later years continue the same run
    python studies/replay.py 2016 --rerun         # force a fresh run

A fresh run of the strategy starting on 1 Jan of --start with --capital (default ₹10 lakh), everything else exactly
as strategies/stexit/A_flip.json. Writes results/studies/replay/from<start>/:
    run/ (summary, equity, fills, signals log)  setups_<year>.csv  workbook_<year>.pdf
Each month has two pages: "Your turn" (portfolio going in, last month's setups and the orders they imply) and
"What happened" (fills with the sizing worked out, skips and why, exits with P&L and R).
"""
import argparse, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
import lib.pdffont  # noqa: F401  (DejaVu glyphs for ₹ and −)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, PageBreak, Spacer
import run_strategy as R
from lib import ids, membership, market, portfolio
from lib.engine import _signal_mask
from lib.indicators import resample, ema, rsi, stoch_rsi, supertrend

NAME = "stexit/A_flip_capentry"
CFG = ROOT / "strategies" / f"{NAME}.json"

ap = argparse.ArgumentParser()
ap.add_argument("year", type=int)
ap.add_argument("--start", type=int)
ap.add_argument("--capital", type=float, default=10_00_000)
ap.add_argument("--rerun", action="store_true")
a = ap.parse_args()
START = a.start or a.year
OUT = ROOT / "results" / "studies" / "replay" / f"from{START}"
RUN = OUT / "run"
OUT.mkdir(parents=True, exist_ok=True)
cfg = json.load(open(CFG))
cfg["period"]["start"] = f"{START}-01-01"
cfg["sizing"]["capital"] = a.capital
cfg["log_skips"] = True
closes, dailies = R.load_dailies(cfg["universe"])
if a.rerun or not (RUN / "signals_none.csv").exists():
    print("running backtest from", START)
    R.run(cfg, closes, dailies, RUN)

eq = pd.read_csv(RUN / "equity.csv", index_col=0, parse_dates=True).iloc[:, 0].dropna()
fills = pd.read_csv(RUN / "fills_none.csv", parse_dates=["entry_date", "exit_date"])
sig = pd.read_csv(RUN / "signals_none.csv", parse_dates=["signal_date", "entry_date", "exit_date", "day"])
risk, slots = cfg["sizing"]["risk_pct"] / 100, cfg["sizing"]["max_positions"]
ddr = cfg["sizing"]["dd_rule"]

# ---- drawdown-rule state per day (same logic as lib/portfolio.py, on the previous close) ----
state, pk, halved, used, left = {}, 0.0, False, False, 0
prev = eq.shift(1).fillna(eq.iloc[0])
for d, v in prev.items():
    pk = max(pk, v); dd = (1 - v / pk) * 100
    if v >= pk:
        halved = used = False
    if dd >= ddr["halve"]:
        halved = True
    if dd >= ddr["pause"] and not used:
        used, left = True, ddr["pause_days"]
    if left > 0:
        left -= 1; state[d] = ("Paused", 0.0, pk, dd)
    else:
        state[d] = ("Half risk", 0.5, pk, dd) if halved else ("Full risk", 1.0, pk, dd)

# ---- monthly setups (every stock in the index at the month's end whose monthly candle gave a signal) ----
mkt = market.regime(cfg["entry"]["day_filters"]["market_sma"], cfg["entry"]["day_filters"].get("market_index"))
sp = OUT / f"setups_{a.year}.csv"
if not sp.exists() or a.rerun:
    rows = []
    lo, hi = pd.Timestamp(f"{a.year - 1}-12-01"), pd.Timestamp(f"{a.year}-11-30")
    for s, d in dailies.items():
        d = d[: hi + pd.offsets.MonthEnd(0)]
        if len(d) < 300:
            continue
        b = resample(d, "M")
        m = _signal_mask(d, b, "M", cfg)
        for i in np.flatnonzero(m):
            me = b.index[i]
            if not (lo <= me <= hi):
                continue
            last = d.index[d.index <= me][-1]
            nxt = last + pd.offsets.MonthEnd(1)             # trades need membership on the fill day (next month)
            if s not in membership.members_on(last) and s not in membership.members_on(nxt):
                continue
            w = resample(d, "W"); w = w[w.index <= last]; _, K, D = stoch_rsi(b["Close"][: i + 1])
            rows.append({"month": me, "symbol": s, "buy_stop": b["High"].iat[i], "m_low": b["Low"].iat[i],
                         "close": b["Close"].iat[i], "ema_m": ema(b["Close"], 61).iat[i],
                         "close_w": w["Close"].iat[-1], "ema_w": ema(w["Close"], 61).iat[-1],
                         "ema_d": ema(d["Close"], 61)[:last].iat[-1], "rsi_m": rsi(b["Close"]).iat[i],
                         "k": K.iat[-1], "d": D.iat[-1], "k_prev": K.iat[-2], "d_prev": D.iat[-2],
                         "wk_low": w["Low"].iat[-1], "st_w": "bull" if supertrend(w).iat[-1] else "bear"})
    pd.DataFrame(rows).to_csv(sp, index=False)
setups = pd.read_csv(sp, parse_dates=["month"])

# ---- PDF ----
ss = getSampleStyleSheet(); DARK, GREY, AMBER, GREEN, RED = "#0f172a", "#64748b", "#b45309", "#15803d", "#dc2626"
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=17, leading=21, alignment=0, textColor=colors.HexColor(DARK))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12.5, textColor=colors.HexColor(AMBER), spaceBefore=6, spaceAfter=3)
H3 = ParagraphStyle("H3", parent=ss["Heading3"], fontSize=10, textColor=colors.HexColor(DARK), spaceBefore=5, spaceAfter=2)
P = ParagraphStyle("P", parent=ss["Normal"], fontSize=8.6, leading=11.5, spaceAfter=3)
SM = ParagraphStyle("SM", parent=P, fontSize=7.4, leading=9.5, textColor=colors.HexColor(GREY))
TC = ParagraphStyle("TC", parent=ss["Normal"], fontSize=7.2, leading=8.8)
bl = lambda xs: [Paragraph(x, P, bulletText="•") for x in xs]
L = lambda v: f"₹{v / 1e5:,.2f} L"
R0 = lambda v: f"₹{v:,.0f}"
nm = lambda s: s.replace(".NS", "")


def table(rows, widths, head=DARK):
    rows = [[Paragraph(str(c), TC) if isinstance(c, str) and len(c) > 28 else c for c in r] for r in rows]
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.2), ("FONT", (0, 1), (-1, -1), "Helvetica", 7.2),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(head)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5)]))
    return t


def close_on(sym, day):
    c = closes[sym][:day].dropna()
    return c.iat[-1] if len(c) else np.nan


def open_book(day):
    """Positions held going into `day` (bought before it, not fully sold before it)."""
    f = fills[(fills.entry_date < day) & (fills.exit_date.isna() | (fills.exit_date >= day))]
    out = []
    for (s, ed), g in f.groupby(["symbol", "entry_date"], sort=False):
        r0 = g.iloc[0]; q = g.qty.sum(); px = close_on(s, day - pd.Timedelta(days=1))
        sg = sig[(sig.symbol == s) & (sig.entry_date == ed)]
        r_ = (px - r0.entry) / (r0.entry - r0.stop)
        out.append({"symbol": s, "entry_date": ed, "entry": r0.entry, "stop": r0.stop, "qty": q, "px": px,
                    "value": q * px, "pnl": q * (px - r0.entry), "R": r_, "days": (day - ed).days,
                    "tstop": ed + pd.Timedelta(days=25), "exit_plan": sg.exit_date.iat[0] if len(sg) else pd.NaT})
    return pd.DataFrame(out)


eq_y = eq[str(a.year)]
story = [Paragraph(f"Replay workbook {a.year}: S44984096 (your choice)", H1),
         Paragraph(f"A fresh run started 1 Jan {START} with {L(a.capital)}; point-in-time NIFTY 500, 1% risk, 10 slots, costs "
                   f"included (Sharekhan delivery + 0.1% slippage). {a.year}: {L(eq_y.iloc[0])} → {L(eq_y.iloc[-1])} "
                   f"({(eq_y.iloc[-1] / prev[eq_y.index[0]] - 1) * 100:+.1f}%).", SM),
         Paragraph("How to use this workbook", H2)] + bl([
    "This workbook has three parts: the <b>trading guide</b> (every rule, step by step), the <b>strategy report</b> "
    "(the full backtest of S44984096 from 2000), and the <b>month-by-month replay</b> that follows.",
    "Each month has two pages. Work through <b>Your turn</b> first: check the portfolio and the drawdown status, read "
    "the setups from last month's candle, and write down which buy-stops you would place, your stop and how many "
    "shares. Then turn the page to <b>What happened</b>: fills (with the sizing worked out), skipped signals and why, "
    "and every sale with its reason, P&L and R.",
    "Setups list stocks whose just-closed monthly candle met every entry rule (guide, Step 1). The stop shown is an "
    "estimate (last week's low at month end); the real stop is the low of the last completed week before the fill.",
    "Replay numbers are a fresh run from 1 Jan of the start year, so they differ from the 2000–2026 report."])

for mth in range(1, 13):
    ms = pd.Timestamp(f"{a.year}-{mth:02d}-01"); me = ms + pd.offsets.MonthEnd(0)
    days = eq[ms:me].index
    if not len(days):
        continue
    d0 = days[0]; st = state[d0]; e_in = prev[d0]
    book = open_book(d0)
    inv = book.value.sum() if len(book) else 0.0
    story += [PageBreak(), Paragraph(f"{ms:%B %Y} · Your turn", H1),
              Paragraph(f"Going into {d0:%a %d %b}: equity {L(e_in)} · peak {L(st[2])} · drawdown {st[3]:.1f}% · "
                        f"<b>{st[0]}</b> (risk per trade {risk * st[1] * 100:g}% = {R0(e_in * risk * st[1])}) · "
                        f"{len(book)} of {slots} slots used · invested {L(inv)} · cash ≈ {L(e_in - inv)}", P),
              Paragraph("Open positions", H3)]
    if len(book):
        rows = [["Stock", "Bought", "Entry", "Stop", "Shares", "Last close", "Value", "P&L", "R now", "Days",
                 "25-day check"]]
        for _, r in book.iterrows():
            rows.append([nm(r.symbol), f"{r.entry_date:%d %b %y}", f"{r.entry:,.1f}", f"{r.stop:,.1f}", int(r.qty),
                         f"{r.px:,.1f}", R0(r.value), R0(r.pnl), f"{r.R:+.2f}", int(r.days),
                         f"{r.tstop:%d %b}" if r.days < 25 else "passed"])
        story.append(table(rows, [24 * mm, 17 * mm, 15 * mm, 15 * mm, 13 * mm, 17 * mm, 20 * mm, 18 * mm, 13 * mm, 11 * mm, 18 * mm]))
    else:
        story.append(Paragraph("None: all cash (earning the liquid-fund rate).", P))
    su = setups[setups.month == ms - pd.Timedelta(days=1)].sort_values("symbol")
    mk = bool(mkt.shift(1).reindex([d0], method="ffill").iat[0])
    story += [Paragraph(f"Setups from the {(ms - pd.Timedelta(days=1)):%B} monthly candle ({len(su)}) → buy-stop orders for {ms:%B}", H3),
              Paragraph(f"Market filter on {d0:%d %b}: NIFTY 500 index {'above' if mk else '<b>below</b>'} its 200-day "
                        f"average{'' if mk else ' → no new buys until it closes back above'}.", P)]
    if len(su):
        rows = [["Stock", "Buy-stop", "Stop est.", "Risk %", "Shares est.", "%K / %D", "prev %K / %D", "RSI m",
                 "Close / EMA61 m", "Week / EMA61 w", "Wk ST"]]
        for _, r in su.iterrows():
            rk = (r.buy_stop - r.wk_low) / r.buy_stop * 100
            sh = int(e_in * risk * st[1] // (r.buy_stop - r.wk_low)) if r.buy_stop > r.wk_low else 0
            rows.append([nm(r.symbol), f"{r.buy_stop:,.1f}", f"{r.wk_low:,.1f}", f"{rk:.1f}", sh,
                         f"{r.k:.0f} / {r.d:.0f}", f"{r.k_prev:.0f} / {r.d_prev:.0f}", f"{r.rsi_m:.0f}",
                         f"{r.close:,.0f} / {r.ema_m:,.0f}", f"{r.close_w:,.0f} / {r.ema_w:,.0f}", r.st_w])
        story.append(table(rows, [24 * mm, 17 * mm, 16 * mm, 12 * mm, 16 * mm, 16 * mm, 19 * mm, 12 * mm, 24 * mm, 24 * mm, 11 * mm]))
        story.append(Paragraph("Stop est. = last week's low at month end; the real stop is the low of the last completed week "
                               "before the fill. Shares est. = today's risk budget ÷ (buy-stop − stop est.), before the cash "
                               "check. Wk ST = weekly Supertrend now (bearish is fine: the exit needs a turn after entry).", SM))
    story.append(Paragraph("Your notes: which orders, how many shares, what you expect to happen to each open position.", SM))

    # ---- answers ----
    story += [PageBreak(), Paragraph(f"{ms:%B %Y} · What happened", H1)]
    ent = sig[(sig.day >= ms) & (sig.day <= me) & (sig.taken != "held")].sort_values(["day", "taken"])
    rows = [["Stock", "Fill day", "Entry", "Stop", "Stop %", "Status", "Sizing", "Shares", "Exit", "Reason", "R"]]
    for _, r in ent.iterrows():
        st_d = state.get(r.day, ("", 1.0, 0, 0)); ev = prev.get(r.day, np.nan)
        dist = r.entry - r.stop
        f = fills[(fills.symbol == r.symbol) & (fills.entry_date == r.day)]
        q = int(f.qty.sum()) if len(f) else 0
        calc = f"{L(ev)} × {risk * st_d[1] * 100:g}% ÷ {dist:,.1f} = {int(ev * risk * st_d[1] // dist) if dist > 0 else 0}"
        status = {"taken": "Bought", "slots": "Skipped: slots full", "cash": "Skipped: no cash", "paused": "Skipped: paused",
                  "too-small": "Skipped: < 1 share"}.get(r.taken, r.taken)
        if r.taken == "taken" and f.capped.any():
            status = "Bought, cut by cash"
        rr = (r.exit - r.entry) / dist if pd.notna(r.exit) and dist > 0 else np.nan
        rows.append([nm(r.symbol), f"{r.day:%d %b}", f"{r.entry:,.1f}", f"{r.stop:,.1f}", f"{dist / r.entry * 100:.1f}",
                     status, calc, q if q else "–",
                     f"{r.exit_date:%d %b %y}" if pd.notna(r.exit_date) else "open",
                     {"close<ema": "ST turn", "stop": "stop", "stop-gap": "stop (gap)", "time-stop": "time stop",
                      "open": "still open", "stop-entry-day": "stop same day"}.get(r.reason, r.reason),
                     f"{rr:+.2f}" if pd.notna(rr) else ""])
    story.append(Paragraph(f"Fills and skipped signals ({(ent.taken == 'taken').sum()} bought, {(ent.taken != 'taken').sum()} skipped)", H3))
    story.append(table(rows, [20 * mm, 13 * mm, 15 * mm, 15 * mm, 11 * mm, 26 * mm, 44 * mm, 12 * mm, 15 * mm, 15 * mm, 11 * mm])
                 if len(ent) else Paragraph("No buy-stop was triggered this month.", P))
    nf = su[~su.symbol.isin(ent.symbol)] if len(su) else su
    if len(nf):
        story.append(Paragraph("Not triggered (price never broke the high on a day the filters allowed): "
                               + ", ".join(nm(s) for s in nf.symbol), SM))
    ex = fills[(fills.exit_date >= ms) & (fills.exit_date <= me)]
    rows = [["Stock", "Bought", "Sold", "Shares", "Entry", "Exit", "Why", "Net P&L", "R", "Days"]]
    for _, r in ex.sort_values("exit_date").iterrows():
        sg = sig[(sig.symbol == r.symbol) & (sig.entry_date == r.entry_date)]
        why = sg.reason.iat[0] if len(sg) else ""
        trim = len(sg) and pd.notna(sg.exit_date.iat[0]) and r.exit_date < sg.exit_date.iat[0]
        why = "20% cap trim" if trim or (len(sg) and pd.isna(sg.exit_date.iat[0])) else \
            {"close<ema": "ST turned bearish", "stop": "stop hit", "stop-gap": "gapped below stop",
             "time-stop": "time stop (< +0.25R at day 25)", "stop-entry-day": "stop on entry day"}.get(why, why)
        rows.append([nm(r.symbol), f"{r.entry_date:%d %b %y}", f"{r.exit_date:%d %b}", int(r.qty), f"{r.entry:,.1f}",
                     f"{r.exit:,.1f}", why, R0(r.proceeds - r.cost), f"{(r.exit - r.entry) / (r.entry - r.stop):+.2f}",
                     (r.exit_date - r.entry_date).days])
    story.append(Paragraph(f"Sales ({len(ex)})", H3))
    story.append(table(rows, [22 * mm, 17 * mm, 14 * mm, 14 * mm, 16 * mm, 16 * mm, 42 * mm, 20 * mm, 13 * mm, 11 * mm])
                 if len(ex) else Paragraph("Nothing sold this month.", P))
    e_out = eq[:me].iloc[-1]
    story.append(Paragraph(f"<b>Month end:</b> equity {L(e_out)} ({(e_out / e_in - 1) * 100:+.1f}% for the month; "
                           f"{(e_out / a.capital - 1) * 100:+.1f}% since the start).", P))

story += [PageBreak(), Paragraph(f"{a.year} summary", H1)]
ty = portfolio.trades(fills)
cl = ty[(ty.exit_date.dt.year == a.year) & ~ty.open]
mrows = [["Month", "Start", "End", "Return", "Status at start"]]
for mth in range(1, 13):
    x = eq[f"{a.year}-{mth:02d}"]
    if len(x):
        mrows.append([f"{x.index[0]:%b}", L(prev[x.index[0]]), L(x.iloc[-1]),
                      f"{(x.iloc[-1] / prev[x.index[0]] - 1) * 100:+.1f}%", state[x.index[0]][0]])
story += [table(mrows, [20 * mm, 30 * mm, 30 * mm, 20 * mm, 30 * mm]),
          Paragraph(f"Trades closed in {a.year}: {len(cl)} ({(cl.pnl > 0).sum()} winners), net {R0(cl.pnl.sum())}.", P),
          Paragraph("Research and education only, not investment advice.", SM)]
story += ids.pdf_section([NAME], H2)
pdf = OUT / f"workbook_{a.year}.pdf"
body = OUT / f"_months_{a.year}.pdf"
SimpleDocTemplate(str(body), pagesize=landscape(A4), leftMargin=10 * mm, rightMargin=10 * mm, topMargin=9 * mm,
                  bottomMargin=9 * mm, title=f"Replay workbook {a.year}").build(story)
# guide + strategy report + replay months -> one PDF
sys.path.insert(0, str(ROOT / "reports" / "notes"))
import strategy_guide_report
from pypdf import PdfWriter, PdfReader
guide = strategy_guide_report.build()
w = PdfWriter()
body_r = PdfReader(str(body))
w.append(body_r, pages=(0, 1))                                  # title page
w.append(PdfReader(str(guide)))
w.append(PdfReader(str(ROOT / "results" / NAME / "nifty500_pit" / "report.pdf")))
w.append(body_r, pages=(1, len(body_r.pages)))
w.write(str(pdf)); body.unlink()
print("wrote", pdf)
