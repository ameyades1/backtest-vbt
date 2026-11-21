"""Holding-period study on S1704ed9f -> results/studies/hold/report.pdf (+ summary.csv). Text: notes.json."""
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
from lib import ids, portfolio

OUT = ROOT / "results" / "studies" / "hold"
IDS = ids.by_name()
BASE = "filter/F_i200"
J = json.load(open(OUT / "jobs.json"))
DAYS, RS = (10, 15, 20, 25, 35, 50), (0, 0.25, 0.5, 1.0)


def cg(e):
    return ((e.iloc[-1] / e.iloc[0]) ** (365.25 / (e.index[-1] - e.index[0]).days) - 1) * 100


def stats(n):
    d = ROOT / "results" / n / "nifty500_pit"
    r = pd.read_csv(d / "summary.csv", index_col=0).iloc[0]
    e = pd.read_csv(d / "equity.csv", index_col=0, parse_dates=True)[r.name].dropna()
    ins, oos = e[:"2014-12-31"], e["2014-12-31":]
    f = portfolio.read_fills(d / "fills_none.csv", parse_dates=["entry_date", "exit_date"])
    f["pnl"] = f.proceeds - f.cost
    f["days"] = (f.exit_date - f.entry_date).dt.days
    return {"name": n, "CAGR": r["CAGR %"], "DD": r["Max DD %"], "trades": int(r["Trades taken"]),
            "win": r["Win %"], "hold_med": r["Median hold days"], "hold_avg": r["Avg hold days"],
            "IS CAGR": cg(ins), "IS DD": (ins / ins.cummax() - 1).min() * 100, "OOS CAGR": cg(oos),
            "OOS DD": (oos / oos.cummax() - 1).min() * 100}, f


S, F = {}, {}
for n in [BASE] + [j["name"] for j in J]:
    try:
        S[n], F[n] = stats(n)
    except FileNotFoundError:
        pass
df = pd.DataFrame(S.values()); df.to_csv(OUT / "summary.csv", index=False)
cell = lambda d, r: BASE if (d, r) == (25, 0.5) else f"hold/T{d}_r{str(r).replace('.', '')}"
grid_c = np.array([[S[cell(d, r)]["CAGR"] if cell(d, r) in S else np.nan for r in RS] for d in DAYS])
grid_d = np.array([[S[cell(d, r)]["DD"] if cell(d, r) in S else np.nan for r in RS] for d in DAYS])
fig, axs = plt.subplots(1, 2, figsize=(7.4, 3.0))
for ax, g, t, cm in [(axs[0], grid_c, "CAGR %", "Greens"), (axs[1], grid_d, "Max drawdown %", "Reds_r")]:
    ax.imshow(g, cmap=cm, aspect="auto")
    ax.set_xticks(range(len(RS)), [f"{r:g}R" for r in RS], fontsize=7); ax.set_yticks(range(len(DAYS)), [f"{d}d" for d in DAYS], fontsize=7)
    ax.set_xlabel("gain needed at the check", fontsize=7); ax.set_ylabel("check day", fontsize=7)
    for i in range(len(DAYS)):
        for k in range(len(RS)):
            ax.text(k, i, f"{g[i, k]:.1f}", ha="center", va="center", fontsize=7,
                    fontweight="bold" if (DAYS[i], RS[k]) == (25, 0.5) else "normal")
    ax.set_title(t, fontsize=8.5)
fig.tight_layout(); fig.savefig(OUT / "grid.png", dpi=160); plt.close(fig)


def row(n, label=None):
    s = S[n]
    return [ids.short(IDS[n]) if n in IDS else "", label or n.split("/")[-1], f"{s['CAGR']:.1f}", f"{s['DD']:.0f}",
            f"{s['CAGR'] / -s['DD']:.2f}", s["trades"], f"{s['win']:.0f}", f"{s['hold_med']:.0f}", f"{s['hold_avg']:.0f}",
            f"{s['OOS CAGR']:.1f}", f"{s['OOS DD']:.0f}"]


HDR = ["ID", "Variant", "CAGR", "Max DD", "CAGR/DD", "Trades", "Win %", "Median hold", "Avg hold", "2015–26 CAGR", "2015–26 DD"]
W = [16 * mm, 50 * mm, 11 * mm, 12 * mm, 13 * mm, 12 * mm, 11 * mm, 14 * mm, 13 * mm, 15 * mm, 14 * mm]
grp = lambda ph: [j["name"] for j in J if j["phase"] == ph and j["name"] in S]
lab = {"hold/T_none": "No time stop", "hold/X_st25": "Weekly Supertrend(10, 2.5)", "hold/X_st4": "Weekly Supertrend(10, 4)",
       "hold/X_mst3": "Monthly Supertrend(10, 3)", "hold/X_atr3": "+ 3 x ATR trailing stop", "hold/Cap90": "Sell after 90 days",
       "hold/Cap180": "Sell after 180 days", "hold/Cap365": "Sell after 365 days"}
RLAB = {"0": "0", "025": "0.25", "05": "0.5", "10": "1"}
tlab = lambda n: lab[n] if n in lab else f"{n.split('/T')[1].split('_r')[0]} days, {RLAB[n.split('_r')[1]]}R"
T1 = [HDR, row(BASE, "S1704ed9f: 25 days, 0.5R")] + [row(n, tlab(n)) for n in grp("1-timestop")]
T3 = [HDR, row(BASE, "S1704ed9f: weekly Supertrend(10, 3)")] + [row(n, lab[n]) for n in grp("3-trail")]
T4 = [HDR, row(BASE, "S1704ed9f: no cap")] + [row(n, lab[n]) for n in grp("4-cap")]
# walk-forward on all variants
cand = df[df.name != BASE].assign(score=lambda x: x["IS CAGR"] / -x["IS DD"]).sort_values("score", ascending=False)
b0 = S[BASE]
WF = [["Rank on 2000–14", "ID", "Variant", "2000–14 CAGR / DD", "2015–26 CAGR / DD", "vs S1704ed9f 2015–26"]]
for i, r in enumerate(cand.head(5).to_dict("records"), 1):
    WF.append([i, ids.short(IDS[r["name"]]), r["name"].split("/")[-1], f"{r['IS CAGR']:.1f} / {r['IS DD']:.0f}",
               f"{r['OOS CAGR']:.1f} / {r['OOS DD']:.0f}", f"{r['OOS CAGR'] - b0['OOS CAGR']:+.1f} pts"])
WF.append(["–", "S1704ed9f", "F_i200", f"{b0['IS CAGR']:.1f} / {b0['IS DD']:.0f}", f"{b0['OOS CAGR']:.1f} / {b0['OOS DD']:.0f}", "–"])
# holding-time buckets for the base
f = F[BASE]
B = [["Held", "Trades", "Share of trades", "Net P&L share", "Win %"]]
for a, b, t in [(0, 30, "under 1 month"), (30, 182, "1–6 months"), (182, 365, "6–12 months"), (365, 10 ** 5, "over 1 year")]:
    x = f[(f.days >= a) & (f.days < b)]
    B.append([t, len(x), f"{len(x) / len(f) * 100:.0f}%", f"{x.pnl.sum() / f.pnl.sum() * 100:.0f}%", f"{(x.pnl > 0).mean() * 100:.0f}"])

ss = getSampleStyleSheet()
DARK, GREY = "#0f172a", "#64748b"
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=17, leading=21, alignment=0, textColor=colors.HexColor(DARK))
SUB = ParagraphStyle("SUB", parent=ss["Normal"], fontSize=9, textColor=colors.HexColor(GREY))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12.5, textColor=colors.HexColor(DARK), spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("P", parent=ss["Normal"], fontSize=9.2, leading=13, spaceAfter=4)
BL = ParagraphStyle("BL", parent=P, leftIndent=10, spaceAfter=2)
SM = ParagraphStyle("SM", parent=P, fontSize=7.8, leading=10, textColor=colors.HexColor(GREY))
bl = lambda xs: [Paragraph(x, BL, bulletText="•") for x in xs]


def table(rows, widths, fs=6.9):
    tb = Table(rows, colWidths=widths, repeatRows=1)
    tb.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", fs), ("FONT", (0, 1), (-1, -1), "Helvetica", fs),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(DARK)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#fef3c7")),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    return tb


notes = json.load(open(OUT / "notes.json"))
story = [Paragraph("Holding periods for S1704ed9f", H1),
         Paragraph("Your strategy (Sde394f26 with the NIFTY 500 index filter) at 1% risk, point-in-time NIFTY 500 from "
                   "2000, costs included. Only the exit rules change. Amber row: S1704ed9f as it is.", SUB),
         Paragraph("Verdict", H2)] + bl(notes["verdict"])
story += [Paragraph("1. Time-stop check: day × gain needed", H2), Image(str(OUT / "grid.png"), width=180 * mm, height=73 * mm),
          Paragraph("Bold cell: the current rule (sell at the next open if the trade is not 0.5R up 25 days after entry).", SM),
          table(T1, W)]
story += [Paragraph("3. Trailing exit", H2), table(T3, W), Paragraph("4. Holding caps", H2), table(T4, W),
          Paragraph("Hold columns in calendar days, per fill.", SM)]
story += [Paragraph("Where S1704ed9f's profit comes from, by holding time", H2),
          table(B, [40 * mm, 20 * mm, 28 * mm, 28 * mm, 18 * mm])]
story += [Paragraph("Walk-forward: choose on 2000–14, check on 2015–26", H2),
          table(WF, [22 * mm, 16 * mm, 30 * mm, 32 * mm, 32 * mm, 34 * mm])]
for k in ("findings", "method"):
    if k in notes:
        story += [Paragraph(notes[k]["title"], H2)] + bl(notes[k]["points"])
story += ids.pdf_section([BASE] + [j["name"] for j in J], H2)
SimpleDocTemplate(str(OUT / "report.pdf"), pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm,
                  bottomMargin=12 * mm, title="Holding periods for S1704ed9f").build(story)
print("wrote", OUT / "report.pdf")
