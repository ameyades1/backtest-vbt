"""Report for the CAGR-18 study -> results/studies/cagr18/report.pdf (+ all_runs.csv).

Reads every job in results/studies/cagr18/jobs_all.json. In-sample = 2000-2018, hold-out = 2019 onwards,
walk-forward windows are slices of each run's own equity curve. "Without top 10" removes the 10 most
profitable trades' rupee P&L from the final equity. Survivorship yardstick: equal weight in every current
constituent of the universe, rebalanced daily, no costs.
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "studies"))
from lib import portfolio
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image, PageBreak
from lib import ids

OUT = ROOT / "results" / "studies" / "cagr18"
JOBS = json.load(open(OUT / "jobs_all.json"))
IDS = ids.by_name()
MAIN = "stochrsi_pullback/monthly_prev_week_stop"
ST = "stochrsi_pullback/monthly_prev_week_stop_nifty200_exit_supertrend"
UNIS = ["NIFTY500", "NIFTY50", "NIFTY100", "MIDCAP150", "SMALLCAP250"]
WIN = [("2000", "2004"), ("2005", "2009"), ("2010", "2014"), ("2015", "2019"), ("2020", "2026")]
GREY, DARK = "#64748b", "#0f172a"


def cagr(e):
    e = e.dropna()
    if len(e) < 2 or e.iloc[0] <= 0:
        return np.nan
    return ((e.iloc[-1] / e.iloc[0]) ** (365.25 / max((e.index[-1] - e.index[0]).days, 1)) - 1) * 100


def mdd(e):
    e = e.dropna()
    return ((e / e.cummax()) - 1).min() * 100 if len(e) else np.nan


def short(n):
    return ids.short(IDS[n]) if n in IDS else ""


def label(n):
    if n.startswith("rotation/"):
        return n
    base = "main" if n.startswith(MAIN + "_c18") else "st" if n.startswith(ST + "_c18") else n
    return f"{base}: {n.split('_c18_')[-1]}" if "_c18_" in n else n


EQ = {}


def run_row(name, uni):
    d = ROOT / "results" / name / uni.lower()
    if not (d / "summary.csv").exists():
        return None
    sm = pd.read_csv(d / "summary.csv", index_col=0)
    ex = sm.index[0]
    r = sm.loc[ex]
    e = pd.read_csv(d / "equity.csv", index_col=0, parse_dates=True)[ex].dropna()
    EQ[(name, uni)] = e
    f = portfolio.read_fills(sorted(d.glob("fills_*.csv"))[0])
    pnl = np.sort((f.proceeds - f.cost).to_numpy())[::-1]
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    cap = e.iloc[0]
    cg = lambda tot: ((cap + tot) / cap) ** (1 / yrs) * 100 - 100 if cap + tot > 0 else -100.0
    ins, out = e[:"2018-12-31"], e["2019-01-01":]
    row = {"name": name, "label": label(name), "id": short(name), "universe": uni, "block": "",
           "CAGR": r["CAGR %"], "DD": r["Max DD %"], "Trades": int(r["Trades taken"]), "Win": r["Win %"],
           "Deployed": r["Avg deployed %"], "CAGR_in": cagr(ins), "DD_in": mdd(ins), "CAGR_out": cagr(out),
           "DD_out": mdd(out), "noTop10": cg(pnl.sum() - pnl[:10].sum())}
    for a, z in WIN:
        row[f"WF {a}"] = cagr(e[f"{a}-01-01":f"{z}-12-31"])
    return row


rows = []
for j in JOBS:
    r = run_row(j["name"], j["universe"])
    if r:
        r["block"] = j["phase"]
        rows.append(r)
ALL = pd.DataFrame(rows).drop_duplicates(["name", "universe"])
ALL.to_csv(OUT / "all_runs.csv", index=False)
N5 = ALL[ALL.universe == "NIFTY500"].set_index("name")

# survivorship yardstick: equal weight of current constituents
import run_strategy as R
EW = {}
for u in ["NIFTY50", "NIFTY100", "NIFTY200", "NIFTY500", "MIDCAP150", "SMALLCAP250"]:
    cl, _ = R.load_dailies(u)
    rt = cl.pct_change(fill_method=None).clip(-0.5, 0.5)
    rt = rt["2000-01-01":].mean(axis=1).fillna(0)
    EW[u] = 100_000 * (1 + rt).cumprod()

# pass / fail
def verdict(name):
    sub = ALL[ALL.name == name].set_index("universe")
    n15 = int((sub.CAGR >= 15).sum())
    r = sub.loc["NIFTY500"] if "NIFTY500" in sub.index else sub.iloc[0]
    ok = n15 >= 2 and r.DD >= -30 and r.noTop10 >= 8
    return n15, len(sub), ok


# ---------------- PDF ----------------
ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=17, leading=21, alignment=0, textColor=colors.HexColor(DARK))
SUB = ParagraphStyle("SUB", parent=ss["Normal"], fontSize=9, textColor=colors.HexColor(GREY))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12.5, textColor=colors.HexColor(DARK), spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("P", parent=ss["Normal"], fontSize=9.2, leading=13, spaceAfter=4)
BL = ParagraphStyle("BL", parent=P, leftIndent=10, spaceAfter=2)
SM = ParagraphStyle("SM", parent=P, fontSize=7.8, leading=10, textColor=colors.HexColor(GREY))
TC = ParagraphStyle("TC", parent=SM, fontSize=6.6, leading=8, textColor=colors.HexColor(DARK))
bl = lambda xs: [Paragraph(x, BL, bulletText="•") for x in xs]
f1 = lambda v, f="{:.1f}": "–" if v is None or (isinstance(v, float) and np.isnan(v)) else f.format(v)


def table(rows, widths, fs=6.6):
    rows = [[Paragraph(str(c), TC) if (i > 0 and j == 1 and isinstance(c, str) and len(c) > 30) else c
             for j, c in enumerate(r)] for i, r in enumerate(rows)]
    tb = Table(rows, colWidths=widths, repeatRows=1)
    tb.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", fs), ("FONT", (0, 1), (-1, -1), "Helvetica", fs),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(DARK)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6)]))
    return tb


HDR = ["ID", "Variant", "CAGR", "Max DD", "CAGR/DD", "Trades", "Deployed", "In CAGR/DD", "Out CAGR/DD", "w/o top 10", "Δ CAGR"]
W = [15 * mm, 56 * mm, 11 * mm, 12 * mm, 13 * mm, 11 * mm, 13 * mm, 17 * mm, 17 * mm, 14 * mm, 12 * mm]


def line(r, base_cagr=None):
    return [r["id"], r["label"], f1(r["CAGR"]), f1(r["DD"], "{:.0f}"), f1(r["CAGR"] / -r["DD"] if r["DD"] < 0 else np.nan, "{:.2f}"),
            int(r["Trades"]), f1(r["Deployed"], "{:.0f}%"), f"{f1(r['CAGR_in'])} / {f1(r['DD_in'], '{:.0f}')}",
            f"{f1(r['CAGR_out'])} / {f1(r['DD_out'], '{:.0f}')}", f1(r["noTop10"]),
            "" if base_cagr is None else f"{r['CAGR'] - base_cagr:+.1f}"]


def block_table(prefix):
    sub = N5[N5.block.str.startswith(prefix)]
    out = [HDR]
    for n, r in sub.sort_values("CAGR", ascending=False).iterrows():
        b = MAIN if n.startswith(MAIN + "_c18") else ST
        bc = N5.loc[f"{b}_c18_base", "CAGR"] if f"{b}_c18_base" in N5.index else None
        out.append(line({**r, "name": n}, bc))
    return table(out, W)


story = []
story += [Paragraph("CAGR 18%: what moves the needle", H1),
          Paragraph("74 variants and a momentum-rotation engine; NIFTY 500 (current constituents), 2000 – Nov 2026, "
                    "costs and 0.1% slippage included. In-sample 2000-18, hold-out 2019+.", SUB)]
NOTES = json.load(open(OUT / "notes.json")) if (OUT / "notes.json").exists() else {}
if NOTES.get("verdict"):
    story += [Paragraph("Verdict", H2)] + bl(NOTES["verdict"])

# finalists
story.append(Paragraph("Finalists against the acceptance test", H2))
story.append(Paragraph("Pass = CAGR ≥ 15% on at least 2 universes, NIFTY 500 max drawdown no worse than −30%, and "
                       "CAGR ≥ 8% after removing the 10 best trades.", SM))
fin = sorted({j["name"] for j in JOBS if j["phase"] in ("S2-universe", "H-compound")} | {MAIN + "_c18_base", ST + "_c18_base"})
rot = sorted({j["name"] for j in JOBS if j["name"].startswith("rotation/")})
fr = [["ID", "Strategy"] + [u.replace("SMALLCAP", "SC").replace("MIDCAP", "MC") for u in UNIS] + ["w/o top 10", "Pass"]]
for n in fin:
    n15, nu, ok = verdict(n)
    cells = []
    for u in UNIS:
        x = ALL[(ALL.name == n) & (ALL.universe == u)]
        cells.append(f"{x.CAGR.iloc[0]:.1f} / {x.DD.iloc[0]:.0f}" if len(x) else "–")
    fr.append([short(n), label(n)] + cells + [f1(N5.loc[n, "noTop10"]) if n in N5.index else "–", "yes" if ok else "no"])
story.append(table(fr, [15 * mm, 50 * mm] + [19 * mm] * 5 + [14 * mm, 10 * mm]))
story.append(Paragraph("Cells: CAGR % / max drawdown %.", SM))

if NOTES.get("blocks"):
    story += [Paragraph("What each block did", H2)] + bl(NOTES["blocks"])

for prefix, title in [("A", "A. 2×ATR-style stop + Supertrend exit grid (on S3f9854aa)"), ("B", "B. More capital at work"),
                      ("C", "C. Exits: chandelier, partial, time stop"), ("D", "D. Selection: RS ranking, sectors, filters"),
                      ("E", "E. Regime sizing"), ("F-c", "F1. Second engine sharing the portfolio"),
                      ("G", "G. Stacked levers"), ("H", "H. Compounding: risk a % of current equity")]:
    story += [Paragraph(title + " — NIFTY 500", H2), block_table(prefix)]
story.append(Paragraph("Δ CAGR is against the same base with no fixed target (main = S7c315ace, st = S3f9854aa).", SM))

# walk-forward
story += [PageBreak(), Paragraph("Walk-forward: CAGR in each window (slices of the NIFTY 500 equity curve)", H2)]
wf = [["ID", "Strategy"] + [f"{a}–{z[-2:]}" for a, z in WIN]]
for n in fin:
    if n in N5.index:
        wf.append([short(n), label(n)] + [f1(N5.loc[n, f"WF {a}"]) for a, _ in WIN])
story.append(table(wf, [15 * mm, 70 * mm] + [17 * mm] * 5))

# rotation
story.append(Paragraph("F2. Momentum rotation against the survivorship yardstick", H2))
rr = [["ID", "Strategy", "Universe", "CAGR", "Max DD", "In CAGR", "Out CAGR", "w/o top 10", "EW yardstick", "Excess"]]
for n in rot:
    for u in ["NIFTY50", "NIFTY100", "NIFTY200", "NIFTY500"]:
        x = ALL[(ALL.name == n) & (ALL.universe == u)]
        if len(x):
            x = x.iloc[0]; ew = cagr(EW[u])
            rr.append([short(n), n.split("/")[1], u, f1(x.CAGR), f1(x.DD, "{:.0f}"), f1(x.CAGR_in), f1(x.CAGR_out),
                       f1(x.noTop10), f1(ew), f"{x.CAGR - ew:+.1f}"])
story.append(table(rr, [15 * mm, 40 * mm, 18 * mm, 12 * mm, 13 * mm, 13 * mm, 14 * mm, 15 * mm, 18 * mm, 13 * mm]))
yr = [["Universe", "EW CAGR", "EW Max DD"]] + [[u, f1(cagr(e)), f1(mdd(e), "{:.0f}")] for u, e in EW.items()]
story.append(Paragraph("Equal weight of today's constituents (no costs) — what simply owning the survivors earned:", SM))
story.append(table(yr, [30 * mm, 20 * mm, 20 * mm]))
if NOTES.get("rotation"):
    story += bl(NOTES["rotation"])

# chart
fig, ax = plt.subplots(figsize=(7.4, 3.4))
pick = [(MAIN + "_c18_base", "NIFTY500"), (ST + "_c18_base", "NIFTY500")] + [(n, "NIFTY500") for n in fin[:0]]
best = [ST + "_c18_stack_compound", MAIN + "_c18_stack_rs_compound"]
pick += [(n, "NIFTY500") for n in best if (n, "NIFTY500") not in pick] + [("rotation/momentum_top10", "NIFTY100")]
for n, u in pick:
    if (n, u) in EQ:
        ax.plot(EQ[(n, u)] / EQ[(n, u)].iloc[0], lw=1, label=f"{short(n)} {label(n)} ({u})")
ax.plot(EW["NIFTY500"] / 100_000, lw=1, ls="--", color="grey", label="EW NIFTY 500 survivors (no costs)")
ax.set_yscale("log"); ax.grid(alpha=.3); ax.legend(fontsize=6); ax.set_title("Growth of 1 (log)", fontsize=9)
fig.tight_layout(); fig.savefig(OUT / "equity.png", dpi=160); plt.close(fig)
story += [Paragraph("Equity curves", H2), Image(str(OUT / "equity.png"), width=180 * mm, height=83 * mm)]

if NOTES.get("risk"):
    story += [Paragraph("Risk manager's notes", H2)] + bl(NOTES["risk"])
story += ids.pdf_section(sorted(set(ALL.name)), H2)
SimpleDocTemplate(str(OUT / "report.pdf"), pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm,
                  bottomMargin=12 * mm, title="CAGR 18% study").build(story)
print("wrote", OUT / "report.pdf")
