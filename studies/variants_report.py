"""Variations of your choice S44984096 -> results/studies/variants/report.pdf
Risk x slots grid, idle-cash interest, Zerodha costs, liquidity floor, Supertrend exit settings, same-day ranking.
Point-in-time NIFTY 500 from 2000; everything else as S44984096. Verdict bullets: results/studies/variants/notes.json.
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
import lib.pdffont  # noqa: F401  (DejaVu glyphs for ₹ and −)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image, PageBreak, KeepTogether
from lib import ids, metrics

OUT = ROOT / "results" / "studies" / "variants"
BASE = "stexit/A_flip_capentry"
IDS = ids.by_name()
J = json.load(open(OUT / "jobs.json"))
WIN = [(2000, 2004), (2005, 2009), (2010, 2014), (2015, 2019), (2020, 2026)]
GROUPS = {"1-grid": "1. Risk per trade × number of slots", "2-cash": "2. Idle cash: liquid fund or nothing",
          "3-costs": "3. Broker costs: Sharekhan or Zerodha", "4-liquidity": "4. Liquidity floor",
          "5-supertrend": "5. Supertrend settings for the exit", "6-ranking": "6. Which same-day signal gets the slot",
          "7-neighbours": "7. Neighbouring settings (robustness)"}


def load(n):
    d = ROOT / "results" / n / "nifty500_pit"
    s = pd.read_csv(d / "summary.csv", index_col=0).iloc[0]
    e = pd.read_csv(d / "equity.csv", index_col=0, parse_dates=True).iloc[:, 0].dropna()
    m = metrics.compute(pd.read_csv(d / "fills_none.csv"), s, "2000-01-01")
    wf = []
    for a, b in WIN:
        x = e[f"{a}-01-01":f"{b}-12-31"]
        wf.append(((x.iloc[-1] / x.iloc[0]) ** (365.25 / (x.index[-1] - x.index[0]).days) - 1) * 100)
    y = e.resample("YE").last(); y = pd.concat([pd.Series([e.iloc[0]], index=[e.index[0]]), y]).pct_change().dropna() * 100
    dd = e / e.cummax() - 1
    uw = (dd < 0).astype(int); runs = uw.groupby((uw == 0).cumsum()).sum()
    return {"s": s, "e": e, "m": m, "wf": wf, "worst_year": y.min(), "uw_days": int(runs.max()),
            "final": s["Final equity (Rs)"]}


R = {BASE: load(BASE)}
for j in J:
    R[j["name"]] = load(j["name"])
sid = lambda n: ids.short(IDS[n])

ss = getSampleStyleSheet(); DARK, GREY, AMBER = "#0f172a", "#64748b", "#b45309"
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=17, leading=21, alignment=0, textColor=colors.HexColor(DARK))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12.5, textColor=colors.HexColor(AMBER), spaceBefore=9, spaceAfter=3)
P = ParagraphStyle("P", parent=ss["Normal"], fontSize=9, leading=12.5, spaceAfter=3)
BL = ParagraphStyle("BL", parent=P, leftIndent=10, spaceAfter=2)
SM = ParagraphStyle("SM", parent=P, fontSize=7.6, leading=9.8, textColor=colors.HexColor(GREY))
bl = lambda xs: [Paragraph(x, BL, bulletText="•") for x in xs]


def table(rows, widths, bold_first=True, fs=7.2):
    t = Table(rows, colWidths=[w * mm for w in widths], repeatRows=1)
    st = [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", fs), ("FONT", (0, 1), (-1, -1), "Helvetica", fs),
          ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(DARK)),
          ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
          ("ALIGN", (2, 0), (-1, -1), "RIGHT"), ("TOPPADDING", (0, 0), (-1, -1), 1.8), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8)]
    if bold_first:
        st += [("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#fef3c7")), ("FONT", (0, 1), (-1, 1), "Helvetica-Bold", fs)]
    t.setStyle(TableStyle(st))
    return t


HEAD = ["ID", "Variant", "CAGR", "Max DD", "CAGR/DD", "Worst yr", "Longest under water", "Trades", "Win %",
        "Exp. R", "Loss streak", "Final (₹1 L start)"]
W = [16, 50, 12, 13, 13, 13, 18, 12, 11, 11, 12, 20]


def row(n, label):
    r = R[n]; m = r["m"]; s = r["s"]
    return [sid(n), label, f"{s['CAGR %']:.1f}%", f"{s['Max DD %']:.1f}%", f"{m['mar']:.2f}", f"{r['worst_year']:.0f}%",
            f"{r['uw_days'] / 365.25:.1f} yrs", m["trades"], f"{m['win']:.0f}", f"{m['exp_r']:+.2f}", m["streak"],
            f"₹{r['final'] / 1e5:,.1f} L"]


base_label = "S44984096 (your choice): 1% risk, 10 slots"
story = [Paragraph("Variations of S44984096: risk, slots, cash, costs, liquidity, exits, ranking", H1),
         Paragraph(f"{len(J)} new strategies, each one change from your choice S44984096. Point-in-time NIFTY 500 from 2000, "
                   "costs included (Sharekhan unless stated), the drawdown rule and the 20% position cap (at entry and at "
                   "month end) as in S44984096. The first row of every table (amber) is S44984096 itself.", SM),
         Paragraph("Verdict", H2)] + bl(json.load(open(OUT / "notes.json"))["verdict"])

# grid heatmaps
g = [j for j in J if j["group"] == "1-grid"]
risks, slots = [0.75, 1.0, 1.5, 2.0], [5, 7, 10]


def cell(r, k, key):
    n = BASE if (r, k) == (1.0, 10) else f"variants/r{r:g}_s{k}".replace(".", "p")
    s = R[n]["s"]
    return s["CAGR %"] if key == "cagr" else s["Max DD %"] if key == "dd" else s["CAGR %"] / -s["Max DD %"]


fig, axs = plt.subplots(1, 3, figsize=(7.6, 2.5))
for ax, (key, title, cmap) in zip(axs, [("cagr", "CAGR %", "Greens"), ("dd", "Max drawdown %", "Reds_r"),
                                         ("mar", "CAGR / drawdown", "Blues")]):
    M = np.array([[cell(r, k, key) for k in slots] for r in risks])
    ax.imshow(M, cmap=cmap, aspect="auto")
    for i in range(len(risks)):
        for jx in range(len(slots)):
            ax.text(jx, i, f"{M[i, jx]:.2f}" if key == "mar" else f"{M[i, jx]:.1f}", ha="center", va="center", fontsize=7,
                    fontweight="bold" if (risks[i], slots[jx]) == (1.0, 10) else "normal")
    ax.set_xticks(range(3), [f"{k} slots" for k in slots], fontsize=7); ax.set_yticks(range(4), [f"{r:g}%" for r in risks], fontsize=7)
    ax.set_title(title, fontsize=8)
fig.tight_layout(); fig.savefig(OUT / "grid.png", dpi=170); plt.close(fig)

story += [PageBreak(), Paragraph(GROUPS["1-grid"], H2),
          Image(str(OUT / "grid.png"), width=186 * mm, height=61 * mm),
          Paragraph("Rows: risk per trade. Columns: maximum open positions. Bold: S44984096.", SM),
          table([HEAD, row(BASE, base_label)] + [row(j["name"], j["desc"]) for j in g], W)]
for grp in ["2-cash", "3-costs", "4-liquidity", "5-supertrend", "6-ranking", "7-neighbours"]:
    js = [j for j in J if j["group"] == grp]
    story += [KeepTogether([Paragraph(GROUPS[grp], H2),
                            table([HEAD, row(BASE, base_label)] + [row(j["name"], j["desc"]) for j in js], W)])]

# random-pick check (studies/skipped.py: 200 runs each with random choice among same-day signals)
RP = ROOT / "results" / "studies" / "skipped" / "random.csv"
TAGS = {"E": BASE, "G": "variants/r1_s7", "I": "variants/r1_s6", "J": "variants/r1_s8", "H": "variants/r1p5_s7",
        "K": "variants/r1p5_s6", "L": "variants/r1p5_s8", "T": "variants/st14_3", "M": "variants/st12_3",
        "N": "variants/st14_2p5"}
if RP.exists():
    rnd = pd.read_csv(RP); be = rnd[rnd.tag == "E"]
    rr = [["ID", "Variant", "Actual", "Random median CAGR", "5th–95th", "Actual pct", "Median DD", "DD 5th–95th",
           "Median CAGR/DD", "Beats S44984096 (pairs)"]]
    for t, n in TAGS.items():
        x = rnd[rnd.tag == t]
        if len(x) < 150:
            continue
        a = R[n]["s"]["CAGR %"]
        lab = base_label if n == BASE else next(j["desc"] for j in J if j["name"] == n)
        rr.append([sid(n), lab, f"{a:.1f}%", f"{x.CAGR.median():.1f}%", f"{x.CAGR.quantile(.05):.1f}–{x.CAGR.quantile(.95):.1f}",
                   f"{(x.CAGR < a).mean() * 100:.0f}", f"{x.DD.median():.1f}%", f"{x.DD.quantile(.05):.0f} to {x.DD.quantile(.95):.0f}",
                   f"{(x.CAGR / -x.DD).median():.2f}",
                   "–" if t == "E" else f"{(x.CAGR.values[:, None] > be.CAGR.values[None, :]).mean() * 100:.0f}%"])
    story += [PageBreak(), Paragraph("8. Random-pick check: is the edge luck?", H2),
              Paragraph("Each strategy rerun 200 times choosing at random among signals that fill on the same day (instead "
                        "of tightest stop first). A real improvement shifts the whole distribution, not just the one actual "
                        "path. Last column: share of (variant run, S44984096 run) pairs where the variant has the higher CAGR.", SM),
              table(rr, [16, 46, 13, 18, 18, 12, 15, 18, 15, 19])]
    fig, ax = plt.subplots(figsize=(7.6, 3.0))
    data_ = [rnd[rnd.tag == t].CAGR for t in TAGS if (rnd.tag == t).sum() >= 150]
    labs = [sid(TAGS[t]) for t in TAGS if (rnd.tag == t).sum() >= 150]
    ax.boxplot(data_, tick_labels=labs, showfliers=False); ax.tick_params(labelsize=6.5); ax.grid(alpha=.3)
    ax.set_ylabel("CAGR % (200 random-pick runs)", fontsize=7.5)
    fig.tight_layout(); fig.savefig(OUT / "random.png", dpi=170); plt.close(fig)
    story.append(Image(str(OUT / "random.png"), width=186 * mm, height=73 * mm))

# walk-forward
wf = [["ID", "Variant"] + [f"{a}–{str(b)[-2:]}" for a, b in WIN]]
for n, lab in [(BASE, base_label)] + [(j["name"], j["desc"]) for j in J]:
    wf.append([sid(n), lab] + [f"{x:.1f}" for x in R[n]["wf"]])
story += [PageBreak(), Paragraph("Walk-forward: CAGR within each period", H2), table(wf, [16, 74] + [19] * 5),
          Paragraph("Each column is the CAGR inside that window of the same equity curve. A variant that wins only in one "
                    "window is fragile.", SM)]

# equity chart
pick = [(BASE, "S44984096 (1%, 10 slots)"), ("variants/r2_s5", "2% risk, 5 slots"), ("variants/r1p5_s7", "1.5% risk, 7 slots"),
        ("variants/zerodha", "Zerodha costs"), ("variants/cash0", "No interest on idle cash")]
fig, ax = plt.subplots(figsize=(7.6, 3.2))
for n, lab in pick:
    e = R[n]["e"]; ax.plot(e / e.iloc[0], lw=1.1 if n != BASE else 1.8, label=f"{sid(n)} {lab}")
ax.set_yscale("log"); ax.grid(alpha=.3); ax.legend(fontsize=6.5); ax.set_title("Growth of ₹1 (log)", fontsize=8.5)
fig.tight_layout(); fig.savefig(OUT / "equity.png", dpi=170); plt.close(fig)
story += [Image(str(OUT / "equity.png"), width=186 * mm, height=78 * mm),
          Paragraph("Columns: Worst yr = worst calendar year. Longest under water = longest time below a previous equity "
                    "high. Exp. R = average net profit per trade in units of initial risk. Loss streak = most losing "
                    "trades in a row. Final = ending equity from ₹1 lakh in Jan 2000.", SM)]
story += ids.pdf_section([BASE] + [j["name"] for j in J], H2)
SimpleDocTemplate(str(OUT / "report.pdf"), pagesize=A4, leftMargin=10 * mm, rightMargin=10 * mm, topMargin=11 * mm,
                  bottomMargin=11 * mm, title="Variations of S44984096").build(story)
print("wrote", OUT / "report.pdf")
for n, lab in [(BASE, "base")] + [(j["name"], j["desc"]) for j in J]:
    r = R[n]; print(f"{sid(n)} {lab[:60]:60} {r['s']['CAGR %']:5.1f} {r['s']['Max DD %']:6.1f} mar {r['m']['mar']:.2f} "
                    f"wy {r['worst_year']:.0f} uw {r['uw_days'] / 365.25:.1f} tr {r['m']['trades']} wf {[round(v, 1) for v in r['wf']]}")
