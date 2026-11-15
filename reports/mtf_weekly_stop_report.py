"""Build reports/ema61_mtf_weekly_stop.pdf from data/mtf_weekly_stop/summary.csv
(examples/mtf_weekly_stop_study.py) and the candle-low sizing runs in data/sizing_r2_p4, data/sizing_r1_p8.
"""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "ema61_mtf_weekly_stop.pdf"
BLUE, GREY, DARK, LIGHT, RED = "#2563eb", "#64748b", "#0f172a", "#cbd5e1", "#dc2626"
EXITS = ["No target", "Target 8%", "Target 15%", "Target 20%", "Target 30%"]

mtf = pd.read_csv(ROOT / "data" / "mtf_weekly_stop" / "summary.csv")
cl = []
for sz, folder in [("2%/4", "sizing_r2_p4"), ("1%/8", "sizing_r1_p8")]:
    t = pd.read_csv(ROOT / "data" / folder / "summary.csv", index_col=0)
    t.index = [i.replace(" (close<EMA61)", "") for i in t.index]
    t["Sizing"], t["Stop"] = sz, "candle-low"
    cl.append(t.reset_index(names="Exit"))
allr = pd.concat([pd.concat(cl), mtf], ignore_index=True)
LABEL = {"candle-low": "Monthly candle low (previous study)", "fixed": "Previous week low, fixed",
         "trail": "Previous week low, trailing weekly"}


def get(stop, exit_, sizing, col):
    r = allr[(allr.Stop == stop) & (allr.Exit == exit_) & (allr.Sizing == sizing)]
    return float(r[col].iloc[0])


def style(ax):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=GREY, length=0)
    ax.grid(axis="y", color="#e2e8f0", zorder=0)


charts = []
for col, title, fname, fmt in [
    ("CAGR %", "The fixed weekly stop matches, but does not beat, the candle-low stop", "_c1.png", "{:.1f}"),
    ("Avg deployed %", "The weekly stop raises capital deployed from about 20% to about 33%", "_c2.png", "{:.0f}")]:
    fig, ax = plt.subplots(figsize=(7.2, 3.3), dpi=200)
    x = np.arange(len(EXITS)); w = 0.26
    for i, (stop, c, a) in enumerate([("candle-low", GREY, 0.55), ("fixed", BLUE, 1.0), ("trail", DARK, 0.85)]):
        vals = [get(stop, e, "2%/4", col) for e in EXITS]
        ax.bar(x + (i - 1) * w, vals, w * 0.92, color=c, alpha=a, label=LABEL[stop], zorder=2)
        for xi, v in zip(x + (i - 1) * w, vals):
            ax.text(xi, v + (0.4 if v >= 0 else -0.4) * (1 if col == "CAGR %" else 3), fmt.format(v),
                    ha="center", va="bottom" if v >= 0 else "top", fontsize=6.5, color=DARK)
    ax.axhline(0, color=GREY, lw=0.8)
    ax.set_xticks(x, EXITS)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    if col == "CAGR %":
        ax.set_ylim(-12.5, 12)
    else:
        ax.set_ylim(0, 70)
    ax.legend(frameon=False, fontsize=7, loc="upper right", ncol=1)
    ax.set_title(title, loc="left", fontsize=10, fontweight="bold", color=DARK)
    ax.set_ylabel(("CAGR" if col == "CAGR %" else "Avg capital deployed") + " (2% risk, 4 slots)",
                  color=GREY, fontsize=8)
    style(ax); fig.tight_layout(); p = ROOT / "reports" / fname; fig.savefig(p); plt.close(fig); charts.append(p)

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=17, leading=21, alignment=0,
                    textColor=colors.HexColor(DARK), spaceAfter=2)
SUB = ParagraphStyle("SUB", parent=ss["Normal"], fontSize=9, textColor=colors.HexColor(GREY))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12.5, textColor=colors.HexColor(DARK),
                    spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("P", parent=ss["Normal"], fontSize=9.5, leading=13.5, spaceAfter=4)
B = ParagraphStyle("B", parent=P, leftIndent=10, spaceAfter=2)
SM = ParagraphStyle("SM", parent=P, fontSize=8, leading=10.5, textColor=colors.HexColor(GREY))


def table(rows, widths, num_from=1, bold_rows=()):
    tb = Table(rows, colWidths=widths, repeatRows=1)
    st = [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.6), ("FONT", (0, 1), (-1, -1), "Helvetica", 7.6),
          ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(DARK)),
          ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
          ("ALIGN", (num_from, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]
    for r in bold_rows:
        st.append(("FONT", (0, r), (-1, r), "Helvetica-Bold", 7.6))
    tb.setStyle(TableStyle(st))
    return tb


fx = mtf[mtf.Stop == "fixed"]; tr = mtf[mtf.Stop == "trail"]
best = allr.loc[allr["CAGR %"].idxmax()]
sig_cl = 1405
sig_m = int(fx[(fx.Exit == "No target") & (fx.Sizing == "2%/4")]["Signals"].iloc[0])
med_stop = float(fx["Median stop %"].median())
story = [
    Paragraph("EMA61 Breakout: Triple Timeframe with a Weekly Stop", H1),
    Paragraph("Rs 1,00,000 capital · NIFTY 500 · monthly breakout, weekly + daily EMA61 filters · "
              "Jan 2000 – Nov 2026 · Sharekhan costs · prepared 16 Nov 2026", SUB),
    Spacer(1, 8),
    Paragraph("Answer", H2),
    Paragraph(f"The idea works as intended on capital use but not on returns. The previous week's low "
              f"gives a median stop of <b>{med_stop:.1f}%</b> instead of 18.3%, so each trade is about twice "
              f"the size and average capital deployed rises from about 20% to about 33%. CAGR does not rise "
              f"with it: the tighter stop is hit more often and costs take a bigger share of each move.", P),
    Paragraph(f"<b>Use the weekly stop fixed, with no target or a 30% target.</b> The best result in either "
              f"study is the fixed weekly stop with no target at {best['Sizing'].replace('%/', '% risk / ')} slots: "
              f"<b>{best['CAGR %']:.1f}% CAGR</b>, {best['Max DD %']:.0f}% max drawdown. Trailing the stop to each "
              f"week's low loses money in every version.", P),
    Paragraph("Rules", H2),
    table([["Rule", "Definition"],
           ["Monthly signal", "Monthly candle with Open < EMA61 < Close"],
           ["Entry", "Next month, first day with High > breakout High (fill at the level, or the Open on a gap-up)"],
           ["Weekly filter", "On that day, the last completed week closed at or above the weekly EMA61"],
           ["Daily filter", "The previous day closed at or above the daily EMA61"],
           ["Stop, fixed", "Low of the last completed week before entry; never moves"],
           ["Stop, trailing", "Same start; after each completed week, raised to that week's Low"],
           ["Exits", "Targets 8%, 15%, 20%, 30%, or no target (next open after a monthly close below EMA61)"],
           ["Sizing", "qty = risk / (entry − stop); 2% risk with 4 slots, or 1% risk with 8 slots; "
                      "tightest-stop signals fill free slots first"],
           ["Costs", "Sharekhan delivery 0.465% per side + 0.1% slippage per side"]],
          [28 * mm, 144 * mm], num_from=9),
    Paragraph(f"The weekly and daily filters removed {(1 - sig_m / sig_cl) * 100:.0f}% of monthly signals "
              f"({sig_cl:,} to {sig_m:,}).", SM),
    KeepTogether([Paragraph("Returns", H2), Image(str(charts[0]), width=172 * mm, height=79 * mm)]),
    KeepTogether([Paragraph("Capital deployed", H2), Image(str(charts[1]), width=172 * mm, height=79 * mm)]),
    Paragraph("Full results", H2),
]
hdr = ["Stop", "Exit", "Sizing", "CAGR %", "Max DD %", "Trades", "Win %", "Avg pos. (Rs)", "Deployed %",
       "Slots full %", "Worst %"]
rows, bold = [hdr], []
order = {"candle-low": 0, "fixed": 1, "trail": 2}
srt = allr.assign(o=allr.Stop.map(order), e=allr.Exit.map(EXITS.index)).sort_values(["o", "e", "Sizing"],
                                                                                   ascending=[True, True, False])
names = {"candle-low": "Candle low", "fixed": "Week low, fixed", "trail": "Week low, trail"}
for _, r in srt.iterrows():
    rows.append([names[r.Stop], r.Exit, r.Sizing, f"{r['CAGR %']:.1f}", f"{r['Max DD %']:.1f}",
                 f"{int(r['Trades taken']):,}", f"{r['Win %']:.1f}", f"{r['Avg position (Rs)']:,.0f}",
                 f"{r['Avg deployed %']:.1f}", f"{r['Days all slots full %']:.1f}",
                 f"{r['Worst trade % of capital']:.1f}"])
    if r.Stop == best.Stop and r.Exit == best.Exit and r.Sizing == best.Sizing:
        bold.append(len(rows) - 1)
story += [table(rows, [24 * mm, 18 * mm, 12 * mm, 13 * mm, 15 * mm, 13 * mm, 12 * mm, 19 * mm, 17 * mm,
                       17 * mm, 13 * mm], num_from=3, bold_rows=bold),
          Paragraph("Win % is of trades actually taken by the portfolio. Worst % = worst single trade as % of "
                    "starting capital. Bold = best CAGR.", SM),
          Paragraph("Trade duration and gain", H2),
          Paragraph("The weekly stop shortens trades: at the same exit, fixed weekly-stop trades are held for "
                    "a shorter median time than candle-low trades, and trailing ones shorter still.", P)]
dur = [["Stop", "Exit", "Sizing", "Avg hold (days)", "Median hold (days)", "Avg trade %", "Median trade %"]]
for _, r in srt.iterrows():
    dur.append([names[r.Stop], r.Exit, r.Sizing, f"{r['Avg hold days']:.0f}", f"{r['Median hold days']:.0f}",
                f"{r['Avg trade %']:.1f}", f"{r['Median trade %']:.1f}"])
story += [table(dur, [28 * mm, 22 * mm, 16 * mm, 26 * mm, 28 * mm, 24 * mm, 26 * mm], num_from=3),
          Paragraph("Trades taken by the portfolio only. Trade % = net return per trade after costs. Hold = "
                    "calendar days from entry to exit; open trades counted to 13 Nov 2026.", SM),
          Paragraph("Why the weekly stop does not add return", H2)]
w8f = get("fixed", "Target 8%", "2%/4", "Win %"); w8c = get("candle-low", "Target 8%", "2%/4", "Win %")
pts = [
    f"<b>More stop-outs:</b> a breakout often dips back below the previous week's low before it runs. With "
    f"an 8% target the win rate falls from {w8c:.0f}% (candle-low stop) to {w8f:.0f}%, and the small targets "
    f"turn loss-making after the ~1.13% round-trip cost.",
    "<b>Trailing weekly does not fit a monthly signal:</b> it exits on normal weekly pullbacks, so hundreds of "
    "small losses plus costs drain the account. Every trailing version has negative or near-zero CAGR.",
    f"<b>Gaps hurt more with tight stops:</b> the worst trade lost "
    f"{-mtf[mtf.Sizing == '2%/4']['Worst trade % of capital'].min():.1f}% of capital at 2% risk, because a gap "
    f"below a 10% stop is large relative to the risk taken.",
    f"<b>Deployment is still well short of 100%:</b> total open risk is capped at 8%, so a {med_stop:.0f}% stop "
    f"allows at most about {8 / med_stop * 100:.0f}% of capital invested.",
    "<b>Survivorship bias:</b> today's NIFTY 500 members only, so absolute returns are optimistic; the "
    "comparison between stops is the useful part.",
]
story += [Paragraph(x, B, bulletText="•") for x in pts]
story += [Paragraph("Correction to the earlier sizing study", H2),
          Paragraph("A simulator bug valued open positions at zero on dates with no price row, which inflated "
                    "drawdowns. It is fixed, and both this study and the position-sizing PDF use corrected "
                    "figures (for example the no-target drawdown at 2% / 4 slots is −56%, not −66%).", P),
          Paragraph("How to reproduce", H2),
          Paragraph("<font face='Courier' size='8'>python examples/position_sizing_study.py --risk 2 --max-pos 4<br/>"
                    "python examples/position_sizing_study.py --risk 1 --max-pos 8<br/>"
                    "python examples/mtf_weekly_stop_study.py<br/>python reports/mtf_weekly_stop_report.py</font>", P),
          Paragraph("Code: lib/ema61_mtf.py (signals, filters, weekly stop), lib/portfolio.py (shared capital). "
                    "For research and education only; not investment advice.", SM)]


def footer(c, d):
    c.setFont("Helvetica", 7.5); c.setFillColor(colors.HexColor(GREY))
    c.drawString(18 * mm, 10 * mm, "EMA61 breakout – triple timeframe, weekly stop")
    c.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {d.page}")


SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                  bottomMargin=16 * mm, title="EMA61 Breakout: Triple Timeframe, Weekly Stop").build(
    story, onFirstPage=footer, onLaterPages=footer)
for c in charts:
    c.unlink()
print(OUT)
