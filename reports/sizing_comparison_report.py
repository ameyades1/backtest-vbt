"""Build reports/ema61_sizing_r1p8_vs_r2p4.pdf: 1% risk / 8 positions vs 2% risk / 4 positions.

Reads data/sizing_r1_p8 and data/sizing_r2_p4 written by examples/position_sizing_study.py.
"""
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
OUT = ROOT / "reports" / "ema61_sizing_r1p8_vs_r2p4.pdf"
BLUE, GREY, DARK, LIGHT = "#2563eb", "#64748b", "#0f172a", "#93c5fd"
NT = "No target (close<EMA61)"
CFG = {"1% risk, 8 pos.": "sizing_r1_p8", "2% risk, 4 pos.": "sizing_r2_p4"}
COL = {"1% risk, 8 pos.": BLUE, "2% risk, 4 pos.": DARK}

S, EQ, DEP = {}, {}, {}
for k, d in CFG.items():
    S[k] = pd.read_csv(ROOT / "data" / d / "summary.csv", index_col=0)
    EQ[k] = pd.read_csv(ROOT / "data" / d / "equity.csv", index_col=0, parse_dates=True)
    DEP[k] = pd.read_csv(ROOT / "data" / d / "deployed.csv", index_col=0, parse_dates=True)
A, B_ = "1% risk, 8 pos.", "2% risk, 4 pos."


def dd_info(eq):
    dd = eq / eq.cummax() - 1
    trough = dd.idxmin()
    peak = eq[:trough].idxmax()
    return dd, peak, trough


dd_a, peak_a, trough_a = dd_info(EQ[A][NT])
dep_peak = DEP[A][NT][peak_a:trough_a].mean() * 100


def style(ax):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=GREY, length=0, labelsize=8)
    ax.grid(axis="y", color="#e2e8f0", zorder=0)


charts = []
# chart 1: equity curves, no target
fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=200)
for k in CFG:
    ax.plot(EQ[k].index, EQ[k][NT] / 1e5, color=COL[k], lw=1.8, label=k)
ax.set_yscale("log")
ax.yaxis.set_major_formatter(lambda v, _: f"Rs {v:g}L")
ax.legend(frameon=False, fontsize=8, loc="upper left")
ax.set_title("No-target version: both setups end in the same place", loc="left",
             fontsize=10.5, fontweight="bold", color=DARK)
ax.set_ylabel("Equity (log scale)", color=GREY, fontsize=8)
style(ax); fig.tight_layout(); p = ROOT / "reports" / "_s1.png"; fig.savefig(p); plt.close(fig); charts.append(p)

# chart 2: drawdown curves, no target
fig, ax = plt.subplots(figsize=(7.2, 2.8), dpi=200)
for k in CFG:
    dd = EQ[k][NT] / EQ[k][NT].cummax() - 1
    ax.plot(dd.index, dd * 100, color=COL[k], lw=1.4, label=k)
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax.legend(frameon=False, fontsize=8, loc="lower left")
ax.set_title("Drawdowns are similar: more positions did not help in 2008",
             loc="left", fontsize=10.5, fontweight="bold", color=DARK)
ax.set_ylabel("Drawdown from peak", color=GREY, fontsize=8)
style(ax); fig.tight_layout(); p = ROOT / "reports" / "_s2.png"; fig.savefig(p); plt.close(fig); charts.append(p)

# chart 3: CAGR by exit, grouped bars
exits = list(S[A].index)
lab = [e.replace(" (close<EMA61)", "") for e in exits]
fig, ax = plt.subplots(figsize=(7.2, 2.8), dpi=200)
w = 0.38
for i, k in enumerate(CFG):
    xs = [j + (i - 0.5) * w for j in range(len(exits))]
    v = S[k]["CAGR %"].values
    ax.bar(xs, v, w, color=COL[k] if k == A else "#475569", label=k, zorder=2)
    for x, y in zip(xs, v):
        ax.text(x, y + 0.15, f"{y:.1f}", ha="center", fontsize=7, color=DARK)
ax.set_xticks(range(len(exits)), lab)
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax.legend(frameon=False, fontsize=8, loc="upper right")
ax.set_title("CAGR by exit: only the no-target version earns a real return",
             loc="left", fontsize=10.5, fontweight="bold", color=DARK)
style(ax); fig.tight_layout(); p = ROOT / "reports" / "_s3.png"; fig.savefig(p); plt.close(fig); charts.append(p)

# ---- document
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


na, nb = S[A].loc[NT], S[B_].loc[NT]
fmt = lambda d: d.strftime("%b %Y")
story = [
    Paragraph("EMA61 Breakout: 1% Risk / 8 Positions vs 2% Risk / 4 Positions", H1),
    Paragraph("Rs 1,00,000 capital · NIFTY 500 · monthly signals · Jan 2000 – Nov 2026 · "
              "prepared 17 Nov 2026", SUB),
    Paragraph("Data: actual traded prices (adjusted for splits and bonuses, not for dividends; dividend income is not counted). Junk pre-listing quotes removed. Re-run on 17 Nov 2026.", SM),
    Spacer(1, 8),
    Paragraph("Answer", H2),
    Paragraph(f"Halving the risk per trade and doubling the slots gave <b>about the same return and no "
              f"smaller drawdown</b>. In the no-target version, 1% / 8 made {na['CAGR %']:.1f}% CAGR with a "
              f"{na['Max DD %']:.0f}% maximum drawdown; 2% / 4 made {nb['CAGR %']:.1f}% with "
              f"{nb['Max DD %']:.0f}%.", P),
    Paragraph(f"The drawdown is not caused by stop losses. It is open profit given back: from "
              f"{fmt(peak_a)} to {fmt(trough_a)} the 1% / 8 portfolio was on average "
              f"{dep_peak:.0f}% invested, holding stocks that all fell together. The exit (a monthly close "
              f"below EMA61) reacts too slowly in a crash, so more, smaller positions do not protect the "
              f"account.", P),
    Paragraph("Setup", H2),
    table([["Rule", "Value"],
           ["Capital", "Rs 1,00,000; risk is a % of starting capital, not of current equity"],
           ["Setup A", "1% risk (Rs 1,000) per trade, max 8 open trades, total open risk ≤ 8%"],
           ["Setup B", "2% risk (Rs 2,000) per trade, max 4 open trades, total open risk ≤ 8%"],
           ["Signal", "Monthly Open < EMA61 < Close; buy above that candle's high next month"],
           ["Stop", "Breakout candle low (fixed)"],
           ["Exits", "Targets 8%, 15%, 20%, 30%, or no target (exit on monthly close below EMA61)"],
           ["Costs", "Sharekhan delivery 0.465% per side + 0.1% slippage per side"]],
          [30 * mm, 144 * mm], num_from=9),
    KeepTogether([Paragraph("Equity", H2), Image(str(charts[0]), width=172 * mm, height=76 * mm)]),
    KeepTogether([Paragraph("Drawdown", H2), Image(str(charts[1]), width=172 * mm, height=67 * mm)]),
    KeepTogether([Paragraph("Return by exit", H2), Image(str(charts[2]), width=172 * mm, height=67 * mm)]),
]

cols = [("CAGR %", "{:.1f}"), ("Max DD %", "{:.1f}"), ("Final equity (Rs)", "{:,.0f}"),
        ("Trades taken", "{:,.0f}"), ("Signals skipped", "{:,.0f}"), ("Win %", "{:.1f}"),
        ("Avg position (Rs)", "{:,.0f}"), ("Avg deployed %", "{:.1f}"), ("Avg open positions", "{:.1f}"),
        ("Worst trade % of capital", "{:.1f}")]
hdr = ["Exit", "Setup", "CAGR %", "Max DD %", "Final equity", "Trades", "Skipped", "Win %",
       "Avg pos.", "Deployed %", "Open pos.", "Worst %"]
rows = [hdr]
for e in exits:
    for k in CFG:
        r = S[k].loc[e]
        rows.append([e.replace(" (close<EMA61)", "") if k == A else "", k.replace(" pos.", "")]
                    + [f.format(r[c]) for c, f in cols])
story += [Paragraph("Full results", H2),
          table(rows, [18 * mm, 18 * mm, 12 * mm, 14 * mm, 17 * mm, 11 * mm, 13 * mm, 11 * mm,
                       13 * mm, 16 * mm, 14 * mm, 13 * mm], num_from=2),
          Paragraph("Deployed % = market value of open positions / equity, averaged over all trading days. "
                    "Worst % = worst single trade as a share of starting capital.", SM)]

t15 = S[A].loc["Target 15%"]
pts = [
    f"<b>The no-target exit is the only version that pays.</b> Win rate {na['Win %']:.0f}% and a median "
    f"trade of {na['Median trade %']:.1f}%, but a few multi-year winners lift the average trade to "
    f"{na['Avg trade %']:.0f}%. Every fixed target ({min(S[k].drop(index=NT)['CAGR %'].min() for k in CFG):.1f}–{max(S[k].drop(index=NT)['CAGR %'].max() for k in CFG):.1f}% CAGR) cuts those winners short.",
    f"<b>Fixed-target versions do slightly worse at 1% / 8.</b> Each position is only about "
    f"Rs {S[A]['Avg position (Rs)'].mean():,.0f}, so on average just "
    f"{S[A].drop(index=NT)['Avg deployed %'].min():.0f}–{S[A].drop(index=NT)['Avg deployed %'].max():.0f}% "
    f"of capital is invested and the rest sits idle.",
    f"<b>Gaps break the risk limit.</b> With only 1% at risk, the worst Target 15% trade still lost "
    f"{-t15['Worst trade % of capital']:.1f}% of capital after gapping through its stop.",
    "<b>Returns are understated.</b> Risk is fixed on starting capital, so position size never grows "
    "with the account.",
    "<b>Survivorship bias:</b> only today's NIFTY 500 members are tested, so returns are optimistic.",
]
story += [Paragraph("What the study shows", H2)] + [Paragraph(x, BL, bulletText="•") for x in pts]
nxt = [
    "<b>Size from current equity</b> instead of starting capital, so the account compounds.",
    "<b>Add a market regime filter:</b> no new entries when NIFTY is below its 200-day average, or "
    "reduced exposure when India VIX is high. This targets the market-wide crashes behind the drawdown.",
    "<b>Protect open profit:</b> keep the monthly EMA61 for direction, but trail a weekly ATR stop once a "
    "trade is well in profit.",
]
story += [Paragraph("Next tests", H2)] + [Paragraph(x, BL, bulletText="•") for x in nxt]
story += [Paragraph("How to reproduce", H2),
          Paragraph("<font face='Courier' size='8'>python examples/position_sizing_study.py --risk 1 --max-pos 8"
                    "<br/>python examples/position_sizing_study.py --risk 2 --max-pos 4"
                    "<br/>python reports/sizing_comparison_report.py</font>", P),
          Paragraph("For research and education only; not investment advice.", SM)]


def footer(c, d):
    c.setFont("Helvetica", 7.5); c.setFillColor(colors.HexColor(GREY))
    c.drawString(18 * mm, 10 * mm, "EMA61 breakout – 1% / 8 vs 2% / 4 position sizing")
    c.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {d.page}")


SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                  bottomMargin=16 * mm, title="EMA61 Sizing Comparison").build(
    story, onFirstPage=footer, onLaterPages=footer)
for c in charts:
    c.unlink()
print(OUT, peak_a.date(), trough_a.date(), round(dep_peak, 1))
