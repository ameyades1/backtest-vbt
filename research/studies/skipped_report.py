"""Skipped-signals study -> results/studies/skipped/report.pdf. Verdict text: results/studies/skipped/notes.json."""
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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image
from lib import ids

OUT = ROOT / "results" / "studies" / "skipped"
IDS = ids.by_name()
BASES = {"Y": "hold/T25_r025", "A": "stexit/A_flip", "E": "stexit/A_flip_capentry", "D": "longshort/L_cap20_dd", "C": "ddcut/C_hedge_i50_breadth"}
NAME = {"Y": "S63387f09", "A": "Sf5b94362", "E": "S44984096 (your choice: 20% cap at entry)", "D": "Sde394f26", "C": "Sa016f4eb"}
SN = {"Y": "S63387f09", "A": "Sf5b94362", "E": "S44984096", "D": "Sde394f26", "C": "Sa016f4eb"}
WHY = {"taken": "Taken", "held": "Stock already held", "slots": "All slots full", "paused": "Drawdown pause",
       "cash": "Not enough cash", "too-small": "Risk buys < 1 share", "open-risk": "Open-risk cap",
       "sector": "Sector cap", "short-max": "Short limit"}


def sig(tag):
    s = pd.read_csv(OUT / tag / "base" / "signals_none.csv", parse_dates=["day", "entry_date", "exit_date"])
    s["R"] = (s.exit - s.entry) / (s.entry - s.stop) * s.side
    s["hold"] = (s.exit_date - s.entry_date).dt.days
    return s[s.exit.notna()]


def outcome_table(s):
    rows = [["Signal outcome", "Signals", "Win %", "Avg R", "Median R", "≥ 5R winners", "Total R", "Median hold (days)"]]
    order = ["taken"] + [k for k in WHY if k != "taken" and k in set(s.taken)]
    for k in order + ["_skipped"]:
        x = s[s.taken != "taken"] if k == "_skipped" else s[s.taken == k]
        if k == "_skipped":
            x = x[x.taken != "held"]
        if not len(x):
            continue
        rows.append(["All skipped (excl. already held)" if k == "_skipped" else WHY[k], len(x), f"{(x.R > 0).mean() * 100:.0f}",
                     f"{x.R.mean():.2f}", f"{x.R.median():.2f}", f"{(x.R >= 5).mean() * 100:.1f}%", f"{x.R.sum():.0f}",
                     f"{x.hold.median():.0f}"])
    return rows


def year_table(s):
    s = s.assign(y=s.entry_date.dt.year, sk=s.taken != "taken")
    s = s[s.taken != "held"]
    rows = [["Period", "Taken", "Avg R taken", "Skipped", "Avg R skipped"]]
    for a, b in [(2000, 2004), (2005, 2009), (2010, 2014), (2015, 2019), (2020, 2026)]:
        x = s[(s.y >= a) & (s.y <= b)]
        t, k = x[~x.sk], x[x.sk]
        rows.append([f"{a}–{str(b)[-2:]}", len(t), f"{t.R.mean():.2f}" if len(t) else "–", len(k),
                     f"{k.R.mean():.2f}" if len(k) else "–"])
    return rows


def slots_table():
    rows = [["ID", "Strategy", "Slots", "CAGR", "Max DD", "Trades", "Skipped", "Avg deployed", "Max deployed",
             "Cash-capped trades"]]
    for tag, base in BASES.items():
        for n, k in [(base, "10"), (f"skipped/{SN[tag]}_slots15", "15"), (f"skipped/{SN[tag]}_slots20", "20"),
                     (f"skipped/{SN[tag]}_slotsall", "no limit")]:
            p = ROOT / "results" / n / "nifty500_pit" / "summary.csv"
            if not p.exists():
                continue
            r = pd.read_csv(p, index_col=0).iloc[0]
            cc = [c for c in r.index if c.startswith("Cash-capped")]
            rows.append([ids.short(IDS[n]) if n in IDS else "", SN[tag], k, f"{r['CAGR %']:.1f}", f"{r['Max DD %']:.0f}",
                         int(r["Trades taken"]), int(r["Signals skipped"]), f"{r['Avg deployed %']:.0f}%",
                         f"{r['Max deployed %']:.0f}%", f"{r[cc[0]]:.0f}" if cc else "–"])
    return rows


ss = getSampleStyleSheet()
DARK, GREY = "#0f172a", "#64748b"
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=17, leading=21, alignment=0, textColor=colors.HexColor(DARK))
SUB = ParagraphStyle("SUB", parent=ss["Normal"], fontSize=9, textColor=colors.HexColor(GREY))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12.5, textColor=colors.HexColor(DARK), spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("P", parent=ss["Normal"], fontSize=9.2, leading=13, spaceAfter=4)
BL = ParagraphStyle("BL", parent=P, leftIndent=10, spaceAfter=2)
SM = ParagraphStyle("SM", parent=P, fontSize=7.8, leading=10, textColor=colors.HexColor(GREY))
bl = lambda xs: [Paragraph(x, BL, bulletText="•") for x in xs]


def table(rows, widths, fs=7.2):
    tb = Table(rows, colWidths=widths, repeatRows=1)
    tb.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", fs), ("FONT", (0, 1), (-1, -1), "Helvetica", fs),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(DARK)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    return tb


notes = json.load(open(OUT / "notes.json"))
rnd = pd.read_csv(OUT / "random.csv")
story = [Paragraph("Skipped signals: what if we had traded them?", H1),
         Paragraph("S44984096 (your choice), Sf5b94362, S63387f09, Sde394f26 and Sa016f4eb (hedged), point-in-time NIFTY 500 from 2000, costs included. Every signal "
                   "is played out in full by the engine whether or not the portfolio takes it.", SUB),
         Paragraph("Verdict", H2)] + bl(notes["verdict"])
base = {}
for tag in BASES:
    r = pd.read_csv(ROOT / "results" / BASES[tag] / "nifty500_pit" / "summary.csv", index_col=0).iloc[0]
    base[tag] = r
s_all = {t: sig(t) for t in BASES}
for tag in BASES:
    story += [Paragraph(f"{NAME[tag]}: taken vs skipped signals", H2),
              table(outcome_table(s_all[tag]), [52 * mm, 16 * mm, 14 * mm, 15 * mm, 17 * mm, 22 * mm, 17 * mm, 26 * mm])]
story.append(Paragraph("R = profit or loss as a multiple of the trade's initial risk (entry − stop). 'Stock already held': "
                       "a new signal in a stock the portfolio already owns.", SM))
story += [Paragraph("Taken vs skipped by period (S63387f09)", H2),
          table(year_table(s_all["Y"]), [30 * mm, 22 * mm, 26 * mm, 22 * mm, 26 * mm])]
story += [Paragraph("Trading more of them: 15, 20 and unlimited slots", H2),
          table(slots_table(), [15 * mm, 22 * mm, 15 * mm, 12 * mm, 14 * mm, 14 * mm, 15 * mm, 20 * mm, 20 * mm, 26 * mm])]
story.append(Paragraph("Same 1% risk per trade on current equity; with more slots, cash, not slots, becomes the limit.", SM))
fig, axs = plt.subplots(1, len(BASES), figsize=(7.4, 2.6))
rr = [["Strategy", "Actual (tightest stop first)", "Random: median", "5th – 95th pct", "Actual's percentile",
       "Random DD median", "DD 5th – 95th"]]
for ax, tag in zip(axs, BASES):
    x = rnd[rnd.tag == tag]
    a, d = base[tag]["CAGR %"], base[tag]["Max DD %"]
    ax.hist(x.CAGR, bins=25, color="#94a3b8"); ax.axvline(a, color="#dc2626", lw=1.5, label=f"actual {a:.1f}%")
    ax.set_title(f"{SN[tag]}: {len(x)} random picks", fontsize=8); ax.legend(fontsize=6.5); ax.tick_params(labelsize=7)
    rr.append([SN[tag], f"{a:.1f}% / {d:.0f}%", f"{x.CAGR.median():.1f}%", f"{x.CAGR.quantile(.05):.1f} – {x.CAGR.quantile(.95):.1f}%",
               f"{(x.CAGR < a).mean() * 100:.0f}", f"{x.DD.median():.0f}%", f"{x.DD.quantile(.05):.0f} to {x.DD.quantile(.95):.0f}%"])
fig.tight_layout(); fig.savefig(OUT / "random.png", dpi=160); plt.close(fig)
story += [Paragraph("Random-pick check: 200 runs each", H2),
          table(rr, [22 * mm, 34 * mm, 24 * mm, 26 * mm, 24 * mm, 26 * mm, 26 * mm]),
          Image(str(OUT / "random.png"), width=180 * mm, height=68 * mm),
          Paragraph("Each run fills scarce slots with a random order of the same day's signals instead of the tightest "
                    "stop first; everything else is identical. Percentile: share of random runs with a lower CAGR.", SM)]
for k in ("findings", "method"):
    if k in notes:
        story += [Paragraph(notes[k]["title"], H2)] + bl(notes[k]["points"])
story += ids.pdf_section(list(BASES.values()) + [f"skipped/{SN[t]}_slots{k}" for t in BASES for k in ("15", "20", "all")], H2)
SimpleDocTemplate(str(OUT / "report.pdf"), pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm,
                  bottomMargin=12 * mm, title="Skipped signals").build(story)
print("wrote", OUT / "report.pdf")
