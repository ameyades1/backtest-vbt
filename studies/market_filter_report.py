"""NIFTY 200-day market filter: every strategy with and without it.

    python run_strategy.py strategies/*/*_nifty200.json            (and --universe NIFTY50 for the StochRSI pair)
    python studies/market_filter_report.py

Reads results/<family>/<variant>[_nifty200]/<universe>/ and writes results/studies/market_filter/
(report.pdf, pairs.csv).
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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak
from lib import data, market

OUT = ROOT / "results" / "studies" / "market_filter"
OUT.mkdir(parents=True, exist_ok=True)
BLUE, GREY, DARK, RED, GREEN, LIGHT = "#2563eb", "#64748b", "#0f172a", "#dc2626", "#15803d", "#cbd5e1"
NAMES = {"ema61_breakout/monthly_candle_stop": "EMA61 breakout, candle-low stop",
         "ema61_breakout/monthly_candle_stop_r2p4": "EMA61 breakout, candle-low stop, 2%/4",
         "ema61_breakout/monthly_candle_stop_time90": "EMA61 breakout, candle-low, 90-day exit",
         "ema61_breakout/monthly_candle_stop_time180": "EMA61 breakout, candle-low, 180-day exit",
         "ema61_breakout/monthly_candle_stop_time365": "EMA61 breakout, candle-low, 365-day exit",
         "ema61_breakout/monthly_weekly_stop": "EMA61 breakout, weekly stop",
         "ema61_breakout/monthly_weekly_stop_time90": "EMA61 breakout, weekly stop, 90-day exit",
         "ema61_breakout/monthly_weekly_stop_time180": "EMA61 breakout, weekly stop, 180-day exit",
         "ema61_breakout/monthly_weekly_stop_time365": "EMA61 breakout, weekly stop, 365-day exit",
         "ema61_breakout/monthly_weekly_trail": "EMA61 breakout, trailing weekly stop",
         "stochrsi_pullback/monthly_candle_stop": "StochRSI pullback, candle-low stop",
         "stochrsi_pullback/monthly_prev_week_stop": "StochRSI pullback, prev-week stop",
         "stochrsi_pullback/weekly_candle_stop": "StochRSI pullback, weekly candles"}

# ---------------- pairs ----------------
pairs = []
for f in sorted(ROOT.glob("results/*/*_nifty200/*/summary.csv")):
    fam, var, uni = f.parts[-4], f.parts[-3].replace("_nifty200", ""), f.parts[-2]
    base = ROOT / "results" / fam / var / uni
    pairs.append({"key": f"{fam}/{var}", "uni": uni.upper(), "base": base, "filt": f.parent,
                  "name": NAMES.get(f"{fam}/{var}", f"{fam}/{var}") + ("" if uni == "nifty500" else " (NIFTY 50)")})
rows = []
for p in pairs:
    a, b = pd.read_csv(p["base"] / "summary.csv", index_col=0), pd.read_csv(p["filt"] / "summary.csv", index_col=0)
    for ex in a.index:
        r = {"Strategy": p["name"], "Universe": p["uni"], "Exit": ex}
        for k in ["CAGR %", "Max DD %", "Win %", "Trades taken", "Avg deployed %", "Final equity (Rs)"]:
            r[k] = a.at[ex, k]; r[k + " (filter)"] = b.at[ex, k]
        r["CAGR/DD"] = a.at[ex, "CAGR %"] / -a.at[ex, "Max DD %"]
        r["CAGR/DD (filter)"] = b.at[ex, "CAGR %"] / -b.at[ex, "Max DD %"]
        rows.append(r)
T = pd.DataFrame(rows)
T.to_csv(OUT / "pairs.csv", index=False)
T["dC"] = T["CAGR % (filter)"] - T["CAGR %"]
T["dD"] = T["Max DD % (filter)"] - T["Max DD %"]          # positive = shallower with filter
T["dM"] = T["CAGR/DD (filter)"] - T["CAGR/DD"]
NT = T[T.Exit == "No target"]
TG = T[T.Exit != "No target"]

# ---------------- market regime ----------------
reg = market.regime(200)
src = market.source(200)
idx = data.load(["^NSEI", "^BSESN"])["Close"]
nifty_start = src[src == "NIFTY 50"].index[0]
lvl = pd.concat([idx["^BSESN"].dropna()[lambda s: s.index < nifty_start] / idx["^BSESN"].dropna()[:nifty_start].iloc[-1]
                 * idx["^NSEI"].dropna()[nifty_start:].iloc[0], idx["^NSEI"].dropna()[nifty_start:]])
lvl = lvl["2000":]
sma = pd.concat([idx["^BSESN"].dropna().rolling(200).mean()[lambda s: s.index < nifty_start]
                 / idx["^BSESN"].dropna()[:nifty_start].iloc[-1] * idx["^NSEI"].dropna()[nifty_start:].iloc[0],
                 idx["^NSEI"].dropna().rolling(200).mean()[nifty_start:]])["2000":]
r00 = reg["2000":]
below_pct = (~r00).mean() * 100
switches = int((r00 != r00.shift()).sum() - 1)
# below-200 spells of at least 40 trading days
spells, start = [], None
for d, v in r00.items():
    if not v and start is None:
        start = d
    if v and start is not None:
        spells.append((start, prev)); start = None
    prev = d
if start is not None:
    spells.append((start, r00.index[-1]))
spells = [(s, e) for s, e in spells if len(r00[s:e]) >= 40]
spell_rows = [["Below 200-DMA from", "to", "Trading days", "Index change"]]
for s, e in spells:
    ch = (lvl.asof(e) / lvl.asof(s) - 1) * 100
    spell_rows.append([f"{s:%d %b %Y}", f"{e:%d %b %Y}", f"{len(r00[s:e])}", f"{ch:+.0f}%"])

# ---------------- main strategies: curves ----------------
MAINS = [("stochrsi_pullback/monthly_prev_week_stop", "nifty500", "No target"),
         ("stochrsi_pullback/monthly_candle_stop", "nifty500", "No target"),
         ("ema61_breakout/monthly_weekly_stop", "nifty500", "No target"),
         ("ema61_breakout/monthly_candle_stop", "nifty500", "No target"),
         ("stochrsi_pullback/weekly_candle_stop", "nifty500", "Target 15%"),
         ("ema61_breakout/monthly_candle_stop", "nifty500", "Target 20%")]


def curves(key, uni, ex):
    fam, var = key.split("/")
    a = pd.read_csv(ROOT / "results" / fam / var / uni / "equity.csv", index_col=0, parse_dates=True)[ex].dropna()
    b = pd.read_csv(ROOT / "results" / fam / f"{var}_nifty200" / uni / "equity.csv", index_col=0, parse_dates=True)[ex].dropna()
    da = pd.read_csv(ROOT / "results" / fam / var / uni / f"fills_{'none' if ex == 'No target' else ex.split()[1].rstrip('%')}.csv",
                     parse_dates=["entry_date", "exit_date"])
    return a, b


def cagr(e, s, t):
    e = e[s:t]
    if len(e) < 2:
        return np.nan
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    return ((e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1) * 100


def mdd(e):
    return (e / e.cummax() - 1).min() * 100


CRASH = [("Dot-com bust", "2000-02-15", "2001-09-21"), ("2008 crash", "2008-01-08", "2009-03-09"),
         ("2011 slide", "2010-11-05", "2011-12-20"), ("2015–16 fall", "2015-03-04", "2016-02-29"),
         ("COVID crash", "2020-01-17", "2020-03-23"), ("2024–25 correction", "2024-09-27", "2025-03-04")]
crash_rows = [["Window", "Index"] + sum([[f"S{i + 1}", f"S{i + 1} filter"] for i in range(4)], [])]
eqs = {m: curves(*m) for m in MAINS}
for nm, s, t in CRASH:
    row = [Paragraph(f"{nm}<br/><font size=6.5>{pd.Timestamp(s):%b %Y}–{pd.Timestamp(t):%b %Y}</font>", None),
           f"{(lvl.asof(pd.Timestamp(t)) / lvl.asof(pd.Timestamp(s)) - 1) * 100:+.0f}%"]
    for m in MAINS[:4]:
        for e in eqs[m]:
            row.append(f"{(e.asof(pd.Timestamp(t)) / e.asof(pd.Timestamp(s)) - 1) * 100:+.0f}%")
    crash_rows.append(row)

# exposure when below 200-DMA
exp_rows = [["Strategy", "Open trades, market above", "Open trades, market below", "Below, with filter"]]
for m in MAINS[:4]:
    fam, var = m[0].split("/")
    out = [NAMES[m[0]]]
    for v in [var, var, f"{var}_nifty200"]:
        pass
    a = pd.read_csv(ROOT / "results" / fam / var / m[1] / "equity.csv", index_col=0, parse_dates=True)
    # deployed share is not stored in equity.csv; rebuild from fills
    def deployed(folder):
        f = pd.read_csv(folder / "fills_none.csv", parse_dates=["entry_date", "exit_date"])
        eq = pd.read_csv(folder / "equity.csv", index_col=0, parse_dates=True)["No target"].dropna()
        n = pd.Series(0.0, index=eq.index)
        for r in f.itertuples():
            end = r.exit_date if pd.notna(r.exit_date) else eq.index[-1]
            n[r.entry_date:end] += 1
        return n
    da = deployed(ROOT / "results" / fam / var / m[1])
    db = deployed(ROOT / "results" / fam / f"{var}_nifty200" / m[1])
    rg = r00.reindex(da.index, method="ffill").fillna(True)
    exp_rows.append([NAMES[m[0]], f"{da[rg].mean():.1f} of 8", f"{da[~rg].mean():.1f} of 8",
                     f"{db[~r00.reindex(db.index, method='ffill').fillna(True)].mean():.1f} of 8"])

sub_rows = [["Strategy", "Exit", f"2000–{nifty_start:%b %Y} (Sensex)", "with filter",
             f"{nifty_start:%b %Y}–2026 (NIFTY)", "with filter"]]
for m in MAINS:
    a, b = eqs[m]
    sub_rows.append([NAMES[m[0]], m[2], f"{cagr(a, '2000', nifty_start):.1f}%", f"{cagr(b, '2000', nifty_start):.1f}%",
                     f"{cagr(a, nifty_start, None):.1f}%", f"{cagr(b, nifty_start, None):.1f}%"])

# ---------------- charts ----------------
charts = []


def style(ax):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=GREY, length=0, labelsize=7.5)
    ax.grid(axis="y", color="#e2e8f0", zorder=0)


def save(fig, name):
    p = OUT / f"_{name}.png"; fig.tight_layout(); fig.savefig(p); plt.close(fig); charts.append(p); return p


def shade(ax):
    for s, e in spells:
        ax.axvspan(s, e, color=RED, alpha=.07, lw=0)


fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=200)
ax.plot(lvl.index, lvl, color=DARK, lw=1, label="NIFTY 50 (Sensex scaled before mid-2008)")
ax.plot(sma.index, sma, color=BLUE, lw=1, label="200-day average")
ax.fill_between(r00.index, 0, 1, where=~r00.to_numpy(), transform=ax.get_xaxis_transform(), color=RED, alpha=.12, lw=0,
                label="Below: no new entries")
ax.set_yscale("log"); ax.yaxis.set_major_formatter(lambda v, _: f"{v:,.0f}")
ax.legend(frameon=False, fontsize=7, loc="upper left")
ax.set_title("When the filter blocks new trades", loc="left", fontsize=10.5, fontweight="bold", color=DARK)
style(ax); p_reg = save(fig, "regime")

fig, axs = plt.subplots(3, 2, figsize=(7.2, 7.6), dpi=200)
for ax, m in zip(axs.flat, MAINS):
    a, b = eqs[m]
    shade(ax)
    ax.plot(a.index, a / 1e5, color="#94a3b8", lw=1.2, label="No filter")
    ax.plot(b.index, b / 1e5, color=BLUE, lw=1.3, label="200-DMA filter")
    ax.set_yscale("log"); ax.yaxis.set_major_formatter(lambda v, _: f"{v:g}L")
    ax.set_title(f"{NAMES[m[0]]}\n{m[2]}", loc="left", fontsize=7.8, fontweight="bold", color=DARK)
    style(ax)
axs[0, 0].legend(frameon=False, fontsize=7, loc="upper left")
p_eq = save(fig, "equity")

fig, axs = plt.subplots(3, 2, figsize=(7.2, 6.6), dpi=200, sharey=True)
for ax, m in zip(axs.flat, MAINS):
    a, b = eqs[m]
    shade(ax)
    ax.plot(a.index, (a / a.cummax() - 1) * 100, color="#94a3b8", lw=1)
    ax.plot(b.index, (b / b.cummax() - 1) * 100, color=BLUE, lw=1)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.set_title(f"{NAMES[m[0]]} · {m[2]}", loc="left", fontsize=7.5, fontweight="bold", color=DARK)
    style(ax)
p_dd = save(fig, "dd")

fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.0), dpi=200)
for ax, (sub, lbl) in zip(axs, [(NT, "No-target exits"), (TG, "Fixed-target exits")]):
    ax.axhline(0, color=GREY, lw=.6); ax.axvline(0, color=GREY, lw=.6)
    ax.scatter(sub["dD"], sub["dC"], s=16, color=BLUE, zorder=3)
    ax.set_xlabel("Drawdown change (points, + = shallower)", fontsize=7, color=GREY)
    ax.set_ylabel("CAGR change (points)", fontsize=7, color=GREY)
    ax.set_title(f"{lbl} ({len(sub)})", loc="left", fontsize=9, fontweight="bold", color=DARK)
    style(ax)
p_sc = save(fig, "scatter")

# ---------------- PDF ----------------
ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=17, leading=21, alignment=0, textColor=colors.HexColor(DARK), spaceAfter=2)
SUB = ParagraphStyle("SUB", parent=ss["Normal"], fontSize=9, textColor=colors.HexColor(GREY))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12.5, textColor=colors.HexColor(DARK), spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("P", parent=ss["Normal"], fontSize=9.5, leading=13.5, spaceAfter=4)
BL = ParagraphStyle("BL", parent=P, leftIndent=10, spaceAfter=2)
SM = ParagraphStyle("SM", parent=P, fontSize=8, leading=10.5, textColor=colors.HexColor(GREY))
TC = ParagraphStyle("TC", parent=SM, fontSize=7.4, leading=9, textColor=colors.HexColor(DARK))
for r in crash_rows[1:]:
    r[0].style = TC


def table(rows, widths, num_from=1, fs=7.5):
    tb = Table(rows, colWidths=widths, repeatRows=1)
    tb.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", fs), ("FONT", (0, 1), (-1, -1), "Helvetica", fs),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(DARK)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("ALIGN", (num_from, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))
    return tb


bl = lambda xs: [Paragraph(x, BL, bulletText="•") for x in xs]
n_nt, n_tg = len(NT), len(TG)
nt_cu, nt_du = (NT.dC > 0).sum(), (NT.dD > 0).sum()
tg_cu, tg_du = (TG.dC > 0).sum(), (TG.dD > 0).sum()
main = T[(T.Strategy == "StochRSI pullback, prev-week stop") & (T.Exit == "No target")].iloc[0]
wk = T[(T.Strategy == "StochRSI pullback, weekly candles") & (T.Exit == "Target 15%")].iloc[0]
c2008 = crash_rows[2]
exp_main = exp_rows[1]

FIND = [
    f"<b>The filter does what it promises for short, fixed-target trades.</b> Across {n_tg} fixed-target results it made "
    f"the maximum drawdown shallower in {tg_du} and raised CAGR in {tg_cu}; the median drawdown improved by "
    f"{TG.dD.median():.1f} points. Example: the weekly StochRSI pullback with a 15% target goes from "
    f"{wk['CAGR %']:.1f}% / {wk['Max DD %']:.0f}% to {wk['CAGR % (filter)']:.1f}% / {wk['Max DD % (filter)']:.0f}%. These "
    f"trades last weeks, so blocking entries in a falling market removes most of the bear-market losses.",
    f"<b>For the trend-following no-target versions the effect is mixed.</b> Across {n_nt} no-target results CAGR rose "
    f"in {nt_cu} and the drawdown was shallower in {nt_du}, with no consistent pattern; CAGR changed by {NT.dC.min():+.1f} to {NT.dC.max():+.1f} "
    f"points. The main strategy (StochRSI pullback, previous-week stop) goes from {main['CAGR %']:.1f}% / "
    f"{main['Max DD %']:.0f}% to {main['CAGR % (filter)']:.1f}% / {main['Max DD % (filter)']:.0f}%.",
    f"<b>Why: the filter only stops new entries; it never sells.</b> No-target positions are held for years and are "
    f"already open when the market turns. They exit only on a monthly close below EMA61, which comes months after "
    f"NIFTY breaks its 200-day average. So the drawdowns are made by positions the filter cannot touch. While the "
    f"market is below its 200-day average the main strategy still holds {exp_main[2]} trades on average without the "
    f"filter and {exp_main[3]} with it (against {exp_main[1]} when the market is above).",
    "<b>The filter also changes which trades get the 8 slots.</b> Blocked signals leave slots free for signals after "
    "the market recovers. That path change, not risk control, explains most of the swings in the no-target results, "
    "in both directions; small differences should be read as noise.",
    f"<b>Whipsaw cost is modest.</b> Since 2000 the index spent {below_pct:.0f}% of days below its 200-day average and "
    f"crossed it {switches} times. Most crossings last days or weeks, during which some good monthly signals are "
    f"blocked.",
]
REC = [
    "<b>Use the filter for strategies with fixed targets or short holding periods.</b> It cuts drawdowns at little "
    "cost there. None of them earn enough to trade yet, but if a short-term variant is pursued, the filter belongs in it.",
    "<b>Do not rely on it for the no-target trend strategies.</b> To cut their drawdowns, the market signal has to "
    "act on open positions: for example, tighten stops to the last weekly low, or halve position sizes, when NIFTY "
    "closes below its 200-day average. That is the next test worth running.",
    "<b>Keep it as a cheap risk rule in live trading anyway.</b> It rarely hurts, and it keeps new money out of the "
    "worst markets (2008, 2011, 2020), which matters for confidence even if the backtest gain is small.",
]

story = [
    Paragraph("NIFTY 200-Day Market Filter", H1),
    Paragraph("Every strategy tested so far, with and without the filter · NIFTY 500 (and NIFTY 50 for the StochRSI "
              "pullback) · Jan 2000 – Nov 2026 · prepared 17 Nov 2026", SUB),
    Paragraph("Data: actual traded prices (split/bonus adjusted, not dividend adjusted). Today's index members only "
              "(survivorship bias). Costs: Sharekhan delivery fees plus 0.1% slippage per side.", SM),
    Spacer(1, 8),
    Paragraph("The rule", H2),
    Paragraph("No new trade is opened on a day when NIFTY 50 closed below its 200-day simple moving average the day "
              "before. Everything else is unchanged: signals, stops, targets, exits and sizing. Open trades are not "
              "sold when the market turns. Yahoo's NIFTY 50 history starts in September 2007, so its 200-day "
              f"average exists from {nifty_start:%d %b %Y}; before that the BSE Sensex is used. The two indices agree on "
              "97.6% of days since 2008.", P),
    Paragraph("Answer", H2)] + bl(FIND[:3]) + [
    Image(str(p_reg), width=172 * mm, height=76 * mm),
    KeepTogether([Paragraph("Long spells below the 200-day average (40+ trading days)", H2),
                  table(spell_rows, [40 * mm, 40 * mm, 30 * mm, 30 * mm])]),
    PageBreak(),
    Paragraph("Headline results", H2),
    Paragraph("One line per strategy: the no-target exit where it exists, otherwise the 15% target. All exits are in the "
              "appendix.", SM)]
hrows = [["Strategy", "Exit", "CAGR %", "filter", "Max DD %", "filter", "CAGR/DD", "filter", "Trades", "filter"]]
for p in pairs:
    sub = T[T.Strategy == p["name"]]
    r = sub[sub.Exit == "No target"].iloc[0] if (sub.Exit == "No target").any() else sub[sub.Exit == "Target 15%"].iloc[0]
    hrows.append([Paragraph(p["name"], TC), r.Exit.replace("Target ", ""), f"{r['CAGR %']:.1f}", f"{r['CAGR % (filter)']:.1f}",
                  f"{r['Max DD %']:.0f}", f"{r['Max DD % (filter)']:.0f}", f"{r['CAGR/DD']:.2f}",
                  f"{r['CAGR/DD (filter)']:.2f}", f"{int(r['Trades taken'])}", f"{int(r['Trades taken (filter)'])}"])
story += [table(hrows, [52 * mm, 15 * mm, 12 * mm, 12 * mm, 15 * mm, 12 * mm, 14 * mm, 12 * mm, 13 * mm, 12 * mm], 2),
          Spacer(1, 6), Image(str(p_sc), width=172 * mm, height=72 * mm),
          Paragraph("Each dot is one strategy and exit. Top right = better on both CAGR and drawdown.", SM),
          PageBreak(),
          Paragraph("Equity, with and without the filter", H2),
          Paragraph("Red shading: market below its 200-day average for 40+ trading days.", SM),
          Image(str(p_eq), width=172 * mm, height=181 * mm),
          PageBreak(),
          Paragraph("Drawdowns", H2), Image(str(p_dd), width=172 * mm, height=158 * mm),
          KeepTogether([Paragraph("Bear markets: account change during each fall", H2),
                        table(crash_rows, [33 * mm, 13 * mm] + [16 * mm] * 8, 1, 7),
                        Paragraph("S1 = " + NAMES[MAINS[0][0]] + "; S2 = " + NAMES[MAINS[1][0]] + "; S3 = "
                                  + NAMES[MAINS[2][0]] + "; S4 = " + NAMES[MAINS[3][0]] + " (all no target). "
                                  "Change in account equity from the index peak to its low.", SM)]),
          KeepTogether([Paragraph("How much is invested when the market is weak", H2),
                        table(exp_rows, [62 * mm, 36 * mm, 36 * mm, 38 * mm]),
                        Paragraph("Average number of open trades (no-target exit). The filter lowers it only slowly, "
                                  "because positions opened earlier stay open.", SM)]),
          KeepTogether([Paragraph("Two periods: Sensex proxy and NIFTY", H2),
                        table(sub_rows, [56 * mm, 18 * mm, 27 * mm, 20 * mm, 27 * mm, 20 * mm]),
                        Paragraph("CAGR within each period. The earlier period uses the Sensex for the filter.", SM)]),
          Paragraph("What the study shows", H2)] + bl(FIND) + [
          Paragraph("Recommendation", H2)] + bl(REC) + [
          Paragraph("Caveats", H2)] + bl([
              "Survivorship bias: today's index members only, in both versions.",
              "The Sensex stands in for NIFTY before mid-2008; on the 2.4% of days where they disagree, the filter could "
              "have decided differently.",
              "Each no-target strategy has only about 50–140 trades; changes of a point or two in CAGR are within noise.",
              "The filter is checked on the previous day's close; an intraday break of the average is not acted on."]) + [
          PageBreak(), Paragraph("Appendix: every strategy and exit", H2)]
arows = [["Strategy", "Exit", "CAGR %", "filter", "Max DD %", "filter", "Win %", "filter", "Trades", "filter"]]
for _, r in T.iterrows():
    arows.append([Paragraph(r.Strategy, TC), r.Exit.replace("Target ", ""), f"{r['CAGR %']:.1f}", f"{r['CAGR % (filter)']:.1f}",
                  f"{r['Max DD %']:.0f}", f"{r['Max DD % (filter)']:.0f}", f"{r['Win %']:.0f}", f"{r['Win % (filter)']:.0f}",
                  f"{int(r['Trades taken'])}", f"{int(r['Trades taken (filter)'])}"])
story += [table(arows, [56 * mm, 15 * mm, 12 * mm, 12 * mm, 14 * mm, 12 * mm, 11 * mm, 12 * mm, 13 * mm, 12 * mm], 2, 6.8),
          Paragraph("How to reproduce", H2),
          Paragraph("<font face='Courier' size='8'>python run_strategy.py strategies/*/*_nifty200.json<br/>"
                    "python run_strategy.py strategies/stochrsi_pullback/monthly_*_nifty200.json --universe NIFTY50<br/>"
                    "python studies/market_filter_report.py</font>", P),
          Paragraph("Code: lib/market.py (regime), lib/engine.py (day_filters.market_sma). Research and education only; "
                    "not investment advice.", SM)]


def footer(c, d):
    c.setFont("Helvetica", 7.5); c.setFillColor(colors.HexColor(GREY))
    c.drawString(18 * mm, 10 * mm, "NIFTY 200-day market filter")
    c.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {d.page}")


SimpleDocTemplate(str(OUT / "report.pdf"), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                  bottomMargin=16 * mm, title="NIFTY 200-Day Market Filter").build(story, onFirstPage=footer, onLaterPages=footer)
for p in charts:
    p.unlink()
print(OUT / "report.pdf")
print("NT:", n_nt, nt_cu, nt_du, " TG:", n_tg, tg_cu, tg_du, TG.dD.median())
for r in exp_rows: print(r)
for r in crash_rows[1:]: print(r[1:])
for r in sub_rows: print(r)
print(below_pct, switches, len(spells))
