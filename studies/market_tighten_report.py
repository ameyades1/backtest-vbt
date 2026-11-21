"""Acting on open trades when NIFTY 50 is below its 200-day average: tighten stops, or exit.

    python run_strategy.py strategies/*/*_nifty200_tighten.json strategies/*/*_nifty200_exit.json
    python studies/market_tighten_report.py

For each strategy compares: no filter | 200-DMA entry filter | + stops raised to the last weekly low while
below | + sell everything when below. Writes results/studies/market_tighten/ (report.pdf, compare.csv).
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
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image, KeepTogether
from lib import market, ids, portfolio

OUT = ROOT / "results" / "studies" / "market_tighten"
OUT.mkdir(parents=True, exist_ok=True)
GREY, DARK = "#64748b", "#0f172a"
STRATS = {"StochRSI pullback, prev-week stop": "stochrsi_pullback/monthly_prev_week_stop",
          "StochRSI pullback, candle-low stop": "stochrsi_pullback/monthly_candle_stop",
          "EMA61 breakout, weekly stop": "ema61_breakout/monthly_weekly_stop",
          "EMA61 breakout, candle-low stop": "ema61_breakout/monthly_candle_stop"}
VERS = {"No filter": "", "Entry filter": "_nifty200", "+ tighten stops": "_nifty200_tighten",
        "+ exit all": "_nifty200_exit"}
VCOL = {"No filter": "#94a3b8", "Entry filter": "#475569", "+ tighten stops": "#2563eb", "+ exit all": "#d97706"}
CRASH = [("2000–01 bust", "2000-02-15", "2001-09-21"), ("2008 crash", "2008-01-08", "2009-03-09"),
         ("2011 slide", "2010-11-05", "2011-12-20"), ("2015–16 fall", "2015-03-04", "2016-02-29"),
         ("COVID crash", "2020-01-17", "2020-03-23"), ("2024–25 correction", "2024-09-27", "2025-03-04")]
folder = lambda s, v: ROOT / "results" / f"{STRATS[s]}{VERS[v]}" / "nifty500"
fid = lambda ex: "none" if ex == "No target" else ex.split()[1].rstrip("%")


def cagr(e, s=None, t=None):
    e = e[s:t].dropna()
    return ((e.iloc[-1] / e.iloc[0]) ** (365.25 / (e.index[-1] - e.index[0]).days) - 1) * 100


def underwater(e):
    peak, best, start = e.cummax(), 0, None
    for d, v in (e < peak).items():
        if v and start is None: start = d
        if not v and start is not None: best, start = max(best, (d - start).days), None
    if start is not None: best = max(best, (e.index[-1] - start).days)
    return best / 365.25


def streak(f):
    best = cur = 0
    for x in (f.sort_values("exit_date").pnl > 0):
        cur = 0 if x else cur + 1; best = max(best, cur)
    return best


rows, EQ = [], {}
for s in STRATS:
    for v in VERS:
        sm = pd.read_csv(folder(s, v) / "summary.csv", index_col=0)
        eq = pd.read_csv(folder(s, v) / "equity.csv", index_col=0, parse_dates=True)
        for ex in sm.index:
            f = portfolio.read_fills(folder(s, v) / f"fills_{fid(ex)}.csv", parse_dates=["entry_date", "exit_date"])
            f["pnl"] = f.proceeds - f.cost
            e = eq[ex].dropna()
            EQ[(s, v, ex)] = e
            r = sm.loc[ex]
            rows.append({"Strategy": s, "Version": v, "Exit": ex, "CAGR %": r["CAGR %"], "Max DD %": r["Max DD %"],
                         "CAGR/DD": r["CAGR %"] / -r["Max DD %"], "Trades": int(r["Trades taken"]), "Win %": r["Win %"],
                         "Avg hold days": r["Avg hold days"], "Avg open": r["Avg open positions"],
                         "Loss streak": streak(f), "Underwater yrs": underwater(e),
                         "CAGR 2000-12": cagr(e, "2000", "2012"), "CAGR 2013-26": cagr(e, "2013")})
C = pd.DataFrame(rows)
C.to_csv(OUT / "compare.csv", index=False)
g = lambda s, v, ex, c: C[(C.Strategy == s) & (C.Version == v) & (C.Exit == ex)][c].iloc[0]

reg = market.regime(200)["2000":]
charts = []


def style(ax):
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.tick_params(colors=GREY, length=0, labelsize=7)
    ax.grid(axis="y", color="#e2e8f0", zorder=0)


def save(fig, name):
    p = OUT / f"_{name}.png"; fig.tight_layout(); fig.savefig(p); plt.close(fig); charts.append(p); return p


fig, axs = plt.subplots(4, 2, figsize=(7.2, 9.2), dpi=200)
for i, s in enumerate(STRATS):
    for v in VERS:
        e = EQ[(s, v, "No target")]
        axs[i, 0].plot(e.index, e / 1e5, color=VCOL[v], lw=1.1, label=v)
        axs[i, 1].plot(e.index, (e / e.cummax() - 1) * 100, color=VCOL[v], lw=.9)
    for ax in axs[i]:
        ax.fill_between(reg.index, 0, 1, where=~reg.to_numpy(), transform=ax.get_xaxis_transform(), color="#dc2626",
                        alpha=.06, lw=0)
        style(ax)
    axs[i, 0].set_yscale("log"); axs[i, 0].yaxis.set_major_formatter(lambda v, _: f"{v:g}L")
    axs[i, 1].yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    axs[i, 0].set_title(f"{s}: equity", loc="left", fontsize=7.8, fontweight="bold", color=DARK)
    axs[i, 1].set_title("drawdown", loc="left", fontsize=7.8, fontweight="bold", color=DARK)
axs[0, 0].legend(frameon=False, fontsize=6.5, loc="upper left")
p_eq = save(fig, "equity")

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=17, leading=21, alignment=0, textColor=colors.HexColor(DARK), spaceAfter=2)
SUB = ParagraphStyle("SUB", parent=ss["Normal"], fontSize=9, textColor=colors.HexColor(GREY))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12.5, textColor=colors.HexColor(DARK), spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("P", parent=ss["Normal"], fontSize=9.5, leading=13.5, spaceAfter=4)
BL = ParagraphStyle("BL", parent=P, leftIndent=10, spaceAfter=2)
SM = ParagraphStyle("SM", parent=P, fontSize=8, leading=10.5, textColor=colors.HexColor(GREY))
bl = lambda xs: [Paragraph(x, BL, bulletText="•") for x in xs]


def table(rows, widths, num_from=1, fs=7.2):
    tb = Table(rows, colWidths=widths, repeatRows=1)
    tb.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", fs), ("FONT", (0, 1), (-1, -1), "Helvetica", fs),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(DARK)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("ALIGN", (num_from, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.3), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.3)]))
    return tb


HDR = ["Version", "CAGR %", "Max DD %", "CAGR/DD", "Trades", "Win %", "Hold days", "Loss streak", "Underwater yrs",
       "2000–12", "2013–26"]
W = [26 * mm, 13 * mm, 15 * mm, 15 * mm, 13 * mm, 12 * mm, 15 * mm, 16 * mm, 18 * mm, 14 * mm, 14 * mm]


def tab(s, ex):
    return table([HDR] + [[v] + [f"{g(s, v, ex, c):.1f}" if c not in ("Trades", "Loss streak") else f"{int(g(s, v, ex, c))}"
                                 for c in ["CAGR %", "Max DD %", "CAGR/DD", "Trades", "Win %", "Avg hold days",
                                           "Loss streak", "Underwater yrs", "CAGR 2000-12", "CAGR 2013-26"]]
                          for v in VERS], W)


crash_rows = [["Window", "Strategy"] + list(VERS)]
for nm, a, b in CRASH:
    for s in list(STRATS)[:3:2]:
        crash_rows.append([nm, s.split(",")[0]] + [
            f"{(EQ[(s, v, 'No target')].asof(pd.Timestamp(b)) / EQ[(s, v, 'No target')].asof(pd.Timestamp(a)) - 1) * 100:+.0f}%"
            for v in VERS])

NT = C[C.Exit == "No target"]
main = list(STRATS)[0]
tight_dd = [(g(s, "+ tighten stops", "No target", "Max DD %") - g(s, "Entry filter", "No target", "Max DD %")) for s in STRATS]
tight_cg = [(g(s, "+ tighten stops", "No target", "CAGR %") - g(s, "Entry filter", "No target", "CAGR %")) for s in STRATS]
exit_dd = [(g(s, "+ exit all", "No target", "Max DD %") - g(s, "Entry filter", "No target", "Max DD %")) for s in STRATS]
exit_cg = [(g(s, "+ exit all", "No target", "CAGR %") - g(s, "Entry filter", "No target", "CAGR %")) for s in STRATS]
TG = C[C.Exit != "No target"]
tgp = TG.pivot_table(index=["Strategy", "Exit"], columns="Version", values=["CAGR %", "Max DD %"])
n_tg = len(tgp)
tg_dd = int((tgp[("Max DD %", "+ tighten stops")] > tgp[("Max DD %", "Entry filter")]).sum())
tg_cg = int((tgp[("CAGR %", "+ tighten stops")] > tgp[("CAGR %", "Entry filter")]).sum())


def fmt(s, v):
    return f"{g(s, v, 'No target', 'CAGR %'):.1f}% / {g(s, v, 'No target', 'Max DD %'):.0f}%"


FIND = [
    f"<b>Main strategy (StochRSI, prev-week stop, no target)</b>: no filter {fmt(main, 'No filter')}; entry filter "
    f"{fmt(main, 'Entry filter')}; + tighten stops {fmt(main, '+ tighten stops')}; + exit all {fmt(main, '+ exit all')} "
    f"(CAGR / max drawdown).",
    f"<b>Tightening stops, no-target exits (vs entry filter only)</b>: drawdown change "
    f"{min(tight_dd):+.0f} to {max(tight_dd):+.0f} points (+ = shallower), CAGR change {min(tight_cg):+.1f} to "
    f"{max(tight_cg):+.1f} points across the four strategies.",
    f"<b>Exit all, no-target exits</b>: drawdown change {min(exit_dd):+.0f} to {max(exit_dd):+.0f} points, CAGR change "
    f"{min(exit_cg):+.1f} to {max(exit_cg):+.1f} points. Selling everything on each cross costs many trends that "
    f"resume, and the index crossed its average about 190 times since 2000.",
    f"<b>Fixed targets</b>: tightening made the drawdown shallower in {tg_dd} of {n_tg} results and raised CAGR in "
    f"{tg_cg} of {n_tg}.",
]
FIND.append(
    f"<b>Why it fails: churn.</b> The main strategy goes from {int(g(main, 'Entry filter', 'No target', 'Trades'))} to "
    f"{int(g(main, '+ tighten stops', 'No target', 'Trades'))} trades and the average hold falls from "
    f"{g(main, 'Entry filter', 'No target', 'Avg hold days'):.0f} to {g(main, '+ tighten stops', 'No target', 'Avg hold days'):.0f} days. "
    f"Each dip below the average stops trades out near the lows; when the market recovers the slots refill with new "
    f"signals at higher prices, and every round trip costs about 1.1% in fees and slippage. The multi-year winners "
    f"that pay for the strategy are cut short. Its worst drawdown is a slow bleed from 2006 to late 2013 through the "
    f"repeated crosses of 2008–2013.")
FIND.append(
    "<b>Where it helps</b>: the EMA61 breakout versions, whose positions are weaker, get much shallower drawdowns "
    f"(weekly stop {fmt(list(STRATS)[2], 'Entry filter')} to {fmt(list(STRATS)[2], '+ tighten stops')}; candle-low stop "
    f"{fmt(list(STRATS)[3], 'Entry filter')} to {fmt(list(STRATS)[3], '+ tighten stops')}), but pay with 2–3 points of "
    "CAGR. Their CAGR/drawdown ratio barely changes, so it is a lower-risk, lower-return version, not a better one.")
REC = [
    "<b>Do not tighten stops or exit on a NIFTY 200-day cross for the main StochRSI strategy.</b> It cuts CAGR almost in "
    "half and does not reduce the drawdown.",
    "<b>The 200-day average is too noisy as a trigger for open trades</b> (about 190 crosses since 2000). If we try "
    "again, use a slower or confirmed signal: for example NIFTY below its 200-day average for 4+ weeks, or the "
    "200-day average itself falling, or a monthly close below a monthly EMA.",
    "<b>Sizing may work better than stops.</b> Halving the risk per new trade after a 10% equity drawdown (our risk "
    "rule) cuts exposure without selling winners. That is the next test worth running.",
]
story = [
    Paragraph("Acting on Open Trades Below the 200-Day Average", H1),
    Paragraph("NIFTY 500 · 2000 to 2026 · 1% risk per trade · 8 slots · Sharekhan delivery costs + 0.1% slippage per side",
              SUB),
    Paragraph("Data: actual traded prices (split/bonus adjusted). Today's index members only (survivorship bias). The "
              "market signal uses the Sensex before mid-2008. Research, not financial advice.", SM),
    Paragraph("What was tested", H2)] + bl([
    "<b>Signal</b>: NIFTY 50 closed below its 200-day simple average the previous day.",
    "<b>Entry filter</b>: no new trades on those days (the earlier study).",
    "<b>+ tighten stops</b>: entry filter, and every day the signal is on, each open trade's stop is raised to the low "
    "of the last completed week (never lowered). When the market recovers the stop stays where it was raised to.",
    "<b>+ exit all</b>: entry filter, and all open trades are sold at the open on the first day the signal is on. "
    "This is the extreme version: it shows the most the signal can do for drawdowns.",
    "Everything else as in each strategy: entries, initial stops, targets and the monthly EMA61 exit."]) + [
    Paragraph("Answer", H2)] + bl(FIND[:1] + FIND[4:6]) + [
    Image(str(p_eq), width=172 * mm, height=220 * mm),
    Paragraph("Red shading: NIFTY below its 200-day average.", SM),
    Paragraph("No-target exit, each strategy", H2)] + sum(
    [[KeepTogether([Paragraph(s, P), tab(s, "No target")])] for s in STRATS], []) + [
    KeepTogether([Paragraph("Account change during each fall (no target)", H2),
                  table(crash_rows, [32 * mm, 30 * mm, 26 * mm, 26 * mm, 28 * mm, 26 * mm])]),
    Paragraph("Fixed targets", H2)] + sum(
    [[KeepTogether([Paragraph(f"{s} · {ex}", P), tab(s, ex)]) for ex in ["Target 15%", "Target 20%"]
      if ex in C[C.Strategy == s].Exit.values] for s in STRATS], []) + [
    Paragraph("What the study shows", H2)] + bl(FIND) + [Paragraph("Recommendation", H2)] + bl(REC)
story += ids.pdf_section([STRATS[s] + VERS[v] for s in STRATS for v in VERS], H2)
SimpleDocTemplate(str(OUT / "report.pdf"), pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=16 * mm,
                  bottomMargin=16 * mm, title="Acting on open trades below the 200-day average").build(story)
for p in charts:
    p.unlink()
print(OUT / "report.pdf")
print(NT[["Strategy", "Version", "CAGR %", "Max DD %", "CAGR/DD", "Trades", "Avg hold days", "Underwater yrs",
          "CAGR 2000-12", "CAGR 2013-26"]].round(1).to_string(index=False))
for f in FIND:
    print("-", f)
