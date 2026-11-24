"""Drawdown-cutting study on Sde394f26 -> results/studies/ddcut/report.pdf (+ summary.csv, gold blends).
Text verdicts come from results/studies/ddcut/notes.json."""
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

OUT = ROOT / "results" / "studies" / "ddcut"
IDS = ids.by_name()
BASE = "longshort/L_cap20_dd"
EPIS = [("2006", "2006-04-01", "2006-12-31"), ("2008", "2008-01-01", "2009-06-30"), ("2015–16", "2015-03-01", "2016-12-31"),
        ("2018–20", "2018-01-01", "2020-12-31"), ("2024–25", "2024-06-01", "2026-12-31")]
TESTS = [("Reference", [BASE, "longshort/LS_hedge50", "longshort/LS_hedge100", "longshort/LS_short_w_st10_2"]),
         ("1. NIFTY futures hedge, faster regime", None), ("2. Tighten or exit the longs", None),
         ("3. Bear-market stock shorts", None), ("5. Hedge + breadth sizing together", None)]
PH = {"1. NIFTY futures hedge, faster regime": "1-hedge", "2. Tighten or exit the longs": "2-tighten",
      "3. Bear-market stock shorts": "3-longshort",
      "5. Hedge + breadth sizing together": "5-combined"}
J = json.load(open(OUT / "jobs.json"))


def curve(n, u="nifty500_pit"):
    d = ROOT / "results" / n / u
    sm = pd.read_csv(d / "summary.csv", index_col=0)
    r = sm.iloc[0]
    e = pd.read_csv(d / "equity.csv", index_col=0, parse_dates=True)[r.name].dropna()
    return r, e


def stats(e):
    dd = e / e.cummax() - 1
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    cg = ((e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1) * 100
    uw, start, longest = dd < -1e-9, None, 0
    for d, v in uw.items():
        if v and start is None:
            start = d
        if not v and start is not None:
            longest, start = max(longest, (d - start).days), None
    if start is not None:
        longest = max(longest, (e.index[-1] - start).days)
    ep = [dd[a:b].min() * 100 for _, a, b in EPIS]
    return cg, dd.min() * 100, longest / 365.25, ep


def gold_inr():
    g = pd.read_csv(ROOT.parent / "data" / "gold_close.csv", index_col=0, parse_dates=True)
    spot = (g["GC=F"] * g["INR=X"]).dropna()
    etf = g["GOLDBEES.NS"].dropna()
    r = spot.pct_change()
    r = r - 0.005 / 252                                    # ~0.5%/yr fund costs on the spot series
    er = etf.pct_change()
    er = er[er.abs() < 0.2]                                # Yahoo has 1/100 bad ticks (Dec 2019): use spot there
    r.loc[er.index[er.index.isin(r.index)]] = er[er.index.isin(r.index)]   # actual Gold BeES from 2009
    return (1 + r.fillna(0)).cumprod()


def blend(e, g, w, freq="YE"):
    idx = e.index.intersection(g.index)
    e, g = e.reindex(idx), g.reindex(idx)
    re, rg = e.pct_change().fillna(0), g.pct_change().fillna(0)
    a, b, out = 1 - w, w, []
    reb = set(pd.Series(idx, index=idx).resample(freq).last())
    for d in idx:
        a *= 1 + re[d]; b *= 1 + rg[d]
        if d in reb:
            tot = a + b; turn = abs(a - (1 - w) * tot)
            tot -= turn * 0.002                             # 0.1% per side on the switched amount
            a, b = (1 - w) * tot, w * tot
        out.append(a + b)
    return pd.Series(out, index=idx)


rows, curves = [], {}
hdr = ["ID", "Variant", "CAGR", "Max DD", "CAGR/DD", "Longest under water (yrs)"] + [x[0] for x in EPIS]
for title, names in TESTS:
    names = names or [j["name"] for j in J if j["phase"] == PH[title]]
    rows.append([title] + [""] * (len(hdr) - 1))
    for n in names:
        try:
            r, e = curve(n)
        except FileNotFoundError:
            continue
        cg, md, uw, ep = stats(e)
        curves[n] = e
        rows.append([ids.short(IDS[n]) if n in IDS else "", n.split("/")[-1], f"{cg:.1f}", f"{md:.0f}",
                     f"{cg / -md:.2f}", f"{uw:.1f}"] + [f"{x:.0f}" for x in ep])
# test 4: gold
g = gold_inr()
e0 = curves[BASE]
rows.append(["4. Gold for part of the capital (from Dec 2003; rebalanced yearly)"] + [""] * (len(hdr) - 1))
gold_rows = []
e04 = e0["2003-12-01":]
C = "ddcut/C_hedge_i50_breadth"
for lab, src, w in [("Sde394f26", e04, 0.0), ("Sde394f26", e04, 0.1), ("Sde394f26", e04, 0.2), ("Sde394f26", e04, 0.3)] + \
        ([("C_hedge_i50_breadth", curves[C]["2003-12-01":], w) for w in (0.0, 0.2, 0.3)] if C in curves else []):
    b = blend(src, g, w) if w else src / src.iloc[0]
    cg, md, uw, ep = stats(b)
    curves[f"{lab} + gold {int(w * 100)}%"] = b
    gold_rows.append({"gold %": w * 100, "CAGR": cg, "Max DD": md})
    rows.append(["", f"{lab} {100 - w * 100:.0f}% + gold {w * 100:.0f}%", f"{cg:.1f}", f"{md:.0f}", f"{cg / -md:.2f}",
                 f"{uw:.1f}"] + [f"{x:.0f}" for x in ep])
cg, md, uw, ep = stats(g["2003-12-01":])
rows.append(["", "Gold alone (INR)", f"{cg:.1f}", f"{md:.0f}", f"{cg / -md:.2f}", f"{uw:.1f}"] + [f"{x:.0f}" for x in ep])
pd.DataFrame([r for r in rows if r[1]], columns=hdr).to_csv(OUT / "summary.csv", index=False)

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
tb = Table([hdr] + rows, colWidths=[15 * mm, 50 * mm, 11 * mm, 12 * mm, 14 * mm, 19 * mm] + [13 * mm] * 5, repeatRows=1)
st = [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 6.8), ("FONT", (0, 1), (-1, -1), "Helvetica", 6.8),
      ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(DARK)),
      ("ALIGN", (2, 0), (-1, -1), "RIGHT"), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
for i, r in enumerate(rows, 1):
    if not r[1]:
        st += [("SPAN", (0, i), (-1, i)), ("BACKGROUND", (0, i), (-1, i), colors.HexColor("#e2e8f0")),
               ("FONT", (0, i), (-1, i), "Helvetica-Bold", 7), ("ALIGN", (0, i), (-1, i), "LEFT")]
tb.setStyle(TableStyle(st))
story = [Paragraph("Cutting Sde394f26's drawdown", H1),
         Paragraph("Four ways to cut the −27% drawdown of Sde394f26 (1% risk, compounding, point-in-time NIFTY 500, "
                   "from 2000, costs included).", SUB), Paragraph("Verdict", H2)] + bl(notes["verdict"])
story += [Paragraph("Results", H2), tb,
          Paragraph("Episode columns: worst drawdown inside each window. Under water: longest stretch below a previous "
                    "equity peak. Gold rows start in Dec 2003 (INR gold price history), so their Sde394f26 row differs "
                    "from the full-period one.", SM)]
fig, ax = plt.subplots(figsize=(7.4, 3.0))
for k in notes.get("plot", []):
    if k in curves:
        e = curves[k]["2003-12-01":]
        ax.plot(e / e.cummax() - 1, lw=0.9, label=k.split("/")[-1])
ax.grid(alpha=.3); ax.legend(fontsize=6.5); ax.set_title("Drawdown from the previous peak", fontsize=9)
fig.tight_layout(); fig.savefig(OUT / "drawdown.png", dpi=160); plt.close(fig)
story.append(Image(str(OUT / "drawdown.png"), width=180 * mm, height=73 * mm))
for k in ("hedge", "tighten", "shorts", "gold", "method"):
    if k in notes:
        story += [Paragraph(notes[k]["title"], H2)] + bl(notes[k]["points"])
story += ids.pdf_section([BASE] + [j["name"] for j in J], H2)
SimpleDocTemplate(str(OUT / "report.pdf"), pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm,
                  bottomMargin=12 * mm, title="Cutting Sde394f26's drawdown").build(story)
print("wrote", OUT / "report.pdf")
