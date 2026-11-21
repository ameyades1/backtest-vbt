"""Risk of ruin and 5-year outcomes for S63387f09 (your choice) -> results/studies/ruin/{report.pdf, ruin.json}.
Block bootstrap of monthly returns (12-month blocks, 20,000 x 20-year paths) and ₹10 lakh over every 5-year window.
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image
from lib import ids

OUT = ROOT / "results" / "studies" / "ruin"
OUT.mkdir(parents=True, exist_ok=True)
NAME = "hold/T25_r025"
D = ROOT / "results" / NAME / "nifty500_pit"
CAP = 10_00_000
e = pd.read_csv(D / "equity.csv", index_col=0, parse_dates=True).iloc[:, 0].dropna()
f = pd.read_csv(D / "fills_none.csv")
lak = lambda x: f"₹{x / 1e5:,.1f} L"

# ---- bootstrap ----
m = e.resample("ME").last().pct_change().dropna().values
rng = np.random.default_rng(1); N, H, B = 20000, 240, 12
dd, fin = np.empty(N), np.empty(N)
for i in range(N):
    st = rng.integers(0, len(m) - B, H // B)
    eq = np.cumprod(1 + np.concatenate([m[s:s + B] for s in st]))
    dd[i] = (eq / np.maximum.accumulate(np.r_[1, eq])[1:] - 1).min(); fin[i] = eq[-1]
ddrows = [["Worst drawdown in 20 years", "Probability"],
          [f"{np.median(dd) * 100:.0f}% or worse (median)", "50%"]] + \
         [[f"{t}% or worse", f"{(dd <= t / 100).mean() * 100:.1f}%"] for t in (-30, -40, -50, -60)] + \
         [["Lose money over 20 years", f"{(fin < 1).mean() * 100:.3f}%"]]
pnl = (f.proceeds - f.cost).values * f.side.values
streak = mx = 0
for p in pnl:
    streak = 0 if p > 0 else streak + 1; mx = max(mx, streak)
mret = pd.Series(m)
facts = ["Position cap 20%: a stock going to zero overnight costs at most about 20% of the account.",
         f"Worst month {mret.min() * 100:.1f}%; longest losing streak {mx} trades; backtest max drawdown "
         f"{((e / e.cummax()) - 1).min() * 100:.1f}%."]

# ---- ₹10 lakh over 5-year windows ----
def at(d):
    return e[e.index >= pd.Timestamp(d)].iloc[0], e[e.index >= pd.Timestamp(d)].index[0]
win = [["Period", "Start", "End value", "CAGR", "Worst DD in period"]]
for y in range(e.index[0].year + (e.index[0].month > 1), e.index[-1].year - 4):
    x = e[f"{y}-01-01":f"{y + 4}-12-31"]
    if x.index[-1].year < y + 4 or x.index[-1].month < 12:
        continue
    v = CAP * x.iloc[-1] / x.iloc[0]
    win.append([f"Jan {y} – Dec {y + 4}", lak(CAP), lak(v), f"{((v / CAP) ** (1 / 5) - 1) * 100:.1f}%",
                f"{((x / x.cummax()) - 1).min() * 100:.0f}%"])
# rolling any-day 5-year
n5 = 5 * 365
ends = e.reindex(e.index + pd.Timedelta(days=n5), method="ffill")
ends.index = e.index
roll = (ends.values / e.values)[e.index + pd.Timedelta(days=n5) <= e.index[-1]] * CAP
q = np.percentile(roll, [0, 10, 50, 90, 100])
rollrows = [["Any start day (" + f"{len(roll):,} windows)", "Value of ₹10 L after 5 years"]] + \
           [[l, lak(v)] for l, v in zip(["Worst", "10th percentile", "Median", "90th percentile", "Best"], q)] + \
           [["Windows ending below ₹10 L", f"{(roll < CAP).mean() * 100:.1f}%"]]
json.dump({"dd": ddrows, "win": win, "roll": rollrows, "facts": facts}, open(OUT / "ruin.json", "w"), indent=1, ensure_ascii=False)

# ---- PDF ----
ss = getSampleStyleSheet(); DARK, GREY = "#0f172a", "#64748b"
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=17, leading=21, alignment=0, textColor=colors.HexColor(DARK))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12.5, textColor=colors.HexColor(DARK), spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("P", parent=ss["Normal"], fontSize=9.2, leading=13, spaceAfter=4)
BL = ParagraphStyle("BL", parent=P, leftIndent=10, spaceAfter=2)
SUB = ParagraphStyle("SUB", parent=P, fontSize=9, textColor=colors.HexColor(GREY))
bl = lambda xs: [Paragraph(x, BL, bulletText="•") for x in xs]
def table(rows, widths):
    tb = Table(rows, colWidths=widths, repeatRows=1)
    tb.setStyle(TableStyle([("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8), ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#b45309")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fef3c7")]),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    return tb
fig, ax = plt.subplots(figsize=(7.4, 2.8))
ax.hist(dd * 100, bins=60, color="#b45309"); ax.set_xlabel("Worst drawdown over a simulated 20 years (%)")
ax.set_title("S63387f09: 20,000 resampled 20-year histories", fontsize=9); ax.grid(alpha=.3)
fig.tight_layout(); fig.savefig(OUT / "dd_hist.png", dpi=160); plt.close(fig)
story = [Paragraph("Risk of ruin and ₹10 lakh outcomes: S63387f09 (your choice)", H1),
         Paragraph("1% risk, long only, no hedges, point-in-time NIFTY 500, costs included. Monthly returns resampled in "
                   "12-month blocks.", SUB), Paragraph("Verdict", H2)] + bl([
    "<b>Going bust is effectively impossible if the rules are followed:</b> 1% risk per trade, 20% position cap, size "
    "halved at −10% and new trades paused at −15%, no leverage, shorts or options.",
    "<b>The real risk is a deep drawdown that makes you quit.</b> Expect −20% to −30% in a typical 20 years; −40% is "
    "rare but possible. Events outside 2000–26 (market shutdown, days of lower circuits, broker failure) are not in the "
    "data, so treat −35% to −40% as the stress case.",
    "<b>Never add leverage or margin to this system</b>; that is the one change that turns a drawdown into ruin."]) + bl(facts)
story += [Paragraph("Drawdown probabilities", H2), table(ddrows, [70 * mm, 30 * mm]),
          Image(str(OUT / "dd_hist.png"), width=180 * mm, height=68 * mm),
          Paragraph("₹10 lakh over each calendar 5-year period", H2), table(win, [45 * mm, 25 * mm, 28 * mm, 20 * mm, 32 * mm]),
          Paragraph("₹10 lakh over any 5-year window", H2), table(rollrows, [70 * mm, 45 * mm]),
          Paragraph("Backtest figures before tax; live results will be somewhat lower. Research only, not advice.", SUB)]
story += ids.pdf_section([NAME], H2)
SimpleDocTemplate(str(OUT / "report.pdf"), pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm,
                  bottomMargin=12 * mm, title="Risk of ruin").build(story)
print("wrote", OUT / "report.pdf")
