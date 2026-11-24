"""S44984096 strategy guide (PDF), built from this release only: the rules come from rules.py and every number from
the release backtest, so the guide cannot disagree with the code you trade.

    python release/s44984096/guide.py            # uses out/trades.csv and out/equity.csv (runs the backtest if missing)
    python release/s44984096/guide.py --rerun    # run the backtest first

Writes release/s44984096/S44984096_guide.pdf.
"""
import argparse, os, sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.fonts import addMapping
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Table, TableStyle, PageBreak, Spacer, Image,
                                KeepTogether, ListFlowable, ListItem)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rules, backtest, data  # noqa: E402

PDF = HERE / "S44984096_guide.pdf"
CAPITAL = 100_000.0

# DejaVu for the Helvetica names so ₹, −, ≥ print (the built-in PDF Helvetica has no such glyphs)
_F = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
for _n, _f in [("Helvetica", "DejaVuSans.ttf"), ("Helvetica-Bold", "DejaVuSans-Bold.ttf"),
               ("Helvetica-Oblique", "DejaVuSans-Oblique.ttf"), ("Helvetica-BoldOblique", "DejaVuSans-BoldOblique.ttf")]:
    pdfmetrics.registerFont(TTFont(_n, os.path.join(_F, _f)))
addMapping("Helvetica", 0, 0, "Helvetica"); addMapping("Helvetica", 1, 0, "Helvetica-Bold")
addMapping("Helvetica", 0, 1, "Helvetica-Oblique"); addMapping("Helvetica", 1, 1, "Helvetica-BoldOblique")

INK, GREY, BAND = colors.HexColor("#1F3864"), colors.HexColor("#666666"), colors.HexColor("#EEF2F8")
_ss = getSampleStyleSheet()
H1 = ParagraphStyle("h1", _ss["Title"], fontSize=20, textColor=INK, alignment=0, spaceAfter=4)
SUB = ParagraphStyle("sub", _ss["Normal"], fontSize=9.5, textColor=GREY, leading=13, spaceAfter=8)
H2 = ParagraphStyle("h2", _ss["Heading2"], textColor=INK, spaceBefore=10, spaceAfter=4)
H3 = ParagraphStyle("h3", _ss["Heading3"], textColor=INK, spaceBefore=6, spaceAfter=2)
P = ParagraphStyle("p", _ss["Normal"], fontSize=9.5, leading=13.5, spaceAfter=4)
SM = ParagraphStyle("sm", P, fontSize=8, textColor=GREY, leading=10.5)
CELL = ParagraphStyle("cell", P, fontSize=8.5, leading=11, spaceAfter=0)


def para(t):
    return Paragraph(t, P)


def bullets(items, numbered=False):
    return ListFlowable([ListItem(Paragraph(t, P), leftIndent=12) for t in items],
                        bulletType="1" if numbered else "bullet", start="1" if numbered else None,
                        leftIndent=14, bulletFontSize=8.5)


def table(rows, widths, head=True):
    HC = ParagraphStyle("hc", CELL, textColor=colors.white, fontName="Helvetica-Bold")
    rows = [[Paragraph(str(c), HC if head and i == 0 else CELL) if isinstance(c, str) else c for c in r]
            for i, r in enumerate(rows)]
    t = Table(rows, colWidths=widths, repeatRows=1 if head else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#BFBFBF")), ("VALIGN", (0, 0), (-1, -1), "TOP")]
    if head:
        st += [("BACKGROUND", (0, 0), (-1, 0), INK)]
    t.setStyle(TableStyle(st))
    return t


def box(text):
    t = Table([[Paragraph(text, P)]], colWidths=[174 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), BAND), ("BOX", (0, 0), (-1, -1), 0.5, INK),
                           ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    return t


# ---- numbers from the release backtest -------------------------------------------------------------------------
def load(rerun):
    if rerun or not (backtest.OUT / "trades.csv").exists():
        trades, closes = backtest.all_trades()
        curve, fills, _ = backtest.run(trades, closes, CAPITAL)
        backtest.OUT.mkdir(exist_ok=True)
        fills.to_csv(backtest.OUT / "trades.csv", index=False); curve.to_csv(backtest.OUT / "equity.csv")
    f = pd.read_csv(backtest.OUT / "trades.csv", parse_dates=["entry_date", "exit_date"])
    e = pd.read_csv(backtest.OUT / "equity.csv", index_col=0, parse_dates=True)
    return f, e


def stats(f, e):
    f = f.copy()
    f["pnl"] = f.proceeds - f.cost
    g = f.groupby(["symbol", "entry_date"])
    t = pd.DataFrame({"entry": g.entry.first(), "stop": g.stop.first(), "qty": g.qty.sum(), "cost": g.cost.sum(),
                      "pnl": g.pnl.sum(), "exit_date": g.exit_date.max(), "open": g.exit_date.apply(lambda x: x.isna().any()),
                      "mult": g.risk_mult.first() if "risk_mult" in f else np.nan,
                      "reason": g.reason.apply(lambda x: [r for r in x if r != "trim 20%"][-1] if any(r != "trim 20%" for r in x) else "trim 20%")}
                     ).reset_index()
    t["R"] = t.pnl / ((t.entry - t.stop) * t.qty)
    t["ret"] = t.pnl / t.cost * 100
    c = t[~t.open].sort_values("exit_date")
    c["days"] = (c.exit_date - c.entry_date).dt.days
    win = c.pnl > 0
    streak = run = 0
    for w in win:
        run = 0 if w else run + 1; streak = max(streak, run)
    eq = e["equity"]
    years = (eq.index[-1] - eq.index[0]).days / 365.25
    dd = eq / eq.cummax() - 1
    hi = (eq >= eq.cummax()).cumsum()
    uw = eq.groupby(hi).apply(lambda s: (s.index[-1] - s.index[0]).days).max() / 365.25
    ye = eq.resample("YE").last()
    yr = ye.pct_change() * 100
    yr.iloc[0] = (ye.iloc[0] / CAPITAL - 1) * 100
    R = c.R.dropna()
    sqn = R.mean() / R.std() * np.sqrt(min(len(R), 100))
    # NIFTY 50 price index (Yahoo ^NSEI, from 17 Sep 2007; no dividends), compared over the dates both exist
    nf = data.load(["^NSEI"])["^NSEI"]["Close"].dropna()
    nf = nf[nf.index <= eq.index[-1]]
    n0 = nf.index[0]
    yrs_n = (nf.index[-1] - n0).days / 365.25
    se = eq[eq.index >= n0]
    nye = nf.resample("YE").last()
    nyr = nye.pct_change() * 100
    nyr = nyr[nyr.index.year > n0.year]                          # first, part year left out
    bench = dict(n0=n0, n_cagr=((nf.iloc[-1] / nf.iloc[0]) ** (1 / yrs_n) - 1) * 100,
                 n_mdd=(nf / nf.cummax() - 1).min() * 100,
                 s_cagr=((se.iloc[-1] / se.iloc[0]) ** (1 / yrs_n) - 1) * 100,
                 s_mdd=(se / se.cummax() - 1).min() * 100, nyr=nyr,
                 beat=int((yr.reindex(nyr.index) > nyr).sum()), nyears=len(nyr))
    return dict(**bench, t=t, c=c, eq=eq, dd=dd, yr=yr, years=years, start=eq.index[0], end=eq.index[-1],
                cagr=((eq.iloc[-1] / CAPITAL) ** (1 / years) - 1) * 100, mdd=dd.min() * 100,
                mdd_at=dd.idxmin(), peak_at=eq[:dd.idxmin()].idxmax(), uw=uw,
                n=len(t), nopen=int(t.open.sum()), win=win.mean() * 100, streak=streak,
                avg_win=c.ret[win].mean(), avg_loss=c.ret[~win].mean(), exp_r=R.mean(), sqn=sqn,
                exp_x10=R.drop(R.nlargest(10).index).mean(), top10=c.pnl.nlargest(10).sum(), net=c.pnl.sum(),
                half=int((t.mult == 0.5).sum()), days_win=c.days[win].median(), days_loss=c.days[~win].median(),
                per_year=len(t) / years, exits=c.reason.value_counts(), best=c.loc[c.R.idxmax()],
                final=eq.iloc[-1])


def chart(k, path):
    fig, (a, b) = plt.subplots(2, 1, figsize=(7.2, 4.2), sharex=True, gridspec_kw={"height_ratios": [2.2, 1]})
    a.plot(k["eq"].index, k["eq"] / CAPITAL, color="#1F3864", lw=1.2)
    a.set_yscale("log"); a.set_ylabel("Growth of ₹1 (log)"); a.grid(alpha=0.3)
    a.set_title(f"S44984096 {k['start']:%b %Y} – {k['end']:%b %Y}: {k['cagr']:.1f}% a year", fontsize=10, loc="left")
    b.fill_between(k["dd"].index, k["dd"] * 100, 0, color="#C0504D", alpha=0.6, lw=0)
    for y in (-rules.DD_HALVE, -rules.DD_PAUSE):
        b.axhline(y, color="#7F7F7F", lw=0.7, ls="--")
    b.set_ylabel("Drawdown %"); b.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(path, dpi=160); plt.close(fig)


# ---- the document ----------------------------------------------------------------------------------------------
def build(k, path=PDF):
    R = rules
    risk, half = R.RISK * 100, R.RISK * 50
    rt = (R.FEE + R.SLIPPAGE) * 200
    img = HERE / "out" / "guide_equity.png"; img.parent.mkdir(exist_ok=True); chart(k, img)
    s = [Paragraph("S44984096 strategy guide", H1),
         Paragraph(f"The strategy you trade, as coded in <b>release/s44984096/rules.py</b>. Numbers from the release "
                   f"backtest: point-in-time NIFTY 500, NSE prices, {k['start']:%b %Y} to {k['end']:%b %Y}, all costs "
                   f"included. Built {pd.Timestamp.today():%d %b %Y}. Research and education only, not investment advice.", SUB),
         box(f"<b>In one paragraph.</b> Buy NIFTY 500 stocks in a long-term uptrend when their monthly momentum turns up "
             f"after a pullback, but only while the NIFTY 500 index is above its {R.MARKET_SMA}-day average. Risk "
             f"{risk:g}% of equity per trade with the stop at the previous week's low. Sell trades that go nowhere in "
             f"{R.TIME_STOP_DAYS} days; otherwise hold until the weekly Supertrend turns bearish, which can take years. "
             f"At most {R.MAX_POSITIONS} stocks, none above {R.POS_CAP:.0%} of equity; half risk {R.DD_HALVE}% below the "
             f"equity high. About 1 trade in {100 / k['win']:.0f} wins; a few multi-year winners pay for everything."),
         Spacer(1, 6), Paragraph("Backtest at a glance", H2),
         table([["CAGR", "Max drawdown", "Trades", "Win % (closed)", "Expectancy", "Longest without a new high"],
                [f"{k['cagr']:.1f}%", f"{k['mdd']:.1f}%", f"{k['n']} ({k['per_year']:.0f}/yr)", f"{k['win']:.1f}%",
                 f"+{k['exp_r']:.2f}R", f"{k['uw']:.1f} years"]], [29 * mm] * 6),
         Spacer(1, 4),
         para(f"<b>Against the NIFTY 50</b> (price index, dividends not included; Yahoo data from {k['n0']:%d %b %Y}): "
              f"over the same dates, {k['n0']:%b %Y} to {k['end']:%b %Y}, the NIFTY 50 returned "
              f"<b>{k['n_cagr']:.1f}% a year</b> with a {k['n_mdd']:.1f}% max drawdown; S44984096 returned "
              f"<b>{k['s_cagr']:.1f}% a year</b> with {k['s_mdd']:.1f}%. It beat the index in {k['beat']} of "
              f"{k['nyears']} full calendar years."),
         Image(str(img), width=174 * mm, height=101 * mm),
         Paragraph(f"Dashed lines: {R.DD_HALVE}% (half risk) and {R.DD_PAUSE}% (21-day pause). Worst fall "
                   f"{k['mdd']:.1f}% from {k['peak_at']:%b %Y} to {k['mdd_at']:%b %Y}. {k['half']} of {k['n']} trades "
                   f"({k['half'] / k['n']:.0%}) were entered at half risk: plan on {half:g}% as the normal risk.", SM)]

    s += [PageBreak(), Paragraph("Step 1: find setups (last trading day of the month)", H2),
          para("After the close, check each NIFTY 500 member. It is a setup only if <b>all</b> of these hold:"),
          bullets([f"<b>Monthly Stochastic RSI {R.STOCH}</b>: %K crosses above %D this month (%K at or below %D last "
                   f"month, above it now), <b>and %D is below {R.OVERSOLD}</b>.",
                   f"<b>Monthly close above the monthly EMA {R.TREND_EMA}.</b>",
                   f"<b>Last completed weekly close above the weekly EMA {R.TREND_EMA}</b>. If the month ends mid-week, "
                   f"use the previous Friday's week (also on a Thursday month end before a Friday holiday).",
                   f"<b>Daily close above the daily EMA {R.TREND_EMA}</b> on the month's last day.",
                   f"<b>Monthly RSI(14) at or above {R.RSI_MIN}.</b>"], numbered=True),
          para("Note each setup's monthly <b>high</b> (the buy-stop). The Supertrend plays no part in entry."),
          Paragraph("Step 2: buy-stops (the next calendar month)", H2),
          bullets(["A <b>buy-stop at the setup month's high</b>, valid for the whole next month; it lapses at month end.",
                   f"<b>Market filter</b>: a buy may fill only on a day after the NIFTY 500 index closed above its "
                   f"{R.MARKET_SMA}-day average. If it closed below, pause every buy-stop for the next day.",
                   "The stock must be a NIFTY 500 member on the fill day; skip it if you already hold it.",
                   "Fill at the buy-stop, or at the open if the stock gaps above it.",
                   f"If several fill the same day, take the <b>tightest stop in percent</b> first. At {R.MAX_POSITIONS} "
                   "positions a triggered buy-stop is skipped for the month."], numbered=True),
          Paragraph("Step 3: stop and size (fill day)", H2),
          bullets(["<b>Stop = low of the last completed week</b> before the fill day. Fixed for the life of the trade.",
                   "<b>Arm it from the next session</b>: place the GTT after the fill-day close. On the fill day only the "
                   "close counts: if it closes at or below the stop, sell at the close or next open.",
                   f"<b>Risk</b> = {risk:g}% of yesterday's equity × the drawdown multiplier (1, ½ or 0, Step 6).",
                   "<b>Shares</b> = risk ÷ (entry − stop), rounded down; fewer if cash runs short.",
                   f"<b>Cap</b>: no new position above {R.POS_CAP:.0%} of yesterday's equity."], numbered=True),
          KeepTogether([Paragraph("Worked example", H3),
                        para(f"Equity ₹10,00,000, full risk: risk ₹{1e6 * R.RISK:,.0f}. Buy-stop ₹500, stop ₹460: "
                             f"₹40 a share, so <b>{rules.shares(1e6, 1, 500, 460, 1e9)[0]} shares</b>. With a ₹480 stop "
                             f"the risk would buy 500 shares (₹2.5 lakh), above the cap, so "
                             f"<b>{rules.shares(1e6, 1, 500, 480, 1e9)[0]} shares</b>. Costs are included in these counts.")]),
          Paragraph("Step 4: time stop", H2),
          para(f"On the first trading day on or after <b>{R.TIME_STOP_DAYS} calendar days</b> from entry, look at the "
               f"previous close. Below <b>entry + {R.TIME_STOP_R:g} × (entry − stop)</b>: sell at the open. At or above: "
               f"the time stop is passed for good. Example: entry ₹500, stop ₹460: level ₹{500 + R.TIME_STOP_R * 40:g}."),
          Paragraph("Step 5: trend exit (weekly)", H2),
          para(f"After each Friday's close, check the <b>weekly Supertrend{R.SUPERTREND}</b>. Sell at the next open only "
               "when it <b>turns</b> from bullish to bearish after your entry. No target and no holding limit: winners "
               "can run for years."),
          Paragraph("Order of exits each day", H3),
          bullets(["Time stop due and failed: sell at the open.", "Opens at or below the stop: sell at the open.",
                   "Supertrend turned bearish last week: sell at the open.", "Trades down to the stop: sold at the stop."],
                  numbered=True)]

    s += [PageBreak(), Paragraph("Step 6: drawdown rule", H2),
          bullets([f"<b>Below {R.DD_HALVE}% under the equity high</b>: full risk, {risk:g}% per trade.",
                   f"<b>{R.DD_HALVE}% or more</b>: half risk, {half:g}%, until equity closes at a <b>new high</b>. "
                   "(Restoring earlier, within 3, 5 or 7% of the high, was tested and rejected: max drawdown −28%.)",
                   f"<b>{R.DD_PAUSE}% or more</b>: no new trades for {R.PAUSE_DAYS} trading days, once per drawdown; "
                   "then half risk.",
                   "Open positions are never resized by this rule."]),
          Paragraph("Step 7: money management", H2),
          bullets([f"At each month's last close, trim any position above <b>{R.POS_CAP:.0%} of equity</b> back to "
                   f"{R.POS_CAP:.0%}.",
                   f"Idle cash in a liquid fund ({R.LIQUID_RATE:g}% a year assumed). No leverage, margin, shorts or F&amp;O.",
                   f"Costs in the backtest: Sharekhan delivery {R.FEE * 100:.2f}% per side plus "
                   f"{R.SLIPPAGE * 100:g}% slippage, about {rt:.1f}% a round trip. Tax is not included."]),
          Paragraph("Your routine", H2),
          table([["When", "What you do", "Time"],
                 ["After the close, daily", "<font face='Courier'>python release/s44984096/live.py report --refresh</font>"
                  ": market filter, actions for tomorrow, buy-stops. Record fills with <i>buy</i> / <i>sell</i>. "
                  "Daily Log row in the journal.", "10 min"],
                 ["Friday", "Supertrend exits (live.py lists them).", "5 min"],
                 ["Month end", "New setups and buy-stops, trims, Monthly Review in the journal. On a month end that "
                  "is not a Friday, Chartink's weekly filters must read <b>1 week ago</b>, or use live.py's list.", "1 hour"]],
                [32 * mm, 124 * mm, 18 * mm]),
          Paragraph("Corporate actions", H3),
          bullets(["Brokers cancel GTT orders on a split or bonus ex-date. Re-place the stop at old stop ÷ ratio for old "
                   "quantity × ratio (live.py adjusts and tells you).",
                   "Demerger or an unexplained gap of more than 30%: decide by hand (live.py flags it)."]),
          Paragraph("Journal and checks", H3),
          bullets(["Log every trade and every skipped signal (with the reason) in the Trading Journal workbook, strategy "
                   "S44984096.",
                   "<font face='Courier'>tests/run_tests.py</font> keeps the backtest frozen; "
                   "<font face='Courier'>tests/chartink_parity.py</font> checks the Chartink screener against these rules."])]

    yr = k["yr"]
    ex = k["exits"]
    names = {"stop": "Stop", "time-stop": "Time stop", "supertrend": "Supertrend", "stop-entry-day": "Stop (fill-day close)", "stop-gap": "Stop (gap below)"}
    s += [PageBreak(), Paragraph("What to expect", H2),
          bullets([f"About <b>{k['win']:.0f}% of closed trades win</b>. Average win +{k['avg_win']:.0f}%, average loss "
                   f"{k['avg_loss']:.1f}%. Up to <b>{k['streak']} losses in a row</b>.",
                   f"Median holding: winners {k['days_win']:.0f} days, losers {k['days_loss']:.0f} days.",
                   f"The 10 best trades made ₹{k['top10'] / 1e5:.1f} lakh of the ₹{k['net'] / 1e5:.1f} lakh net profit "
                   f"(on ₹{CAPITAL / 1e5:g} lakh). Best: {k['best'].symbol[:-3]} +{k['best'].R:.0f}R. Never cut a big "
                   "winner early, and take every signal.",
                   f"Expectancy +{k['exp_r']:.2f}R per trade (+{k['exp_x10']:.2f}R without the 10 best); SQN "
                   f"{k['sqn']:.1f}: tradable but lumpy.",
                   f"Drawdowns of −20% or more happen (worst {k['mdd']:.1f}%), and {k['uw']:.1f} years passed once "
                   f"without a new equity high. Calendar years ranged {yr.min():.0f}% to +{yr.max():.0f}%.",
                   "It earns in bull and quiet markets; choppy sideways years bleed; in bear markets the index filter "
                   "keeps you mostly in cash."]),
          Paragraph("Exits in the backtest", H3),
          table([["Exit", "Trades"]] + [[names.get(r, r), f"{n}"] for r, n in ex.items()], [60 * mm, 25 * mm]),
          Paragraph("Year by year", H3)]
    nyr = k["nyr"]
    cells = [[f"{d.year}", f"{v:+.1f}%", f"{nyr[d]:+.1f}%" if d in nyr.index else "–"] for d, v in yr.items()]
    half_n = (len(cells) + 1) // 2
    rows = [["Year", "S44984096", "NIFTY 50"] * 2] + [cells[i] + (cells[i + half_n] if i + half_n < len(cells)
                                                                  else ["", "", ""]) for i in range(half_n)]
    s += [table(rows, [15 * mm, 26 * mm, 21 * mm] * 2),
          Paragraph(f"{k['start'].year} is a part year from {k['start']:%b}; {k['end'].year} runs to {k['end']:%d %b}. "
                    f"NIFTY 50: price index without dividends (about 1-1.5% a year less than total return); Yahoo has it "
                    f"from {k['n0']:%d %b %Y}, so {k['start'].year}-{k['n0'].year} show –. "
                    f"{k['nopen']} trades still open at the end are valued at the last close.", SM),
          Paragraph("Known limits", H3),
          bullets(["Survivorship: not every past NIFTY 500 member has prices (about 68% in 2006, 99% by 2025), so "
                   "early years are somewhat optimistic.",
                   "Fills assume the buy-stop or the open; circuits and illiquid gaps can be worse.",
                   "Yahoo data can differ from your broker's by a tick: a borderline signal can differ."]),
          Paragraph("How a rule changes", H3),
          para("Test it in research/ first. If adopted: change rules.py, rerun the tests (the golden test fails), check "
               "every changed trade, refreeze the golden trades in the same commit, then rebuild this guide."),
          Paragraph("Research and education only, not investment advice.", SM)]

    def foot(c, d):
        c.saveState(); c.setFont("Helvetica", 7.5); c.setFillColor(GREY)
        c.drawString(18 * mm, 10 * mm, "S44984096 strategy guide · release/s44984096")
        c.drawRightString(192 * mm, 10 * mm, f"page {d.page}"); c.restoreState()

    SimpleDocTemplate(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                      bottomMargin=16 * mm, title="S44984096 strategy guide").build(s, onFirstPage=foot, onLaterPages=foot)
    return path


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rerun", action="store_true")
    a = ap.parse_args()
    print("wrote", build(stats(*load(a.rerun))))
