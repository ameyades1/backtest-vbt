"""Build reports/ema61_stochrsi_stop_comparison.pdf: Stochastic RSI pullback with a monthly-candle-low stop vs a
previous-week-low stop (data/stochrsi_r1_p8 and data/stochrsi_r1_p8_prev_week)."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "ema61_stochrsi_stop_comparison.pdf"
BLUE, GREY, DARK, PALE = "#2563eb", "#64748b", "#0f172a", "#94a3b8"
NT = "No target (close<EMA61)"
CFG = {"Monthly candle low": "stochrsi_r1_p8", "Previous-week low": "stochrsi_r1_p8_prev_week"}
COL = {"Monthly candle low": PALE, "Previous-week low": BLUE}
KEYS = {NT: "none", "Target 8%": "8", "Target 15%": "15", "Target 20%": "20", "Target 30%": "30"}
S, EQ, PNL = {}, {}, {}
for k, d in CFG.items():
    S[k] = pd.read_csv(ROOT / "data" / d / "summary.csv", index_col=0)
    EQ[k] = pd.read_csv(ROOT / "data" / d / "equity.csv", index_col=0, parse_dates=True)
    PNL[k] = {}
    for e, f in KEYS.items():
        fl = pd.read_csv(ROOT / "data" / d / f"fills_{f}.csv")
        p = fl.proceeds - fl.cost
        r = p / fl.cost * 100
        PNL[k][e] = dict(win=p[p > 0].sum(), loss=p[p <= 0].sum(), net=p.sum(),
                         aw=r[p > 0].mean(), al=r[p <= 0].mean())
A, B = list(CFG)
EXITS = list(KEYS)


def style(ax):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=GREY, length=0, labelsize=8)
    ax.grid(axis="y", color="#e2e8f0", zorder=0)


def save(fig, name):
    style(fig.axes[0]); fig.tight_layout(); p = ROOT / "reports" / name; fig.savefig(p); plt.close(fig)
    return p


charts = []
fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=200)
for k in CFG:
    c = EQ[k][NT].dropna(); ax.plot(c.index, c / 1e5, color=COL[k], lw=1.8, label=k)
ax.set_yscale("log"); ax.yaxis.set_major_formatter(lambda v, _: f"Rs {v:g}L")
ax.legend(frameon=False, fontsize=8, loc="upper left")
ax.set_title("No target: the previous-week stop ends higher", loc="left", fontsize=10.5,
             fontweight="bold", color=DARK)
ax.set_ylabel("Equity (log scale)", color=GREY, fontsize=8)
charts.append(save(fig, "_q1.png"))


def grouped(col, title, fname, fmt="{:.1f}"):
    fig, ax = plt.subplots(figsize=(7.2, 2.7), dpi=200)
    w = 0.38
    for i, k in enumerate(CFG):
        xs = [j + (i - 0.5) * w for j in range(len(EXITS))]
        v = [col(k, e) for e in EXITS]
        ax.bar(xs, v, w, color=COL[k], label=k, zorder=2)
        for x, y in zip(xs, v):
            ax.text(x, y + (0.4 if y >= 0 else -1.6), fmt.format(y), ha="center", fontsize=6.8, color=DARK)
    ax.axhline(0, color=GREY, lw=0.6)
    ax.set_xticks(range(len(EXITS)), [e.replace(" (close<EMA61)", "") for e in EXITS])
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax.set_title(title, loc="left", fontsize=10.5, fontweight="bold", color=DARK)
    return save(fig, fname)


charts.append(grouped(lambda k, e: S[k].loc[e, "CAGR %"], "CAGR by exit: targets fail with either stop", "_q2.png"))
charts.append(grouped(lambda k, e: S[k].loc[e, "Win %"], "Win rate: the tighter stop is hit far more often",
                      "_q3.png", "{:.0f}"))

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=17, leading=21, alignment=0,
                    textColor=colors.HexColor(DARK), spaceAfter=2)
SUB = ParagraphStyle("SUB", parent=ss["Normal"], fontSize=9, textColor=colors.HexColor(GREY))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12.5, textColor=colors.HexColor(DARK),
                    spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("P", parent=ss["Normal"], fontSize=9.5, leading=13.5, spaceAfter=4)
BL = ParagraphStyle("BL", parent=P, leftIndent=10, spaceAfter=2)
SM = ParagraphStyle("SM", parent=P, fontSize=8, leading=10.5, textColor=colors.HexColor(GREY))


def table(rows, widths, num_from=2):
    tb = Table(rows, colWidths=widths, repeatRows=1)
    tb.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.6), ("FONT", (0, 1), (-1, -1), "Helvetica", 7.6),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(DARK)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("ALIGN", (num_from, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return tb


na, nb = S[A].loc[NT], S[B].loc[NT]
ta, tb_ = S[A].loc["Target 20%"], S[B].loc["Target 20%"]
pa, pb = PNL[A]["Target 20%"], PNL[B]["Target 20%"]
be = -pb["al"] / (pb["aw"] - pb["al"]) * 100
rs = lambda v: f"{v:,.0f}"
story = [
    Paragraph("Stochastic RSI Pullback: Monthly Candle Low vs Previous-Week Low Stop", H1),
    Paragraph("Rs 1,00,000 capital · 1% risk per trade · max 8 open trades · NIFTY 500 constituents (499 stocks) · "
              "Jan 2000 – Nov 2026 · prepared 17 Nov 2026", SUB),
    Paragraph("Data: actual traded prices (adjusted for splits and bonuses, not for dividends; dividend income is not counted). Junk pre-listing quotes removed. Re-run on 17 Nov 2026.", SM),
    Spacer(1, 8),
    Paragraph("Answer", H2),
    Paragraph(f"The tighter stop <b>helped the no-target version and hurt or did not help the fixed targets</b>. With no target, "
              f"CAGR rose from {na['CAGR %']:.1f}% to <b>{nb['CAGR %']:.1f}%</b> and the drawdown eased from "
              f"{na['Max DD %']:.1f}% to {nb['Max DD %']:.1f}%: losers are cut at about "
              f"{-PNL[B][NT]['al']:.0f}% while multi-year winners still run.", P),
    Paragraph(f"With a 20% target, the stop moved from a median {ta['Median stop %']:.0f}% to "
              f"{tb_['Median stop %']:.0f}% below entry and average losses shrank from {pa['al']:.1f}% to "
              f"{pb['al']:.1f}%, but the win rate fell from {ta['Win %']:.0f}% to {tb_['Win %']:.0f}%. At "
              f"+{pb['aw']:.1f}% / {pb['al']:.1f}% the break-even win rate is about {be:.0f}% before costs, so net "
              f"profit fell from Rs {rs(pa['net'])} to Rs {rs(pb['net'])}.", P),
    Paragraph("Rules", H2),
    table([["Rule", "Value"],
           ["Signal", "Monthly close above EMA61 on monthly, weekly and daily; monthly RSI(14) > 50; monthly "
                      "Stochastic RSI %K crosses above %D with %D below 30"],
           ["Entry", "Next month, buy when price goes above the signal candle's high"],
           ["Stop A", "Monthly signal candle's low (fixed)"],
           ["Stop B", "Low of the last completed week before the entry day (fixed)"],
           ["Exits", "Targets 8%, 15%, 20%, 30%, or no target (exit on monthly close below EMA61)"],
           ["Sizing", "1% of starting capital (Rs 1,000) at risk per trade; max 8 open trades"],
           ["Costs", "Sharekhan delivery 0.465% per side + 0.1% slippage per side"]],
          [22 * mm, 152 * mm], num_from=9),
    KeepTogether([Paragraph("Equity, no target", H2), Image(str(charts[0]), width=172 * mm, height=76 * mm)]),
    KeepTogether([Paragraph("Return by exit", H2), Image(str(charts[1]), width=172 * mm, height=65 * mm)]),
    KeepTogether([Paragraph("Win rate by exit", H2), Image(str(charts[2]), width=172 * mm, height=65 * mm)]),
]
rows = [["Exit", "Stop", "CAGR %", "Max DD %", "Trades", "Win %", "Avg win %", "Avg loss %",
         "Median stop %", "Avg pos. Rs", "Deployed %", "Worst %"]]
for e in EXITS:
    for k in CFG:
        r, q = S[k].loc[e], PNL[k][e]
        rows.append([e.replace(" (close<EMA61)", "") if k == A else "", k,
                     f"{r['CAGR %']:.1f}", f"{r['Max DD %']:.1f}", f"{int(r['Trades taken'])}",
                     f"{r['Win %']:.1f}", f"{q['aw']:.1f}", f"{q['al']:.1f}", f"{r['Median stop %']:.1f}",
                     rs(r['Avg position (Rs)']), f"{r['Avg deployed %']:.1f}",
                     f"{r['Worst trade % of capital']:.1f}"])
story += [Paragraph("Full results", H2),
          table(rows, [17 * mm, 27 * mm, 12 * mm, 14 * mm, 11 * mm, 11 * mm, 14 * mm, 15 * mm, 16 * mm,
                       15 * mm, 15 * mm, 12 * mm]),
          Paragraph("Avg win / loss % = average net return of winning / losing trades. Worst % = worst trade as a "
                    "share of starting capital (gaps through the stop).", SM)]
prow = [["Exit", "Stop", "Gross profit Rs", "Gross loss Rs", "Net profit Rs"]]
for e in EXITS:
    for k in CFG:
        q = PNL[k][e]
        prow.append([e.replace(" (close<EMA61)", "") if k == A else "", k, rs(q["win"]), rs(q["loss"]),
                     rs(q["net"])])
story += [KeepTogether([Paragraph("Profit and loss in rupees", H2),
                        Paragraph("Total over all trades taken, after costs, ignoring idle capital.", SM),
                        table(prow, [24 * mm, 34 * mm, 34 * mm, 34 * mm, 34 * mm])])]
pts = [
    f"<b>Tighter stop, bigger positions.</b> Average position size rose from about Rs {na['Avg position (Rs)']:,.0f} to Rs {nb['Avg position (Rs)']:,.0f}, "
    f"so more capital was invested. Part of the no-target gain comes from this, not from better signals.",
    f"<b>Monthly signals need room.</b> A one-week stop is hit by normal swings inside the month; with a 20% "
    f"target the win rate fell {ta['Win %'] - tb_['Win %']:.0f} points.",
    f"<b>Gaps break the 1% limit.</b> With the tighter stop the worst trade lost "
    f"{-S[B]['Worst trade % of capital'].min():.1f}% of capital.",
    f"<b>Long losing streaks.</b> The no-target version wins only {nb['Win %']:.0f}% of trades; it relies on a "
    f"few huge winners.",
    "<b>Survivorship bias:</b> today's NIFTY 500 members only; returns are optimistic. Risk is a % of starting "
    "capital, so size does not grow with the account.",
]
story += [Paragraph("What the study shows", H2)] + [Paragraph(x, BL, bulletText="•") for x in pts]
nxt = ["<b>Drop fixed targets</b> on this monthly system; they fail with both stops.",
       "<b>Benchmark:</b> compare against NIFTY buy-and-hold over the same period.",
       "<b>Size from current equity</b> so the account compounds.",
       "<b>Market filter:</b> no new entries when NIFTY is below its 200-day average, to cut the 2008-style drawdown.",
       "<b>Middle-ground stop:</b> lowest low of the last 2–3 weeks."]
story += [Paragraph("Next tests", H2)] + [Paragraph(x, BL, bulletText="•") for x in nxt]
story += [Paragraph("How to reproduce", H2),
          Paragraph("<font face='Courier' size='8'>python examples/stochrsi_pullback_study.py --stop candle"
                    "<br/>python examples/stochrsi_pullback_study.py --stop prev_week"
                    "<br/>python reports/stochrsi_stop_report.py</font>", P),
          Paragraph("Code: lib/stochrsi_mtf.py, lib/portfolio.py. For research and education only; not investment "
                    "advice.", SM)]


def footer(c, d):
    c.setFont("Helvetica", 7.5); c.setFillColor(colors.HexColor(GREY))
    c.drawString(18 * mm, 10 * mm, "Stochastic RSI pullback – stop comparison")
    c.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {d.page}")


SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                  bottomMargin=16 * mm, title="Stochastic RSI Stop Comparison").build(
    story, onFirstPage=footer, onLaterPages=footer)
for c in charts:
    c.unlink()
print(OUT, round(be, 1))
