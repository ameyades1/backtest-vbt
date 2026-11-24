"""Weekly Supertrend exit study on S63387f09 -> results/studies/stexit/report.pdf
A: exit only when the weekly Supertrend turns bullish -> bearish after entry. B: no entry unless the last completed
week's Supertrend is bullish. AB: both (identical to B: if bullish at entry, any later bearish week is a turn).
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
from lib import ids, portfolio

OUT = ROOT / "results" / "studies" / "stexit"
OUT.mkdir(parents=True, exist_ok=True)
IDS = ids.by_name()
RUNS = [("S63387f09 (yours): exit on any bearish week", "hold/T25_r025"),
        ("A: exit only on a turn to bearish", "stexit/A_flip"),
        ("B: enter only while weekly Supertrend is bullish", "stexit/B_wst"),
        ("A + B", "stexit/AB"),
        ("A + 20% cap at entry", "stexit/A_flip_capentry")]
WIN = [(2000, 2004), (2005, 2009), (2010, 2014), (2015, 2019), (2020, 2026)]


def load(n):
    d = ROOT / "results" / n / "nifty500_pit"
    s = pd.read_csv(d / "summary.csv", index_col=0).iloc[0]
    e = pd.read_csv(d / "equity.csv", index_col=0, parse_dates=True).iloc[:, 0].dropna()
    return s, e, portfolio.trades(pd.read_csv(d / "fills_none.csv"))


def cg(e, a, b):
    x = e[f"{a}-01-01":f"{b}-12-31"]
    return ((x.iloc[-1] / x.iloc[0]) ** (365.25 / (x.index[-1] - x.index[0]).days) - 1) * 100


res = [["ID", "Variant", "CAGR", "Max DD", "DD dates", "Trades", "Win %", "Med hold", "Deployed"]]
wf = [["ID"] + [f"{a}–{str(b)[-2:]}" for a, b in WIN]]
top = [["ID", "Trades", "Top-10 trades' share of P&L", "Trades held > 1 year", "Their share of P&L"]]
EQ = {}
for lab, n in RUNS:
    s, e, t = load(n)
    EQ[lab] = e
    dd = e / e.cummax() - 1; tr = dd.idxmin(); pk = e[:tr].idxmax()
    sid = ids.short(IDS[n])
    res.append([sid, lab, f"{s['CAGR %']:.1f}%", f"{s['Max DD %']:.1f}%", f"{pk:%b %Y} – {tr:%b %Y}", int(s["Trades taken"]),
                f"{s['Win %']:.0f}%", f"{s['Median hold days']:.0f} d", f"{s['Avg deployed %']:.0f}%"])
    wf.append([sid] + [f"{cg(e, a, b):.1f}" for a, b in WIN])
    held = (t.exit_date.fillna(e.index[-1]) - t.entry_date).dt.days
    p = t.pnl
    top.append([sid, len(t), f"{p.nlargest(10).sum() / p.sum() * 100:.0f}%", int((held > 365).sum()),
                f"{p[held > 365].sum() / p.sum() * 100:.0f}%"])

ss = getSampleStyleSheet(); DARK, GREY = "#0f172a", "#64748b"
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=17, leading=21, alignment=0, textColor=colors.HexColor(DARK))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12.5, textColor=colors.HexColor(DARK), spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("P", parent=ss["Normal"], fontSize=9.2, leading=13, spaceAfter=4)
BL = ParagraphStyle("BL", parent=P, leftIndent=10, spaceAfter=2)
SM = ParagraphStyle("SM", parent=P, fontSize=7.8, leading=10, textColor=colors.HexColor(GREY))
bl = lambda xs: [Paragraph(x, BL, bulletText="•") for x in xs]


def table(rows, widths, fs=7.4):
    tb = Table(rows, colWidths=widths, repeatRows=1)
    tb.setStyle(TableStyle([("FONT", (0, 0), (-1, 0), "Helvetica-Bold", fs), ("FONT", (0, 1), (-1, -1), "Helvetica", fs),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(DARK)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    return tb


fig, ax = plt.subplots(figsize=(7.4, 3.2))
for lab, e in [x for i, x in enumerate(EQ.items()) if i in (0, 1, 4)]:
    ax.plot(e / e.iloc[0], lw=1, label=lab)
ax.set_yscale("log"); ax.grid(alpha=.3); ax.legend(fontsize=7); ax.set_title("Growth of 1 (log)", fontsize=9)
fig.tight_layout(); fig.savefig(OUT / "equity.png", dpi=160); plt.close(fig)
import json
notes = json.load(open(OUT / "notes.json"))
story = [Paragraph("Weekly Supertrend exit on S63387f09: exit on a turn, or enter only when bullish", H1),
         Paragraph("Point-in-time NIFTY 500, 1% risk, costs included; everything else as S63387f09. In S63387f09 a third "
                   "of trades were bought while the weekly Supertrend was already bearish and sold after one week.", SM),
         Paragraph("Verdict", H2)] + bl(notes["verdict"])
story += [Paragraph("Results", H2), table(res, [16 * mm, 58 * mm, 13 * mm, 14 * mm, 28 * mm, 13 * mm, 12 * mm, 15 * mm, 15 * mm]),
          Paragraph("Walk-forward: CAGR within each window", H2), table(wf, [20 * mm] + [24 * mm] * 5),
          Paragraph("Where the profit comes from", H2), table(top, [20 * mm, 18 * mm, 45 * mm, 35 * mm, 35 * mm]),
          Image(str(OUT / "equity.png"), width=180 * mm, height=78 * mm)]
story += ids.pdf_section([n for _, n in RUNS], H2)
SimpleDocTemplate(str(OUT / "report.pdf"), pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm,
                  bottomMargin=12 * mm, title="Weekly Supertrend exit").build(story)
print("wrote", OUT / "report.pdf")
