"""Build reports/ema61_stochrsi_pullback.pdf from data/stochrsi_r1_p8 (examples/stochrsi_pullback_study.py),
compared with the EMA61 breakout at the same sizing (data/sizing_r1_p8)."""
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
OUT = ROOT / "reports" / "ema61_stochrsi_pullback.pdf"
BLUE, GREY, DARK = "#2563eb", "#64748b", "#0f172a"
NT = "No target (close<EMA61)"
S = pd.read_csv(ROOT / "data" / "stochrsi_r1_p8" / "summary.csv", index_col=0)
EQ = pd.read_csv(ROOT / "data" / "stochrsi_r1_p8" / "equity.csv", index_col=0, parse_dates=True)
SB = pd.read_csv(ROOT / "data" / "sizing_r1_p8" / "summary.csv", index_col=0)
EB = pd.read_csv(ROOT / "data" / "sizing_r1_p8" / "equity.csv", index_col=0, parse_dates=True)
curves = {"Stochastic RSI pullback": (EQ[NT].dropna(), BLUE), "EMA61 breakout": (EB[NT].dropna(), "#94a3b8")}
eq = EQ[NT].dropna()
dd = eq / eq.cummax() - 1
trough = dd.idxmin(); peak = eq[:trough].idxmax()


def style(ax):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=GREY, length=0, labelsize=8)
    ax.grid(axis="y", color="#e2e8f0", zorder=0)


charts = []
fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=200)
for k, (c, col) in curves.items():
    ax.plot(c.index, c / 1e5, color=col, lw=1.8, label=k)
ax.set_yscale("log"); ax.yaxis.set_major_formatter(lambda v, _: f"Rs {v:g}L")
ax.legend(frameon=False, fontsize=8, loc="upper left")
ax.set_title("No-target version: similar end point to the breakout", loc="left",
             fontsize=10.5, fontweight="bold", color=DARK)
ax.set_ylabel("Equity (log scale)", color=GREY, fontsize=8)
style(ax); fig.tight_layout(); p = ROOT / "reports" / "_p1.png"; fig.savefig(p); plt.close(fig); charts.append(p)

fig, ax = plt.subplots(figsize=(7.2, 2.8), dpi=200)
for k, (c, col) in curves.items():
    ax.plot(c.index, (c / c.cummax() - 1) * 100, color=col, lw=1.4, label=k)
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax.legend(frameon=False, fontsize=8, loc="lower left")
ax.set_title("Shallower drawdowns than the breakout", loc="left", fontsize=10.5, fontweight="bold", color=DARK)
ax.set_ylabel("Drawdown from peak", color=GREY, fontsize=8)
style(ax); fig.tight_layout(); p = ROOT / "reports" / "_p2.png"; fig.savefig(p); plt.close(fig); charts.append(p)

lab = [e.replace(" (close<EMA61)", "") for e in S.index]
fig, ax = plt.subplots(figsize=(7.2, 2.8), dpi=200)
v = S["CAGR %"].values
ax.bar(range(len(v)), v, 0.55, color=[DARK] + [BLUE] * (len(v) - 1), zorder=2)
for x, y in enumerate(v):
    ax.text(x, y + 0.15, f"{y:.1f}%", ha="center", fontsize=7.5, color=DARK)
ax.set_xticks(range(len(v)), lab); ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax.set_title("CAGR by exit: fixed targets cut off the big winners", loc="left",
             fontsize=10.5, fontweight="bold", color=DARK)
style(ax); fig.tight_layout(); p = ROOT / "reports" / "_p3.png"; fig.savefig(p); plt.close(fig); charts.append(p)

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=17, leading=21, alignment=0,
                    textColor=colors.HexColor(DARK), spaceAfter=2)
SUB = ParagraphStyle("SUB", parent=ss["Normal"], fontSize=9, textColor=colors.HexColor(GREY))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12.5, textColor=colors.HexColor(DARK),
                    spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("P", parent=ss["Normal"], fontSize=9.5, leading=13.5, spaceAfter=4)
BL = ParagraphStyle("BL", parent=P, leftIndent=10, spaceAfter=2)
SM = ParagraphStyle("SM", parent=P, fontSize=8, leading=10.5, textColor=colors.HexColor(GREY))


def table(rows, widths, num_from=1):
    tb = Table(rows, colWidths=widths, repeatRows=1)
    tb.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.8), ("FONT", (0, 1), (-1, -1), "Helvetica", 7.8),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(DARK)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("ALIGN", (num_from, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return tb


n, b = S.loc[NT], SB.loc[NT]
tg = S.drop(index=NT)
story = [
    Paragraph("EMA61 Trend + Stochastic RSI Pullback (Monthly)", H1),
    Paragraph("Rs 1,00,000 capital · 1% risk per trade · max 8 open trades · NIFTY 500 constituents (499 stocks) · "
              "Jan 2000 – Nov 2026 · prepared 17 Nov 2026", SUB),
    Paragraph("Data: actual traded prices (adjusted for splits and bonuses, not for dividends; dividend income is not counted). Junk pre-listing quotes removed. Re-run on 17 Nov 2026.", SM),
    Spacer(1, 8),
    Paragraph("Answer", H2),
    Paragraph(f"With no fixed target, the pullback strategy made <b>{n['CAGR %']:.1f}% CAGR with a "
              f"{n['Max DD %']:.0f}% maximum drawdown</b>, against {b['CAGR %']:.1f}% and {b['Max DD %']:.0f}% "
              f"for the EMA61 breakout at the same sizing. Same return, a much smaller drawdown and a higher "
              f"win rate ({n['Win %']:.0f}% vs {b['Win %']:.0f}%). Fixed targets of 8–30% earn only "
              f"{tg['CAGR %'].min():.1f}–{tg['CAGR %'].max():.1f}% a year.", P),
    Paragraph(f"The worst drawdown ran from {peak:%b %Y} to {trough:%b %Y}. It rests on only "
              f"{int(n['Trades taken'])} trades in 27 years, so the result needs robustness checks before "
              f"real money is used.", P),
    Paragraph("Rules", H2),
    table([["Rule", "Value"],
           ["Trend", "Close above EMA61 on monthly, weekly (last completed week) and daily charts at the month's close"],
           ["Momentum", "Monthly RSI(14) > 50"],
           ["Trigger", "Monthly Stochastic RSI (14,14,3,3): %K crosses above %D this month, with %D below 30"],
           ["Entry", "Next month, buy when price goes above the signal candle's high"],
           ["Stop", "Signal candle's low (fixed)"],
           ["Exits", "Targets 8%, 15%, 20%, 30%, or no target (exit on monthly close below EMA61)"],
           ["Sizing", "1% of starting capital (Rs 1,000) at risk per trade; max 8 open trades"],
           ["Costs", "Sharekhan delivery 0.465% per side + 0.1% slippage per side"]],
          [24 * mm, 150 * mm], num_from=9),
    KeepTogether([Paragraph("Equity", H2), Image(str(charts[0]), width=172 * mm, height=76 * mm)]),
    KeepTogether([Paragraph("Drawdown", H2), Image(str(charts[1]), width=172 * mm, height=67 * mm)]),
    KeepTogether([Paragraph("Return by exit", H2), Image(str(charts[2]), width=172 * mm, height=67 * mm)]),
]
cols = [("CAGR %", "{:.1f}"), ("Max DD %", "{:.1f}"), ("Final equity (Rs)", "{:,.0f}"),
        ("Trades taken", "{:,.0f}"), ("Signals skipped", "{:,.0f}"), ("Win %", "{:.1f}"),
        ("Median trade %", "{:.1f}"), ("Avg hold days", "{:.0f}"), ("Median stop %", "{:.1f}"),
        ("Avg deployed %", "{:.1f}"), ("Worst trade % of capital", "{:.1f}")]
hdr = ["Exit", "CAGR %", "Max DD %", "Final equity", "Trades", "Skipped", "Win %", "Median %",
       "Avg hold d", "Stop %", "Deployed %", "Worst %"]
rows = [hdr] + [[i.replace(" (close<EMA61)", "")] + [f.format(r[c]) for c, f in cols] for i, r in S.iterrows()]
story += [Paragraph("Full results", H2),
          table(rows, [20 * mm, 13 * mm, 15 * mm, 18 * mm, 12 * mm, 13 * mm, 11 * mm, 14 * mm, 15 * mm,
                       12 * mm, 16 * mm, 13 * mm]),
          Paragraph("Median % = median net trade return. Stop % = median stop distance below entry. Deployed % = "
                    "open positions / equity, averaged over all days. Worst % = worst trade as a share of "
                    "starting capital.", SM)]
cmp_rows = [["No target, 1% / 8", "CAGR %", "Max DD %", "Win %", "Trades", "Median trade %", "Deployed %"]]
for name, r in [("EMA61 breakout", b), ("Stochastic RSI pullback", n)]:
    cmp_rows.append([name, f"{r['CAGR %']:.1f}", f"{r['Max DD %']:.1f}", f"{r['Win %']:.0f}",
                     f"{int(r['Trades taken'])}", f"{r['Median trade %']:.1f}", f"{r['Avg deployed %']:.0f}"])
story += [KeepTogether([Paragraph("Against the EMA61 breakout", H2),
                        table(cmp_rows, [44 * mm, 20 * mm, 22 * mm, 18 * mm, 18 * mm, 28 * mm, 24 * mm])])]
pts = [
    "<b>Better entries, same return.</b> Buying a pullback in a confirmed uptrend avoids the breakout's late "
    f"entries; the drawdown is {n['Max DD %'] - b['Max DD %']:.0f} points smaller and more trades win "
    f"({n['Win %']:.0f}% vs {b['Win %']:.0f}%).",
    f"<b>Let winners run on monthly charts.</b> The average no-target trade gained {n['Avg trade %']:.0f}% while "
    f"the median lost {-n['Median trade %']:.1f}%: a few multi-year winners pay for everything, and fixed "
    f"targets remove them.",
    f"<b>The stop is wide.</b> The median stop is {n['Median stop %']:.0f}% below entry, so each position is "
    f"about Rs {n['Avg position (Rs)']:,.0f} and target versions leave about 80% of capital idle.",
    f"<b>Small sample.</b> {int(n['Trades taken'])} trades is too few to be confident; results could shift a "
    f"lot with small rule changes.",
    "<b>Survivorship bias:</b> today's NIFTY 500 members only, so returns are optimistic. Risk is a % of "
    "starting capital, so position size does not grow with the account.",
]
story += [Paragraph("What the study shows", H2)] + [Paragraph(x, BL, bulletText="•") for x in pts]
nxt = ["<b>Robustness:</b> oversold level 20 and 40; test 2000–2012 and 2013–2026 separately.",
       "<b>Market filter:</b> no new entries when NIFTY is below its 200-day average.",
       "<b>Size from current equity</b> so the account compounds."]
story += [Paragraph("Next tests", H2)] + [Paragraph(x, BL, bulletText="•") for x in nxt]
story += [Paragraph("How to reproduce", H2),
          Paragraph("<font face='Courier' size='8'>python examples/stochrsi_pullback_study.py --risk 1 --max-pos 8"
                    "<br/>python reports/stochrsi_pullback_report.py</font>", P),
          Paragraph("Code: lib/stochrsi_mtf.py (signals and exits), lib/portfolio.py (shared-capital simulator). "
                    "For research and education only; not investment advice.", SM)]


def footer(c, d):
    c.setFont("Helvetica", 7.5); c.setFillColor(colors.HexColor(GREY))
    c.drawString(18 * mm, 10 * mm, "EMA61 trend + Stochastic RSI pullback – monthly")
    c.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {d.page}")


SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                  bottomMargin=16 * mm, title="Stochastic RSI Pullback").build(
    story, onFirstPage=footer, onLaterPages=footer)
for c in charts:
    c.unlink()
print(OUT, peak.date(), trough.date())
