"""Build reports/ema61_targets_nifty500.pdf from data/ema61_NIFTY500_M_targets.csv.

    python examples/ema61_breakout.py --index NIFTY500 --targets 4 8 12 15 20 30
    python reports/ema61_targets_report.py
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import duration_section
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                Image, KeepTogether)

ROOT = Path(__file__).resolve().parent.parent
CSV = ROOT / "data" / "ema61_NIFTY500_M_targets.csv"
OUT = ROOT / "reports" / "ema61_targets_nifty500.pdf"
CHART = ROOT / "reports" / "_win_vs_breakeven.png"
BLUE, GREY, DARK = "#2563eb", "#64748b", "#0f172a"

t = pd.read_csv(CSV, index_col=0)
t["BE"] = -t["Avg loss %"] / (t["Avg win %"] - t["Avg loss %"]) * 100
base = t.iloc[0]
tg = t.iloc[1:]
labels = [i.replace("Target ", "") for i in tg.index]

# ---- chart: win rate vs break-even win rate
fig, ax = plt.subplots(figsize=(7.2, 3.6), dpi=200)
x = range(len(tg))
ax.bar(x, tg["Win %"], width=0.5, color=BLUE, alpha=0.85, label="Actual win rate", zorder=2)
for i, (w, be) in enumerate(zip(tg["Win %"], tg["BE"])):
    ax.hlines(be, i - 0.32, i + 0.32, color=DARK, lw=2.4, zorder=3)
    ax.text(i, w + 2, f"{w:.1f}%", ha="center", fontsize=8.5, fontweight="bold", color=DARK)
    ax.text(i + 0.36, (w + be) / 2, f"+{w - be:.1f}", fontsize=8, color=GREY, va="center")
ax.hlines([], 0, 0, color=DARK, lw=2.4, label="Break-even win rate")
ax.set_xticks(list(x), labels)
ax.set_ylim(0, 100)
ax.set_ylabel("Win rate (%)", color=GREY)
ax.set_xlabel("Profit target above entry", color=GREY)
ax.grid(axis="y", color="#e2e8f0", zorder=0)
for s in ("top", "right", "left"):
    ax.spines[s].set_visible(False)
ax.tick_params(colors=GREY, length=0)
ax.legend(frameon=False, fontsize=8, loc="upper right")
ax.set_title("Win rate clears break-even by more as the target widens",
             loc="left", fontsize=10.5, fontweight="bold", color=DARK)
fig.tight_layout()
fig.savefig(CHART)
plt.close(fig)

# ---- document
ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=17, leading=21, alignment=0,
                    textColor=colors.HexColor(DARK), spaceAfter=2)
SUB = ParagraphStyle("SUB", parent=ss["Normal"], fontSize=9, textColor=colors.HexColor(GREY))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12.5, textColor=colors.HexColor(DARK),
                    spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("P", parent=ss["Normal"], fontSize=9.5, leading=13.5, spaceAfter=4)
B = ParagraphStyle("B", parent=P, leftIndent=10, bulletIndent=0, spaceAfter=2)
SM = ParagraphStyle("SM", parent=P, fontSize=8, leading=10.5, textColor=colors.HexColor(GREY))
CELL = ParagraphStyle("CELL", parent=P, fontSize=8, leading=10, spaceAfter=0)
HDR = ParagraphStyle("HDR", parent=CELL, textColor=colors.white, alignment=2, fontSize=7.5, leading=9)
HDRL = ParagraphStyle("HDRL", parent=HDR, alignment=0)


def table(rows, widths, num_cols=()):
    rows = [[Paragraph(str(c), CELL) if isinstance(c, str) and len(c) > 18 else c for c in r]
            for r in rows]
    tb = Table(rows, colWidths=widths, repeatRows=1)
    st = [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),
          ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
          ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
          ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(DARK)),
          ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
          ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
          ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.HexColor("#cbd5e1"))]
    for c in num_cols:
        st.append(("ALIGN", (c, 0), (c, -1), "RIGHT"))
    tb.setStyle(TableStyle(st))
    return tb


f1 = lambda v: f"{v:,.1f}"
f2 = lambda v: f"{v:,.2f}"
w4, w30 = tg.iloc[0], tg.iloc[-1]
story = [
    Paragraph("EMA61 Breakout: Fixed Targets with Candle-Low Stop", H1),
    Paragraph("NIFTY 500 stocks · monthly signals · Jan 2000 – Nov 2026 · "
              "after Sharekhan costs · prepared 17 Nov 2026", SUB),
    Paragraph("Data: actual traded prices (adjusted for splits and bonuses, not for dividends; dividend income is not counted). Junk pre-listing quotes removed. Re-run on 17 Nov 2026.", SM),
    Spacer(1, 8),
    Paragraph("Summary", H2),
    Paragraph(f"Win rate ranges from <b>{w4['Win %']:.1f}%</b> with a 4% target to "
              f"<b>{w30['Win %']:.1f}%</b> with a 30% target, across {int(tg['Trades'].min()):,} to "
              f"{int(tg['Trades'].max()):,} trades in 499 stocks. A high win rate does not mean a "
              f"profitable strategy here: the stop at the breakout candle's low sits on average "
              f"{tg['Avg stop dist %'].mean():.1f}% below entry, so one loss of about 20% wipes out "
              f"several small wins.", P),
    Paragraph(f"<b>4% target:</b> wins {w4['Win %']:.1f}% of the time but averages only "
              f"{w4['Avg trade %']:+.2f}% per trade after costs, which is break-even.", B, bulletText="•"),
    Paragraph(f"<b>30% target:</b> wins {w30['Win %']:.1f}% of the time and averages "
              f"{w30['Avg trade %']:+.2f}% per trade, the best of the fixed targets.", B, bulletText="•"),
    Paragraph(f"<b>No target</b> (exit on a monthly close below EMA61): wins only "
              f"{base['Win %']:.1f}% of the time but averages {base['Avg trade %']:+.0f}% per trade, "
              f"because a few winners run for years. It is the only version that compounds "
              f"meaningfully: {base['CAGR %']:.1f}% CAGR on the whole book, "
              f"{base['Max DD %']:.1f}% max drawdown.", B, bulletText="•"),
    Paragraph("Wider targets are better at every step tested. For a fixed-target version, "
              "20% to 30% is the usable range.", P),
    Paragraph("Strategy rules", H2),
    table([["Rule", "Definition"],
           ["Signal candle", "Monthly candle with Open < EMA61 < Close (EMA of monthly closes, 61 periods)"],
           ["Entry", "Buy-stop at the breakout candle's High, valid for the next month only; a gap-up fills at the day's Open"],
           ["Stop-loss", "Breakout candle's Low; a gap-down below it fills at the day's Open"],
           ["Target", "Entry + 4%, 8%, 12%, 15%, 20% or 30%; a gap-up above it fills at the day's Open"],
           ["Same-day conflict", "If one daily candle touches both stop and target, the stop is assumed to hit first"],
           ["Entry day", "Only the close is checked against stop and target (intraday order unknown)"],
           ["Baseline", "Same entry and stop, no target: exit at next open after a monthly close below EMA61"],
           ["Universe", "Current NIFTY 500 members with Yahoo data (499 of 501), daily data 1996 – 13 Nov 2026"],
           ["Costs", "Sharekhan delivery fees 0.465% per side + 0.1% slippage per side (~1.13% round trip)"],
           ["Sizing", "Rs 1 lakh per stock, all-in on each trade; one open trade per stock at a time"]],
          [32 * mm, 140 * mm]),
    KeepTogether([Paragraph("Results", H2),
                  Paragraph(f"The 4% target clears its break-even win rate by only "
                            f"{w4['Win %'] - w4['BE']:.1f} points; the 30% target clears it by "
                            f"{w30['Win %'] - w30['BE']:.1f} points.", P),
                  Image(str(CHART), width=172 * mm, height=86 * mm),
                  Paragraph("Bars: actual win rate. Dark tick: win rate needed to break even "
                            "= avg loss / (avg win + avg loss). Grey label: margin in points.", SM)]),
    Spacer(1, 6),
]
rows = [["Exit", "Trades", "Win %", "Avg win %", "Avg loss %", "Avg trade %", "Median trade %",
         "Avg hold (days)", "Median hold (days)", "Stopped %"]]
for name, r in list(tg.iterrows()) + [("No target (close < EMA61)", base)]:
    rows.append([name, f"{int(r['Trades']):,}", f1(r["Win %"]), f2(r["Avg win %"]),
                 f2(r["Avg loss %"]), f2(r["Avg trade %"]), f2(r["Median trade %"]),
                 f"{r['Avg hold days']:.0f}", f"{r['Median hold days']:.0f}", f1(r["Stopped %"])])
story += [
    table([[Paragraph(f"<b>{h}</b>", HDR if i else HDRL) for i, h in enumerate(rows[0])]] + rows[1:],
          [33 * mm, 13 * mm, 12 * mm, 15 * mm, 15 * mm, 16 * mm, 17 * mm, 17 * mm, 18 * mm, 15 * mm],
          num_cols=range(1, 10)),
    Paragraph("Trade % = net return of each trade after costs, winners and losers together. Hold = calendar "
              "days from entry to exit (open trades counted to 13 Nov 2026). A long average with a short "
              "median means most trades end quickly while a few run for years.", SM),
    Paragraph(f"Average stop distance is {tg['Avg stop dist %'].min():.1f}–"
              f"{tg['Avg stop dist %'].max():.1f}% below entry for every row. Book-level CAGR is "
              f"{tg['CAGR %'].min():.1f}–{tg['CAGR %'].max():.1f}% for the fixed targets, since capital "
              f"is invested only {tg['Exposure %'].min():.0f}–{tg['Exposure %'].max():.0f}% of the time.", SM),
    Paragraph("Interpretation and caveats", H2),
    Paragraph("Treat the comparison between targets as reliable and the absolute returns as optimistic.", P),
]
caveats = [
    "<b>Survivorship bias:</b> the universe is today's NIFTY 500, so stocks that collapsed and were "
    "dropped since 2000 are missing. Real win rates and returns would be lower.",
    f"<b>Wide stop, small targets:</b> a ~{tg['Avg stop dist %'].mean():.1f}% average stop against a 4–15% target is a poor "
    "reward-to-risk ratio. A tighter stop (e.g. a weekly candle low) is worth testing separately.",
    "<b>Fill assumptions:</b> every stop and target is assumed to fill, at the level or at the open "
    "on a gap. Sharekhan bracket legs are stop-limit orders, so a deep gap-down may not fill.",
    "<b>Same-day ambiguity:</b> when one daily candle touches both stop and target, the stop is "
    "counted, which makes results slightly pessimistic.",
    f"<b>Few signals per stock:</b> about {base['Trades'] / 499:.1f} trades per stock in 27 years. "
    "Stocks listed after about 2020 cannot signal, because EMA61 needs 61 months of data.",
    "<b>Open trades:</b> trades still open at the end are marked to market on 13 Nov 2026.",
]
story += [Paragraph(c, B, bulletText="•") for c in caveats]
story += [
    Paragraph("How to reproduce", H2),
    Paragraph("<font face='Courier' size='8'>python examples/ema61_breakout.py --index NIFTY500 "
              "--targets 4 8 12 15 20 30<br/>python reports/ema61_targets_report.py</font>", P),
    Paragraph("Code: lib/ema61.py (engine), examples/ema61_breakout.py (runner), lib/costs.py "
              "(Sharekhan cost model). For research and education only; not investment advice.", SM),
]

_i = next(i for i, f in enumerate(story) if isinstance(f, Paragraph) and f.text == "Interpretation and caveats")
story[_i:_i] = duration_section.flowables("Candle low", H2, P, SM, lambda r, w, n: table(r, w, num_cols=range(n, len(r[0]))), mm)


def footer(c, d):
    c.setFont("Helvetica", 7.5)
    c.setFillColor(colors.HexColor(GREY))
    c.drawString(18 * mm, 10 * mm, "EMA61 breakout – fixed targets, NIFTY 500")
    c.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {d.page}")


SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm,
                  topMargin=16 * mm, bottomMargin=16 * mm,
                  title="EMA61 Breakout: Fixed Targets (NIFTY 500)").build(
    story, onFirstPage=footer, onLaterPages=footer)
CHART.unlink()
print(OUT)
