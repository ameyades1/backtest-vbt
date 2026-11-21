"""Entry-filter study on Sde394f26 -> results/studies/filter/report.pdf (+ summary.csv). Text: notes.json."""
import json, sys
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
from lib import ids

OUT = ROOT / "results" / "studies" / "filter"
IDS = ids.by_name()
BASE = "longshort/L_cap20_dd"
EPIS = [("2006", "2006-04-01", "2006-12-31"), ("2008", "2008-01-01", "2009-06-30"), ("2015–16", "2015-03-01", "2016-12-31"),
        ("2018–20", "2018-01-01", "2020-12-31"), ("2024–25", "2024-06-01", "2026-12-31")]
GROUPS = [("Sde394f26 (NIFTY 50 above its 200-day average)", ["base"]), ("1. NIFTY 500 index entry filter", ["1-index"]),
          ("NIFTY 50 controls", ["1-nifty50"]), ("2. Breadth (point-in-time members)", ["2-breadth"]),
          ("3. Combinations", ["3-combo"])]
J = json.load(open(OUT / "jobs1.json")) + json.load(open(OUT / "jobs2.json"))


def cg(e):
    return ((e.iloc[-1] / e.iloc[0]) ** (365.25 / (e.index[-1] - e.index[0]).days) - 1) * 100


def stats(n):
    d = ROOT / "results" / n / "nifty500_pit"
    r = pd.read_csv(d / "summary.csv", index_col=0).iloc[0]
    e = pd.read_csv(d / "equity.csv", index_col=0, parse_dates=True)[r.name].dropna()
    dd = e / e.cummax() - 1
    ins, oos = e[:"2014-12-31"], e["2014-12-31":]
    ddo = oos / oos.cummax() - 1
    return {"name": n, "CAGR": r["CAGR %"], "DD": r["Max DD %"], "trades": int(r["Trades taken"]),
            "IS CAGR": cg(ins), "IS DD": (ins / ins.cummax() - 1).min() * 100, "OOS CAGR": cg(oos),
            "OOS DD": ddo.min() * 100, **{k: dd[a:b].min() * 100 for k, a, b in EPIS}}, e


rows, curves, flat = [], {}, []
for title, phases in GROUPS:
    names = [BASE] if phases == ["base"] else [j["name"] for j in J if j["phase"] in phases]
    rows.append([title] + [""] * 12)
    for n in names:
        s, e = stats(n); curves[n] = e; flat.append(s)
        rows.append([ids.short(IDS[n]) if n in IDS else "", n.split("/")[-1], f"{s['CAGR']:.1f}", f"{s['DD']:.0f}",
                     f"{s['CAGR'] / -s['DD']:.2f}", f"{s['IS CAGR']:.1f}", f"{s['OOS CAGR']:.1f}", f"{s['OOS DD']:.0f}"]
                    + [f"{s[k]:.0f}" for k, _, _ in EPIS])
df = pd.DataFrame(flat); df.to_csv(OUT / "summary.csv", index=False)
# walk-forward: pick on 2000-14 (CAGR / DD), check 2015-26
cand = df[df.name != BASE].assign(score=lambda x: x["IS CAGR"] / -x["IS DD"]).sort_values("score", ascending=False)
b0 = df[df.name == BASE].iloc[0]
wf = [["Rank on 2000–14", "ID", "Variant", "2000–14 CAGR / DD", "2015–26 CAGR / DD", "vs Sde394f26 2015–26"]]
for i, r in enumerate(cand.head(5).itertuples(), 1):
    wf.append([i, ids.short(IDS[r.name]) if r.name in IDS else "", r.name.split("/")[-1],
               f"{r._5:.1f} / {r._6:.0f}", f"{r._7:.1f} / {r._8:.0f}", f"{r._7 - b0['OOS CAGR']:+.1f} pts"])
wf.append(["–", "Sde394f26", "L_cap20_dd", f"{b0['IS CAGR']:.1f} / {b0['IS DD']:.0f}",
           f"{b0['OOS CAGR']:.1f} / {b0['OOS DD']:.0f}", "–"])

ss = getSampleStyleSheet()
DARK, GREY = "#0f172a", "#64748b"
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=17, leading=21, alignment=0, textColor=colors.HexColor(DARK))
SUB = ParagraphStyle("SUB", parent=ss["Normal"], fontSize=9, textColor=colors.HexColor(GREY))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12.5, textColor=colors.HexColor(DARK), spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("P", parent=ss["Normal"], fontSize=9.2, leading=13, spaceAfter=4)
BL = ParagraphStyle("BL", parent=P, leftIndent=10, spaceAfter=2)
SM = ParagraphStyle("SM", parent=P, fontSize=7.8, leading=10, textColor=colors.HexColor(GREY))
bl = lambda xs: [Paragraph(x, BL, bulletText="•") for x in xs]
notes = json.load(open(OUT / "notes.json"))
hdr = ["ID", "Variant", "CAGR", "Max DD", "CAGR/DD", "2000–14 CAGR", "2015–26 CAGR", "2015–26 DD"] + [k for k, _, _ in EPIS]
tb = Table([hdr] + rows, colWidths=[15 * mm, 26 * mm, 11 * mm, 12 * mm, 13 * mm, 15 * mm, 15 * mm, 14 * mm] + [12.5 * mm] * 5,
           repeatRows=1)
st = [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 6.6), ("FONT", (0, 1), (-1, -1), "Helvetica", 6.8),
      ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(DARK)),
      ("ALIGN", (2, 0), (-1, -1), "RIGHT"), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
for i, r in enumerate(rows, 1):
    if not r[1]:
        st += [("SPAN", (0, i), (-1, i)), ("BACKGROUND", (0, i), (-1, i), colors.HexColor("#e2e8f0")),
               ("FONT", (0, i), (-1, i), "Helvetica-Bold", 7), ("ALIGN", (0, i), (-1, i), "LEFT")]
tb.setStyle(TableStyle(st))
wt = Table(wf, colWidths=[22 * mm, 16 * mm, 30 * mm, 32 * mm, 32 * mm, 34 * mm], repeatRows=1)
wt.setStyle(TableStyle([("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.2), ("FONT", (0, 1), (-1, -1), "Helvetica", 7.2),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(DARK)),
                        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
                        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
story = [Paragraph("Entry filters for Sde394f26: NIFTY 500 index and breadth", H1),
         Paragraph("Sde394f26 at 1% risk, long only, no hedges; point-in-time NIFTY 500 from 2000, costs included. Only the "
                   "entry filter or the sizing of new trades changes.", SUB), Paragraph("Verdict", H2)] + bl(notes["verdict"])
story += [Paragraph("Results", H2), tb,
          Paragraph("Episode columns: worst drawdown inside each window. 2000–14 / 2015–26: CAGR and drawdown inside each "
                    "half of the same equity curve.", SM)]
story += [Paragraph("Walk-forward: choose on 2000–14, check on 2015–26", H2), wt,
          Paragraph("Ranked by 2000–14 CAGR ÷ max drawdown, without looking at 2015–26.", SM)]
fig, ax = plt.subplots(figsize=(7.4, 3.0))
for n in notes.get("plot", []):
    e = curves[n]; ax.plot(e / e.iloc[0], lw=0.9, label=n.split("/")[-1])
ax.set_yscale("log"); ax.grid(alpha=.3); ax.legend(fontsize=7); ax.set_title("Growth of 1 (log)", fontsize=9)
fig.tight_layout(); fig.savefig(OUT / "equity.png", dpi=160); plt.close(fig)
story.append(Image(str(OUT / "equity.png"), width=180 * mm, height=73 * mm))
for k in ("findings", "method"):
    if k in notes:
        story += [Paragraph(notes[k]["title"], H2)] + bl(notes[k]["points"])
story += ids.pdf_section([BASE] + [j["name"] for j in J], H2)
SimpleDocTemplate(str(OUT / "report.pdf"), pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm,
                  bottomMargin=12 * mm, title="Entry filters for Sde394f26").build(story)
print("wrote", OUT / "report.pdf")
