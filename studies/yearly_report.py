"""Year-by-year table for your choice Sf5b94362 (stexit/A_flip) -> results/studies/yearly/report.pdf
₹10 lakh at the start of 2000 in the strategy vs ₹10 lakh in the index (NIFTY 50; BSE Sensex before 2008, as NIFTY's
Yahoo history starts Sept 2007). Index is price only: dividends (about 1-1.5% a year) not included.
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import lib.pdffont  # noqa: F401  (DejaVu glyphs for ₹ and −)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image
from lib import ids, portfolio, data

OUT = ROOT / "results" / "studies" / "yearly"
OUT.mkdir(parents=True, exist_ok=True)
NAME = "stexit/A_flip"
D = ROOT / "results" / NAME / "nifty500_pit"
e = pd.read_csv(D / "equity.csv", index_col=0, parse_dates=True).iloc[:, 0].dropna()
e = e / e.iloc[0] * 10                                    # ₹ lakh
t = portfolio.trades(pd.read_csv(D / "fills_none.csv"))
x = data.load(["^BSESN", "^NSEI"])["Close"]
nf = x["^NSEI"].dropna()
idx = pd.concat([x["^BSESN"].dropna()[:"2007-12-31"], nf["2008-01-01":]])
# chain: Sensex returns to end-2007, NIFTY returns after
r = idx.pct_change()
r.loc[nf["2008-01-01":].index[0]] = nf["2008-01-01":].iloc[0] / nf[:"2007-12-31"].iloc[-1] - 1
ix = (1 + r.fillna(0)).cumprod().reindex(e.index, method="ffill")
ix = ix / ix.iloc[0] * 10


def fmt(v):
    return f"₹{v / 100:,.2f} Cr" if v >= 100 else f"₹{v:,.1f} L"


rows = [["Year", "Start", "End", "Return", "Worst drop", "Index return", "₹10 L in index", "Trades (won)"]]
bad = 0
for y, g in e.groupby(e.index.year):
    s = e[e.index < g.index[0]]; s = s.iloc[-1] if len(s) else g.iloc[0]
    gi = ix[g.index]; si = ix[ix.index < g.index[0]]; si = si.iloc[-1] if len(si) else gi.iloc[0]
    c = t[t.exit_date.dt.year == y]
    ret = (g.iloc[-1] / s - 1) * 100; bad += ret < 0
    rows.append([str(y) + (" (to " + f"{g.index[-1]:%d %b})" if y == e.index[-1].year else ""), fmt(s), fmt(g.iloc[-1]),
                 f"{ret:+.1f}%", f"{(g / g.cummax() - 1).min() * 100:.0f}%", f"{(gi.iloc[-1] / si - 1) * 100:+.0f}%",
                 fmt(gi.iloc[-1]), f"{len(c)} ({(c.pnl > 0).sum()})"])
yrs = (e.index[-1] - e.index[0]).days / 365.25
cs, ci = ((e.iloc[-1] / 10) ** (1 / yrs) - 1) * 100, ((ix.iloc[-1] / 10) ** (1 / yrs) - 1) * 100
ddi = (ix / ix.cummax() - 1).min() * 100

ss = getSampleStyleSheet(); DARK, GREY = "#0f172a", "#64748b"
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=17, leading=21, alignment=0, textColor=colors.HexColor(DARK))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12.5, textColor=colors.HexColor(DARK), spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("P", parent=ss["Normal"], fontSize=9.2, leading=13, spaceAfter=4)
BL = ParagraphStyle("BL", parent=P, leftIndent=10, spaceAfter=2)
SM = ParagraphStyle("SM", parent=P, fontSize=7.8, leading=10, textColor=colors.HexColor(GREY))
bl = lambda xs: [Paragraph(v, BL, bulletText="•") for v in xs]
tb = Table(rows, colWidths=[26 * mm, 22 * mm, 22 * mm, 17 * mm, 19 * mm, 20 * mm, 26 * mm, 22 * mm], repeatRows=1)
st = [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.6), ("FONT", (0, 1), (-1, -1), "Helvetica", 7.6),
      ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#b45309")),
      ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fef3c7")]),
      ("ALIGN", (1, 0), (-1, -1), "RIGHT"), ("TOPPADDING", (0, 0), (-1, -1), 1.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6)]
st += [("TEXTCOLOR", (3, i), (3, i), colors.HexColor("#dc2626")) for i, r_ in enumerate(rows) if i and r_[3].startswith("-")]
tb.setStyle(TableStyle(st))
fig, ax = plt.subplots(figsize=(7.4, 3.0))
ax.plot(e, lw=1.2, color="#b45309", label="Sf5b94362"); ax.plot(ix, lw=1, color="#64748b", label="NIFTY 50 (Sensex before 2008)")
ax.set_yscale("log"); ax.yaxis.set_major_formatter(lambda v, _: f"₹{v:g} L"); ax.grid(alpha=.3); ax.legend(fontsize=7)
ax.set_title("₹10 lakh from Jan 2000 (log scale)", fontsize=9); fig.tight_layout(); fig.savefig(OUT / "equity.png", dpi=160); plt.close(fig)
story = [Paragraph("Year by year: Sf5b94362 (your choice) vs the index", H1),
         Paragraph("₹10 lakh at the start of 2000. Point-in-time NIFTY 500, 1% risk, costs included, before tax. Index: "
                   "NIFTY 50, BSE Sensex before 2008; price only, dividends (about 1–1.5% a year) not included.", SM),
         Paragraph("Summary", H2)] + bl([
    f"<b>Strategy: {fmt(e.iloc[-1])}</b> ({cs:.1f}% a year, worst drawdown {(e / e.cummax() - 1).min() * 100:.0f}%). "
    f"<b>Index: {fmt(ix.iloc[-1])}</b> ({ci:.1f}% a year, worst drawdown {ddi:.0f}%).",
    f"Losing years: {bad} of {len(rows) - 1}; the worst was 2008 (−21% against −52% for the index). The deepest drop, −28% "
    "in May–June 2006, was inside a winning year.",
    "The strategy lags sharp V-shaped recoveries (2003, 2009, 2019) because it waits for monthly pullback setups, and "
    "makes most of its money in a few strong years (2005, 2007, 2014, 2020–21, 2023).",
    "2000–02 are mostly liquid-fund interest: few usable stocks in the rebuilt index and the market filter was off."])
story += [Paragraph("Year by year", H2), tb,
          Paragraph("Worst drop: deepest fall from a peak within the year. Trades: closed in that year (winners).", SM),
          Image(str(OUT / "equity.png"), width=180 * mm, height=73 * mm)]
story += ids.pdf_section([NAME], H2)
SimpleDocTemplate(str(OUT / "report.pdf"), pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm,
                  bottomMargin=12 * mm, title="Year by year").build(story)
print("wrote", OUT / "report.pdf"); print("\n".join(" | ".join(r_) for r_ in rows)); print(cs, ci, ddi)
