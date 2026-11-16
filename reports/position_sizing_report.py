"""Build reports/ema61_position_sizing.pdf from the CSVs written by
examples/position_sizing_study.py.
"""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
import duration_section
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
import argparse
_a = argparse.ArgumentParser()
_a.add_argument("--risk", type=float, default=2.0)
_a.add_argument("--max-pos", type=int, default=4)
_a = _a.parse_args()
if (_a.risk, _a.max_pos) != (2.0, 4):
    raise SystemExit("The report text is written for the 2% risk / 4 position study; "
                     "use examples/position_sizing_study.py output for other settings.")
D = ROOT / "data" / f"sizing_r{_a.risk:g}_p{_a.max_pos}"
OUT = ROOT / "reports" / ("ema61_position_sizing.pdf" if (_a.risk, _a.max_pos) == (2.0, 4)
                          else f"ema61_position_sizing_r{_a.risk:g}_p{_a.max_pos}.pdf")
CAP, RISK, MAXPOS = 100_000, 100_000 * _a.risk / 100, _a.max_pos
BLUE, GREY, DARK, LIGHT = "#2563eb", "#64748b", "#0f172a", "#cbd5e1"

summ = pd.read_csv(D / "summary.csv", index_col=0)
dep = pd.read_csv(D / "deployed.csv", index_col=0, parse_dates=True)
fills = pd.read_csv(D / "fills_none.csv")
alls = pd.concat([pd.read_csv(D / f"fills_{k}.csv") for k in ["none", "8", "15", "20", "30"]])
sd = (alls.entry - alls.stop) / alls.entry * 100
med_sd = sd.median()
full_pos = RISK / (med_sd / 100)
need_sd = RISK / (CAP / MAXPOS) * 100
charts = []


def style(ax):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=GREY, length=0)
    ax.grid(axis="y", color="#e2e8f0", zorder=0)


# chart 1: position size vs stop distance, with the distribution of actual stops
fig, ax = plt.subplots(figsize=(7.2, 3.4), dpi=200)
x = np.linspace(4, 40, 300)
ax.hist(sd.clip(upper=40), bins=36, range=(4, 40), color=LIGHT, zorder=1,
        weights=np.full(len(sd), 25_000 / len(sd) * 8))
ax.plot(x, RISK / (x / 100), color=BLUE, lw=2.2, zorder=3)
ax.axhline(CAP / MAXPOS, color=DARK, lw=1, ls="--", zorder=2)
ax.text(39.5, CAP / MAXPOS + 900, f"Rs {CAP / MAXPOS:,.0f}: size needed to deploy all capital in {MAXPOS} trades",
        ha="right", fontsize=7.5, color=DARK)
ax.scatter([need_sd], [CAP / MAXPOS], color=DARK, zorder=4, s=18)
ax.annotate(f"needs a stop {need_sd:.0f}% below entry", (need_sd, CAP / MAXPOS), (need_sd + 2.5, 38_000),
            fontsize=7.5, color=DARK, arrowprops=dict(arrowstyle="-", color=DARK, lw=0.6))
ax.scatter([med_sd], [full_pos], color=BLUE, zorder=4, s=22)
ax.annotate(f"median actual stop {med_sd:.1f}% -> Rs {full_pos:,.0f}", (med_sd, full_pos),
            (med_sd + 3, full_pos + 9_000), fontsize=7.5, color=BLUE,
            arrowprops=dict(arrowstyle="-", color=BLUE, lw=0.6))
ax.set_xlim(4, 40); ax.set_ylim(0, 50_000)
ax.yaxis.set_major_formatter(lambda v, _: f"Rs {v / 1000:.0f}k")
ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax.set_xlabel("Stop distance below entry (grey bars: how often each distance occurred)", color=GREY, fontsize=8)
ax.set_ylabel("Position size for Rs 2,000 risk", color=GREY, fontsize=8)
ax.set_title(f"Wide candle-low stops shrink each position to about Rs {full_pos / 1000:.0f}k",
             loc="left", fontsize=10.5, fontweight="bold", color=DARK)
style(ax); fig.tight_layout(); p = ROOT / "reports" / "_c1.png"; fig.savefig(p); plt.close(fig); charts.append(p)

# chart 2: share of capital deployed over time (yearly average)
yr = dep.groupby(dep.index.year).mean() * 100
fig, ax = plt.subplots(figsize=(7.2, 3.0), dpi=200)
show = {"Target 30%": BLUE, "Target 8%": "#93c5fd", "No target (close<EMA61)": DARK}
for col, c in show.items():
    ax.plot(yr.index, yr[col], color=c, lw=2 if c != "#93c5fd" else 1.6, label=col)
ax.axhline(100, color=GREY, lw=0.8, ls=":")
ax.text(yr.index[0], 102, "100% = all capital invested", fontsize=7.5, color=GREY)
ax.set_ylim(0, 110)
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax.legend(frameon=False, fontsize=7.5, loc="upper right", ncol=3, bbox_to_anchor=(1, 0.95))
ax.set_title(f"Fixed-target versions keep about {100 - summ.drop(index='No target (close<EMA61)')['Avg deployed %'].mean():.0f}% of capital idle",
             loc="left", fontsize=10.5, fontweight="bold", color=DARK)
ax.set_ylabel("Capital deployed (yearly avg)", color=GREY, fontsize=8)
style(ax); fig.tight_layout(); p = ROOT / "reports" / "_c2.png"; fig.savefig(p); plt.close(fig); charts.append(p)

# ---- document
ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=17, leading=21, alignment=0,
                    textColor=colors.HexColor(DARK), spaceAfter=2)
SUB = ParagraphStyle("SUB", parent=ss["Normal"], fontSize=9, textColor=colors.HexColor(GREY))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12.5, textColor=colors.HexColor(DARK),
                    spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("P", parent=ss["Normal"], fontSize=9.5, leading=13.5, spaceAfter=4)
B = ParagraphStyle("B", parent=P, leftIndent=10, spaceAfter=2)
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


s = summ
nt, t30 = s.loc["No target (close<EMA61)"], s.loc["Target 30%"]
_eq = pd.read_csv(D / "equity.csv", index_col=0, parse_dates=True)["No target (close<EMA61)"]
_tr = (_eq / _eq.cummax() - 1).idxmin(); _pk = _eq[:_tr].idxmax()
_f = pd.read_csv(D / "fills_none.csv", parse_dates=["entry_date", "exit_date"])
_f["days"] = (_f.exit_date.fillna(_eq.index[-1]) - _f.entry_date).dt.days
_lg = _f.loc[_f.days.idxmax()]
_open = [x.replace(".NS", "") for x in _f[(_f.entry_date <= _pk) & (_f.exit_date.isna() | (_f.exit_date >= _pk))].symbol]
tg = s.drop(index="No target (close<EMA61)")
story = [
    Paragraph("EMA61 Breakout: Does 2% Risk Sizing Deploy the Capital?", H1),
    Paragraph("Rs 1,00,000 capital · Rs 2,000 risk per trade · max 4 open trades · NIFTY 500 · "
              "monthly signals · Jan 2000 – Nov 2026 · prepared 17 Nov 2026", SUB),
    Paragraph("Data: actual traded prices (adjusted for splits and bonuses, not for dividends; dividend income is not counted). Junk pre-listing quotes removed. Re-run on 17 Nov 2026.", SM),
    Spacer(1, 8),
    Paragraph("Answer", H2),
    Paragraph(f"<b>No.</b> With the stop at the breakout candle's low, the strategy never comes close to "
              f"deploying Rs 1,00,000. The fixed-target versions keep on average only "
              f"<b>{tg['Avg deployed %'].min():.0f}–{tg['Avg deployed %'].max():.0f}%</b> of capital invested. "
              f"The no-target version averages {nt['Avg deployed %']:.0f}%, but only because a few early "
              f"positions grew many times over, not because new trades were large.", P),
    Paragraph(f"The cause is the stop distance. The median stop is <b>{med_sd:.1f}%</b> below entry, so "
              f"Rs 2,000 of risk buys a position of about <b>Rs {full_pos:,.0f}</b>. Four such positions "
              f"use about Rs {4 * full_pos:,.0f}. To put Rs {CAP / MAXPOS:,.0f} into each of 4 trades, the "
              f"stop would have to be {need_sd:.0f}% below entry; only "
              f"{(sd <= need_sd).mean() * 100:.1f}% of trades had a stop that tight.", P),
    Paragraph("Sizing rules", H2),
    table([["Rule", "Value"],
           ["Capital", "Rs 1,00,000 (risk is 2% of starting capital, not of current equity)"],
           ["Quantity", "floor(Rs 2,000 / (buy price − stop)), reduced if cash is short"],
           ["Max open trades", "4 (total open risk ≤ 8% of starting capital)"],
           ["Signal", "Monthly Open < EMA61 < Close; buy above that candle's high next month"],
           ["Stop", "Breakout candle low (fixed)"],
           ["Exit variants", "Targets 8%, 15%, 20%, 30%, or no target (exit on monthly close below EMA61)"],
           ["Too many signals", "Exits processed first; then the tightest-stop signals fill free slots; the rest are skipped"],
           ["Costs", "Sharekhan delivery 0.465% per side + 0.1% slippage per side"]],
          [32 * mm, 140 * mm], num_from=9),
    KeepTogether([Paragraph("Why positions stay small", H2), Image(str(charts[0]), width=172 * mm, height=81 * mm),
                  Paragraph(f"Position size = Rs 2,000 / stop distance. Stops measured on all "
                            f"{len(sd):,} trades taken across the five variants: 10th percentile "
                            f"{sd.quantile(.1):.1f}%, median {med_sd:.1f}%, 90th percentile {sd.quantile(.9):.1f}%.", SM)]),
    KeepTogether([Paragraph("Capital deployed over time", H2), Image(str(charts[1]), width=172 * mm, height=72 * mm)]),
    Paragraph("Results by exit", H2),
]
cols = [("Final equity (Rs)", "{:,.0f}"), ("CAGR %", "{:.1f}"), ("Max DD %", "{:.1f}"),
        ("Trades taken", "{:,.0f}"), ("Signals skipped", "{:,.0f}"), ("Win %", "{:.1f}"),
        ("Avg position (Rs)", "{:,.0f}"), ("Avg deployed %", "{:.1f}"), ("Days all slots full %", "{:.1f}"),
        ("Worst trade % of capital", "{:.1f}")]
hdr = ["Exit", "Final equity", "CAGR %", "Max DD %", "Trades", "Skipped", "Win %", "Avg pos.",
       "Deployed %", "All 4 full %", "Worst %"]
rows = [hdr] + [[i.replace(" (close<EMA61)", "")] + [f.format(r[c]) for c, f in cols] for i, r in s.iterrows()]
story += [table(rows, [22 * mm, 18 * mm, 13 * mm, 15 * mm, 12 * mm, 14 * mm, 12 * mm, 15 * mm, 17 * mm, 19 * mm, 15 * mm]),
          Paragraph("Deployed % = market value of open positions / equity, averaged over all trading days.", SM)]
dur = [["Exit", "Trades", "Avg hold (days)", "Median hold (days)", "Avg hold (months)", "Avg trade %",
        "Median trade %"]]
for i, r in s.iterrows():
    dur.append([i.replace(" (close<EMA61)", ""), f"{int(r['Trades taken']):,}", f"{r['Avg hold days']:.0f}",
                f"{r['Median hold days']:.0f}", f"{r['Avg hold days'] / 30.44:.1f}",
                f"{r['Avg trade %']:.1f}", f"{r['Median trade %']:.1f}"])
story += [KeepTogether([Paragraph("Trade duration and gain", H2),
          Paragraph(f"Fixed-target trades last weeks to months; no-target trades run for years. The no-target "
                    f"average gain of {nt['Avg trade %']:.0f}% comes from a handful of multi-year winners: its "
                    f"median trade loses {-nt['Median trade %']:.1f}%.", P),
          table(dur, [32 * mm, 16 * mm, 24 * mm, 26 * mm, 26 * mm, 22 * mm, 26 * mm]),
          Paragraph("Trades taken by the portfolio only. Trade % = net return per trade after costs. Hold = "
                    "calendar days from entry to exit; open trades counted to 13 Nov 2026.", SM)]),
          Paragraph("What else the study shows", H2)]
pts = [
    f"<b>Slots are the binding limit, not cash.</b> No entry was ever reduced for lack of cash, while "
    f"{int(tg['Signals skipped'].min()):,}–{int(nt['Signals skipped']):,} signals were skipped because "
    f"all 4 slots were taken.",
    f"<b>No-target trades block the slots for years.</b> It took only {int(nt['Trades taken'])} trades in "
    f"27 years; {_lg.symbol.replace('.NS', '')} was held from {_lg.entry_date:%b %Y} to {_lg.exit_date:%b %Y}. Its {nt['CAGR %']:.1f}% CAGR came with a "
    f"{nt['Max DD %']:.0f}% drawdown ({_pk:%b %Y} to {_tr:%b %Y}), as large open gains in {', '.join(_open)} "
    f"were given back in the crash.",
    f"<b>Losses can exceed 2%.</b> Gap-downs below the stop plus costs made the worst trade lose "
    f"{-s['Worst trade % of capital'].min():.1f}% of capital (Rs {-s['Worst trade (Rs)'].min():,.0f}).",
    "<b>Risk does not grow with the account.</b> Risk stays Rs 2,000 even after equity rises, so "
    "deployment on new trades falls further as the account grows. Sizing on 2% of current equity would fix this.",
    "<b>Survivorship bias:</b> today's NIFTY 500 members only, so returns are optimistic.",
]
story += [Paragraph(x, B, bulletText="•") for x in pts]
story += [Paragraph("Ways to use more of the capital", H2)]
ideas = [
    f"<b>The 8% risk cap itself limits deployment.</b> Total open risk = deployed capital x stop distance, "
    f"so with a {med_sd:.1f}% median stop, 8% of risk can never hold more than about "
    f"{8 / med_sd * 100:.0f}% of capital, whatever the slot count. Deploying all Rs 1,00,000 at this "
    f"stop distance means accepting about {med_sd:.0f}% total open risk (for example 9 slots at 2%).",
    "<b>Tighter stop:</b> a weekly candle low or a fixed 8–10% stop raises position size; it must be "
    "backtested, since it will also stop out more often.",
    "<b>Park idle cash</b> in a liquid fund or NIFTY ETF (e.g. NIFTYBEES) and redeem when a signal comes.",
]
story += [Paragraph(x, B, bulletText="•") for x in ideas]
story += [Paragraph("How to reproduce", H2),
          Paragraph("<font face='Courier' size='8'>python examples/position_sizing_study.py --capital 100000 "
                    "--risk 2 --max-pos 4<br/>python reports/position_sizing_report.py</font>", P),
          Paragraph("Code: lib/portfolio.py (shared-capital simulator), lib/ema61.py (signals and exits). "
                    "For research and education only; not investment advice.", SM)]

_i = next(i for i, f in enumerate(story) if isinstance(f, Paragraph) and f.text == "What else the study shows")
story[_i:_i] = duration_section.flowables("Candle low", H2, P, SM, table, mm)


def footer(c, d):
    c.setFont("Helvetica", 7.5); c.setFillColor(colors.HexColor(GREY))
    c.drawString(18 * mm, 10 * mm, "EMA61 breakout – position sizing and capital deployment")
    c.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {d.page}")


SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                  bottomMargin=16 * mm, title="EMA61 Breakout: Position Sizing").build(
    story, onFirstPage=footer, onLaterPages=footer)
for c in charts:
    c.unlink()
print(OUT)
