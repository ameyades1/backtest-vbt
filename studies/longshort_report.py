"""Report for the long/short study -> results/studies/longshort/report.pdf (+ all_runs.csv).
Crisis windows are measured on each run's equity curve: 2008 (Dec 2007 -> Dec 2008), 2018-20 mid/small-cap bear
(Aug 2018 -> Aug 2020), COVID crash (19 Feb -> 23 Mar 2020).
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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image, PageBreak
from lib import ids

OUT = ROOT / "results" / "studies" / "longshort"
JOBS = json.load(open(OUT / "jobs12.json")) + json.load(open(OUT / "jobs3.json"))
IDS = ids.by_name()
UNI5 = ["NIFTY500", "NIFTY50", "NIFTY100", "MIDCAP150", "SMALLCAP250"]
CRISIS = {"2008": ("2007-12-31", "2008-12-31"), "2018-20": ("2018-08-31", "2020-08-31"), "COVID": ("2020-02-19", "2020-03-23")}
sid = lambda n: ids.short(IDS[n]) if n in IDS else ""


def pct(e, a, b):
    x, y = e[:a], e[b:]
    return (y.iloc[0] / x.iloc[-1] - 1) * 100 if len(x) and len(y) else np.nan


rows, EQ = [], {}
for j in JOBS:
    d = ROOT / "results" / j["name"] / j["universe"].lower()
    s = pd.read_csv(d / "summary.csv", index_col=0).iloc[0]
    e = pd.read_csv(d / "equity.csv", index_col=0, parse_dates=True).iloc[:, 0].dropna()
    EQ[(j["name"], j["universe"])] = e
    r = {"name": j["name"], "short": j["name"].split("/")[1], "id": sid(j["name"]), "universe": j["universe"],
         "part": j["phase"], "CAGR": s["CAGR %"], "DD": s["Max DD %"], "Trades": int(s["Trades taken"]), "Win": s["Win %"],
         "CAGR_in": ((e[:"2018-12-31"].iloc[-1] / e.iloc[0]) ** (365.25 / (pd.Timestamp("2018-12-31") - e.index[0]).days) - 1) * 100,
         "CAGR_out": ((e.iloc[-1] / e[:"2018-12-31"].iloc[-1]) ** (365.25 / (e.index[-1] - pd.Timestamp("2018-12-31")).days) - 1) * 100}
    for k, (a, b) in CRISIS.items():
        r[k] = pct(e, a, b)
    rows.append(r)
ALL = pd.DataFrame(rows).drop_duplicates(["name", "universe"])
ALL.to_csv(OUT / "all_runs.csv", index=False)

ss = getSampleStyleSheet()
DARK, GREY = "#0f172a", "#64748b"
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=17, leading=21, alignment=0, textColor=colors.HexColor(DARK))
SUB = ParagraphStyle("SUB", parent=ss["Normal"], fontSize=9, textColor=colors.HexColor(GREY))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12.5, textColor=colors.HexColor(DARK), spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("P", parent=ss["Normal"], fontSize=9.2, leading=13, spaceAfter=4)
BL = ParagraphStyle("BL", parent=P, leftIndent=10, spaceAfter=2)
SM = ParagraphStyle("SM", parent=P, fontSize=7.8, leading=10, textColor=colors.HexColor(GREY))
bl = lambda xs: [Paragraph(x, BL, bulletText="•") for x in xs]
f1 = lambda v, f="{:.1f}": "–" if v is None or (isinstance(v, float) and np.isnan(v)) else f.format(v)


def table(rows, widths, fs=6.8):
    tb = Table(rows, colWidths=widths, repeatRows=1)
    tb.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", fs), ("FONT", (0, 1), (-1, -1), "Helvetica", fs),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(DARK)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"), ("TOPPADDING", (0, 0), (-1, -1), 1.6), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.6)]))
    return tb


def grid(part):
    sub = ALL[ALL.part == part]
    out = [["ID", "Variant"] + [u.replace("SMALLCAP", "SC").replace("MIDCAP", "MC") for u in UNI5] + ["2008", "2018-20", "COVID"]]
    order = sub[sub.universe == "NIFTY500"].sort_values("DD", ascending=False).name
    for n in order:
        x = sub[sub.name == n].set_index("universe")
        n5 = x.loc["NIFTY500"]
        out.append([sid(n), n.split("/")[1]] + [f"{x.loc[u, 'CAGR']:.1f} / {x.loc[u, 'DD']:.0f}" if u in x.index else "–"
                                                for u in UNI5] + [f1(n5[k], "{:+.0f}") for k in CRISIS])
    return table(out, [15 * mm, 38 * mm] + [17 * mm] * 5 + [12 * mm, 13 * mm, 12 * mm])


NOTES = json.load(open(OUT / "notes.json"))
story = [Paragraph("Long/short: hardening Sa15d9d9c and adding a short book", H1),
         Paragraph("Shorts as stock futures in NIFTY 200 names (current list), 25% margin, 0.1% roll cost a month, futures "
                   "STT/fees; longs as before. 2000 – Nov 2026, compounding risk, idle cash in a liquid fund at 6.5%.", SUB),
         Paragraph("Verdict", H2)] + bl(NOTES["verdict"])
story += [Paragraph("Part 1: hardening the long book (Sa15d9d9c = L_base)", H2),
          Paragraph("Cells: CAGR % / max drawdown %. Crisis columns: NIFTY 500 equity change over 2008, Aug 2018 – Aug 2020 "
                    "and 19 Feb – 23 Mar 2020.", SM), grid("1-harden")] + bl(NOTES["part1"])
s2 = ALL[ALL.part == "2-short"]
t2 = [["ID", "Short version", "CAGR N100", "DD N100", "CAGR N200", "DD N200", "Trades", "Win %", "2008", "2018-20", "COVID"]]
for n in s2[s2.universe == "NIFTY200"].sort_values("2018-20", ascending=False).name:
    a, b = s2[(s2.name == n) & (s2.universe == "NIFTY100")].iloc[0], s2[(s2.name == n) & (s2.universe == "NIFTY200")].iloc[0]
    t2.append([sid(n), n.split("/")[1], f1(a.CAGR), f1(a.DD, "{:.0f}"), f1(b.CAGR), f1(b.DD, "{:.0f}"), b.Trades, f1(b.Win, "{:.0f}"),
               f1(b["2008"], "{:+.0f}"), f1(b["2018-20"], "{:+.0f}"), f1(b["COVID"], "{:+.0f}")])
story += [PageBreak(), Paragraph("Part 2: short books on their own", H2),
          Paragraph("NIFTY 500 runs equal NIFTY 200 (shorts restricted to NIFTY 200 names), so they are omitted. "
                    "Idle cash earns 6.5%, so a flat short book shows about 6%.", SM), table(t2, [15 * mm, 30 * mm] + [14 * mm] * 9)]
story += bl(NOTES["part2"])
story += [Paragraph("Part 3: combined books (long = L_cap20_dd)", H2), grid("3-combined")] + bl(NOTES["part3"])

fig, ax = plt.subplots(figsize=(7.4, 3.4))
for n, lab in [("longshort/L_base", "Sa15d9d9c (L_base)"), ("longshort/L_cap20_dd", "L_cap20_dd"),
               ("longshort/LS_short_w_st10_2", "LS_short_w_st10_2"), ("longshort/LS_hedge50", "LS_hedge50")]:
    e = EQ[(n, "NIFTY500")]
    ax.plot(e / e.iloc[0], lw=1, label=f"{sid(n)} {lab}")
ax.set_yscale("log"); ax.grid(alpha=.3); ax.legend(fontsize=6.5); ax.set_title("NIFTY 500, growth of 1 (log)", fontsize=9)
fig.tight_layout(); fig.savefig(OUT / "equity.png", dpi=160); plt.close(fig)
story += [Paragraph("Equity curves", H2), Image(str(OUT / "equity.png"), width=180 * mm, height=83 * mm)]
story += [Paragraph("Risk manager's notes", H2)] + bl(NOTES["risk"])
story += ids.pdf_section(sorted(set(ALL.name)), H2)
SimpleDocTemplate(str(OUT / "report.pdf"), pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm,
                  bottomMargin=12 * mm, title="Long/short study").build(story)
print("wrote", OUT / "report.pdf")
