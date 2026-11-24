"""Point-in-time NIFTY 500 study -> results/studies/pit/report.pdf
Compares Sde394f26 (longshort/L_cap20_dd, 1% risk) on today's NIFTY 500 list against the rebuilt historical
membership (universe NIFTY500_PIT, lib/membership.py), with the relative-liquidity diagnostic alongside.
"""
import sys
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
from lib import ids, membership as M, data, indices, portfolio

OUT = ROOT / "results" / "studies" / "pit"
OUT.mkdir(parents=True, exist_ok=True)
IDS = ids.by_name()
NAME = "longshort/L_cap20_dd"
RUNS = [("Today's NIFTY 500 list", NAME, "nifty500"), ("Historical membership (point in time)", NAME, "nifty500_pit"),
        ("Today's list, top-60% liquidity filter", "longshort/L_cap20_dd_liqtop60", "nifty500")]
WIN = [(2000, 2004), (2005, 2009), (2010, 2014), (2015, 2019), (2020, 2026)]
now = {f"{s}.NS" for s in indices.constituents("NIFTY500")["Symbol"].str.strip()}

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


def cg(e, a, b):
    x = e[f"{a}-01-01":f"{b}-12-31"]
    return ((x.iloc[-1] / x.iloc[0]) ** (365.25 / (x.index[-1] - x.index[0]).days) - 1) * 100


res, EQ = [], {}
for lab, n, u in RUNS:
    d = ROOT / "results" / n / u
    s = pd.read_csv(d / "summary.csv", index_col=0).iloc[0]
    e = pd.read_csv(d / "equity.csv", index_col=0, parse_dates=True).iloc[:, 0].dropna()
    EQ[lab] = e
    f = portfolio.read_fills(d / "fills_none.csv"); pnl = (f.proceeds - f.cost).sort_values(ascending=False)
    res.append([lab, f"{s['CAGR %']:.1f}", f"{s['Max DD %']:.0f}", int(s["Trades taken"]), f"{s['Win %']:.0f}",
                f"{pnl.head(5).sum() / pnl.sum() * 100:.0f}%"] + [f"{cg(e, a, b):.1f}" for a, b in WIN])

cached = data.cached_symbols()
cov = [["Mid-year", "Members mapped", "Still in today's list", "With price data", "Share tradeable"]]
for y in [2003, 2006, 2009, 2012, 2015, 2018, 2021, 2024]:
    m = M.members_on(f"{y}-06-30")
    cov.append([y, len(m), len(m & now), len(m & cached), f"{len(m & cached) / 500 * 100:.0f}%"])
ch = pd.read_csv(M.CHANGES).fillna("")
f = portfolio.read_fills(ROOT / "results" / NAME / "nifty500_pit" / "fills_none.csv")
f["pnl"] = f.proceeds - f.cost
f["still"] = f.symbol.isin(now)
gone = f[~f.still]

story = [Paragraph("NIFTY 500 point in time: how much was survivorship bias?", H1),
         Paragraph(f"Sde394f26 at 1% risk. Membership rebuilt from {ch.source.nunique()} NSE Indices change notices "
                   f"({len(ch)} inclusions/exclusions on {ch.date.nunique()} dates, 1998 – 2026).", SUB),
         Paragraph("Verdict", H2)] + bl([
    "<b>On historical membership Sde394f26 makes 13.7% CAGR with a −27% drawdown</b>, against 16.6% / −32% on "
    "today's list. About 3 points a year were survivorship bias.",
    "<b>The bias sits after 2019:</b> walk-forward CAGR is almost the same through 2019 on both lists, but 2020–26 "
    "falls from 23.4% to 11.8%. Today's list is full of stocks that joined the index because they rallied in "
    "2020–24; the backtest on today's list bought them before they were members.",
    f"<b>Stocks that have since left the index:</b> {len(gone)} of {len(f)} trades, net "
    f"₹{gone.pnl.sum():,.0f}. These are invisible when testing on today's list.",
    "<b>The top-60% liquidity diagnostic was a good proxy:</b> it gave 12.2% / −25% and the same pattern (fine "
    "before 2019, weak after).",
    "<b>Realistic figure for Sde394f26 at 1% risk: about 13–14% CAGR with a −27% drawdown</b> (before the remaining "
    "bias below); at 0.5% risk proportionally lower."])
story += [Paragraph("Results", H2), table([["Universe", "CAGR", "Max DD", "Trades", "Win %", "Top-5 share"]
                                            + [f"{a}–{str(b)[-2:]}" for a, b in WIN]] + res,
                                           [52 * mm, 11 * mm, 12 * mm, 12 * mm, 11 * mm, 16 * mm] + [13 * mm] * 5)]
story.append(Paragraph("Window columns: CAGR within each window of the same equity curve.", SM))
fig, ax = plt.subplots(figsize=(7.4, 3.2))
for lab, e in EQ.items():
    ax.plot(e / e.iloc[0], lw=1, label=lab)
ax.set_yscale("log"); ax.grid(alpha=.3); ax.legend(fontsize=7); ax.set_title("Sde394f26, growth of 1 (log)", fontsize=9)
fig.tight_layout(); fig.savefig(OUT / "equity.png", dpi=160); plt.close(fig)
story.append(Image(str(OUT / "equity.png"), width=180 * mm, height=78 * mm))
story += [Paragraph("Coverage of the rebuilt index", H2),
          table(cov, [20 * mm, 28 * mm, 32 * mm, 28 * mm, 26 * mm]),
          Paragraph("'Members mapped' counts stocks matched to an NSE symbol; unmatched names (mostly delisted or merged "
                    "companies) are kept as placeholders so the index size stays near 500.", SM)]
story += [Paragraph("Method and remaining bias", H2)] + bl([
    "Notices from niftyindices.com press releases; the NIFTY 500 section (S&P CNX 500 to 2010, CNX 500, NIFTY 500) "
    "is parsed for excluded / included rows. From 2010 rows carry NSE symbols (97% of rows); before 2010 only company "
    "names, matched to today's symbols through NSE's symbol-change and name-change files (exact, then 92% fuzzy).",
    "Membership is rebuilt backwards from today's list: before each effective date, members = members − included + "
    "excluded. From 2010 the rebuilt index holds 500–505 members; before 2010 unmatched names accumulate (575 incl. "
    "90 placeholders in 2003). Notices for 2000–2001 are almost absent from the archive, so 2000–2002 is the least "
    "reliable period. 3 notices could not be read.",
    "<b>Remaining bias:</b> about 20% of 2003–2009 members and 5–15% of later ones have no price data (delisted, "
    "merged or failed companies Yahoo no longer carries). Most were weak stocks, so the true figure is probably "
    "a little lower still.",
    "A trade is allowed only if the stock is in the index on its entry day; open positions are held to their exits "
    "after a stock leaves the index."])
# ---- all main strategies: today's list vs point in time ----
import json
J = json.load(open(OUT / "jobs.json"))


def one(n, u):
    d = ROOT / "results" / n / u
    if not (d / "summary.csv").exists():
        return None
    sm = pd.read_csv(d / "summary.csv", index_col=0)
    r = sm.loc["No target"] if "No target" in sm.index else sm.iloc[0]
    e = pd.read_csv(d / "equity.csv", index_col=0, parse_dates=True)[r.name].dropna()
    a = e[:"2018-12-31"]
    ins = ((a.iloc[-1] / a.iloc[0]) ** (365.25 / (a.index[-1] - a.index[0]).days) - 1) * 100
    out = ((e.iloc[-1] / a.iloc[-1]) ** (365.25 / (e.index[-1] - a.index[-1]).days) - 1) * 100
    return r["CAGR %"], r["Max DD %"], ins, out


allr = [["ID", "Strategy", "Today: CAGR / DD", "PIT: CAGR / DD", "Δ CAGR", "PIT 2000-18", "PIT 2019+"]]
for j in J:
    t, q = one(j["name"], "nifty500"), one(j["name"], "nifty500_pit")
    if q is None:
        continue
    allr.append([ids.short(IDS[j["name"]]) if j["name"] in IDS else "", j["name"].split("/")[-1][:40],
                 f"{t[0]:.1f} / {t[1]:.0f}" if t else "–", f"{q[0]:.1f} / {q[1]:.0f}",
                 f"{q[0] - t[0]:+.1f}" if t else "–", f"{q[2]:.1f}", f"{q[3]:.1f}"])
story += [Paragraph("All main strategies: today's list vs point in time (NIFTY 500)", H2),
          table(allr, [15 * mm, 62 * mm, 25 * mm, 23 * mm, 14 * mm, 18 * mm, 16 * mm], fs=6.8)]
story += bl(json.load(open(OUT / "notes.json"))["all"])
story += ids.pdf_section([NAME, "longshort/L_cap20_dd_liqtop60"] + [j["name"] for j in J], H2)
SimpleDocTemplate(str(OUT / "report.pdf"), pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm,
                  bottomMargin=12 * mm, title="NIFTY 500 point in time").build(story)
print("wrote", OUT / "report.pdf")
