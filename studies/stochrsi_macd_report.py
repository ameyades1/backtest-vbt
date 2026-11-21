"""MACD with the StochRSI pullback: monthly MACD gate, weekly MACD gate, MACD ranking.

    python run_strategy.py strategies/stochrsi_macd/*.json
    python studies/stochrsi_macd_funnel.py
    python studies/stochrsi_macd_report.py

Writes results/studies/stochrsi_macd/report.pdf (and compare.csv).
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
from lib import ids, portfolio
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak

OUT = ROOT / "results" / "studies" / "stochrsi_macd"
BLUE, GREY, DARK, RED, GREEN, AMBER = "#2563eb", "#64748b", "#0f172a", "#dc2626", "#15803d", "#d97706"
RUNS = {"Plain StochRSI": "stochrsi_pullback/monthly_prev_week_stop",
        "+ MACD": "stochrsi_macd/monthly_prev_week_stop",
        "+ MACD, no RSI filter": "stochrsi_macd/monthly_prev_week_stop_no_rsi",
        "+ MACD, 200-DMA filter": "stochrsi_macd/monthly_prev_week_stop_nifty200",
        "Plain, 200-DMA filter": "stochrsi_pullback/monthly_prev_week_stop_nifty200",
        "Weekly MACD": "stochrsi_macd/weekly_macd_prev_week_stop",
        "Weekly MACD, 200-DMA filter": "stochrsi_macd/weekly_macd_prev_week_stop_nifty200",
        "MACD ranking": "stochrsi_pullback/monthly_prev_week_stop_macd_rank",
        "MACD ranking, 200-DMA filter": "stochrsi_pullback/monthly_prev_week_stop_macd_rank_nifty200"}
COL = {"Plain StochRSI": "#94a3b8", "+ MACD": BLUE, "+ MACD, no RSI filter": AMBER,
       "+ MACD, 200-DMA filter": GREEN, "Plain, 200-DMA filter": "#475569", "Weekly MACD": "#9333ea",
       "Weekly MACD, 200-DMA filter": "#db2777", "MACD ranking": "#0891b2", "MACD ranking, 200-DMA filter": "#155e75"}
EXITS = ["No target", "Target 8%", "Target 15%", "Target 20%", "Target 30%"]
fid = lambda ex: "none" if ex == "No target" else ex.split()[1].rstrip("%")
folder = lambda k: ROOT / "results" / RUNS[k] / "nifty500"
summ = {k: pd.read_csv(folder(k) / "summary.csv", index_col=0) for k in RUNS}
eq = {k: pd.read_csv(folder(k) / "equity.csv", index_col=0, parse_dates=True) for k in RUNS}


def fills(k, ex):
    f = portfolio.read_fills(folder(k) / f"fills_{fid(ex)}.csv", parse_dates=["entry_date", "exit_date"])
    risk = (f.entry - f.stop) * f.qty
    f["R"] = (f.proceeds - f.cost) / risk
    f["pnl"] = f.proceeds - f.cost
    return f


def streak(f):
    w = (f.sort_values("exit_date").pnl > 0).to_numpy()
    best = cur = 0
    for x in w:
        cur = 0 if x else cur + 1; best = max(best, cur)
    return best


def underwater(e):
    """Longest stretch below a previous equity high, in years."""
    peak = e.cummax(); best, start = 0, None
    for d, v in (e < peak).items():
        if v and start is None: start = d
        if not v and start is not None:
            best = max(best, (d - start).days); start = None
    if start is not None: best = max(best, (e.index[-1] - start).days)
    return best / 365.25


def cagr(e, s, t):
    e = e[s:t].dropna()
    yrs = (e.index[-1] - e.index[0]).days / 365.25
    return ((e.iloc[-1] / e.iloc[0]) ** (1 / yrs) - 1) * 100


def mdd(e):
    return ((e / e.cummax()) - 1).min() * 100


rows = []
for k in RUNS:
    for ex in EXITS:
        s, f, e = summ[k].loc[ex], fills(k, ex), eq[k][ex].dropna()
        rows.append({"Version": k, "Exit": ex, "CAGR %": s["CAGR %"], "Max DD %": s["Max DD %"],
                     "Trades": int(s["Trades taken"]), "Win %": s["Win %"], "Avg R": f.R.mean(), "Median R": f.R.median(),
                     "Loss streak": streak(f), "Underwater yrs": underwater(e), "Avg open (of 8)": s["Avg open positions"],
                     "Median stop %": s["Median stop %"], "Avg hold days": s["Avg hold days"],
                     "CAGR 2000-12": cagr(e, "2000", "2012"), "CAGR 2013-26": cagr(e, "2013", None),
                     "Trades 2000-12": int((f.entry_date < "2013").sum()), "Trades 2013-26": int((f.entry_date >= "2013").sum())})
C = pd.DataFrame(rows)
C.to_csv(OUT / "compare.csv", index=False)
g = lambda k, ex, c: C[(C.Version == k) & (C.Exit == ex)][c].iloc[0]

funnel = pd.read_csv(OUT / "funnel.csv", index_col=0).iloc[:, 0]
delay = pd.read_csv(OUT / "delay.csv", parse_dates=["month"])
yearly = delay.groupby(delay.month.dt.year).size()

# ---------------- charts ----------------
charts = []


def style(ax):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=GREY, length=0, labelsize=7.5)
    ax.grid(axis="y", color="#e2e8f0", zorder=0)


def save(fig, name):
    p = OUT / f"_{name}.png"; fig.tight_layout(); fig.savefig(p); plt.close(fig); charts.append(p); return p


fig, axs = plt.subplots(2, 1, figsize=(7.2, 5.6), dpi=200, sharex=True, gridspec_kw={"height_ratios": [3, 2]})
for k in ["Plain StochRSI", "+ MACD", "Weekly MACD", "Weekly MACD, 200-DMA filter", "MACD ranking"]:
    e = eq[k]["No target"].dropna()
    axs[0].plot(e.index, e / 1e5, color=COL[k], lw=1.3, label=k)
    axs[1].plot(e.index, (e / e.cummax() - 1) * 100, color=COL[k], lw=1)
axs[0].set_yscale("log"); axs[0].yaxis.set_major_formatter(lambda v, _: f"{v:g}L")
axs[0].legend(frameon=False, fontsize=7, loc="upper left")
axs[0].set_title("Equity, no-target exit (Rs lakh, log scale)", loc="left", fontsize=10, fontweight="bold", color=DARK)
axs[1].yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
axs[1].set_title("Drawdown", loc="left", fontsize=9, fontweight="bold", color=DARK)
style(axs[0]); style(axs[1]); p_eq = save(fig, "equity")

fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.6), dpi=200)
dc = delay.delay_months.value_counts().sort_index()
axs[0].bar(dc.index, dc.values, color=BLUE, zorder=3)
axs[0].set_xticks(range(4)); axs[0].set_xlabel("Months from StochRSI cross to MACD cross", fontsize=7, color=GREY)
axs[0].set_title("Entry delay", loc="left", fontsize=9, fontweight="bold", color=DARK)
yr = yearly.reindex(range(2000, 2027), fill_value=0)
axs[1].bar(yr.index, yr.values, color=BLUE, zorder=3)
axs[1].set_title("Signals per year (all 499 stocks)", loc="left", fontsize=9, fontweight="bold", color=DARK)
style(axs[0]); style(axs[1]); p_dl = save(fig, "delay")

fig, ax = plt.subplots(figsize=(7.2, 2.6), dpi=200)
bins = np.arange(-1.6, 10.1, .4)
for k in ["Plain StochRSI", "+ MACD"]:
    r = fills(k, "Target 30%").R.clip(-1.6, 10)
    ax.hist(r, bins=bins, color=COL[k], alpha=.65, density=True, label=f"{k} ({len(r)} trades)", zorder=3)
ax.legend(frameon=False, fontsize=7); ax.set_xlabel("Trade result in R (multiples of the risk taken), 30% target",
                                                    fontsize=7, color=GREY)
ax.set_title("Per-trade results", loc="left", fontsize=9, fontweight="bold", color=DARK)
style(ax); p_r = save(fig, "rdist")

# ---------------- PDF ----------------
ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=17, leading=21, alignment=0, textColor=colors.HexColor(DARK), spaceAfter=2)
SUB = ParagraphStyle("SUB", parent=ss["Normal"], fontSize=9, textColor=colors.HexColor(GREY))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12.5, textColor=colors.HexColor(DARK), spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("P", parent=ss["Normal"], fontSize=9.5, leading=13.5, spaceAfter=4)
BL = ParagraphStyle("BL", parent=P, leftIndent=10, spaceAfter=2)
SM = ParagraphStyle("SM", parent=P, fontSize=8, leading=10.5, textColor=colors.HexColor(GREY))
bl = lambda xs: [Paragraph(x, BL, bulletText="•") for x in xs]


def table(rows, widths, num_from=1, fs=7.5):
    tb = Table(rows, colWidths=widths, repeatRows=1)
    tb.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", fs), ("FONT", (0, 1), (-1, -1), "Helvetica", fs),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(DARK)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("ALIGN", (num_from, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))
    return tb


P0, M0, MN = "Plain StochRSI", "+ MACD", "+ MACD, no RSI filter"
WK, WF, RK, RF = "Weekly MACD", "Weekly MACD, 200-DMA filter", "MACD ranking", "MACD ranking, 200-DMA filter"
_a, _b = fills(P0, "No target"), fills(RK, "No target")
_w = fills(WF, "No target")
top5 = _w.pnl.nlargest(5).sum() / _w.pnl.sum() * 100
same = len(set(zip(_a.symbol, _a.entry_date)) & set(zip(_b.symbol, _b.entry_date)))
nt = lambda k, c: g(k, "No target", c)
FIND = [
    f"<b>The MACD confirmation finds very few trades.</b> Across 499 stocks and 26 years it gives "
    f"{int(funnel.iloc[7])} monthly signals, against {int(funnel.iloc[8])} for the plain StochRSI pullback. Only "
    f"{int(nt(M0, 'Trades'))}–{int(g(M0, 'Target 15%', 'Trades'))} trades are taken, about 3 a year. That is too few "
    f"to judge with confidence; one or two big winners decide the whole result.",
    f"<b>The RSI &gt; 50 filter is not the cause.</b> Removing it adds only "
    f"{int(funnel.iloc[6] - funnel.iloc[7])} signals. The binding conditions are the MACD crossing up while still "
    f"below zero ({int(funnel.iloc[3])} times in {int(funnel.iloc[0]):,} monthly candles) and, at that moment, a "
    f"close above the monthly EMA61 (cuts {int(funnel.iloc[4])} to {int(funnel.iloc[5])}). A monthly MACD below zero "
    f"usually means price is still below its long-term average, which our trend filter rejects.",
    f"<b>Each trade is better.</b> Win rate rises from {nt(P0, 'Win %'):.0f}% to {nt(M0, 'Win %'):.0f}% (no target) "
    f"and from {g(P0, 'Target 15%', 'Win %'):.0f}% to {g(M0, 'Target 15%', 'Win %'):.0f}% (15% target). Average R per "
    f"trade with a 30% target goes from {g(P0, 'Target 30%', 'Avg R'):.2f} to {g(M0, 'Target 30%', 'Avg R'):.2f}. "
    f"The confirmation does filter out weaker setups. With no target, average R is lower ({nt(M0, 'Avg R'):.1f} against "
    f"{nt(P0, 'Avg R'):.1f}) because the plain strategy holds a few huge multi-year winners; the median trade is the same.",
    f"<b>The two periods disagree.</b> The plain strategy's lead comes from 2000–2012 ({nt(P0, 'CAGR 2000-12'):.1f}% "
    f"against {nt(M0, 'CAGR 2000-12'):.1f}%, with only {nt(M0, 'Trades 2000-12')} MACD trades). From 2013 the MACD "
    f"version did better: {nt(M0, 'CAGR 2013-26'):.1f}% against {nt(P0, 'CAGR 2013-26'):.1f}%, with a shorter longest "
    f"time below an equity high ({nt(M0, 'Underwater yrs'):.1f} against {nt(P0, 'Underwater yrs'):.1f} years over the "
    f"full test). With 42 trades that may be luck, but it is the reason not to dismiss the idea.",
    f"<b>The account is worse.</b> No-target CAGR falls from {nt(P0, 'CAGR %'):.1f}% to {nt(M0, 'CAGR %'):.1f}% "
    f"because on average only {nt(M0, 'Avg open (of 8)'):.1f} of 8 slots are in use (plain: "
    f"{nt(P0, 'Avg open (of 8)'):.1f}). Drawdown improves only a little ({nt(P0, 'Max DD %'):.0f}% to "
    f"{nt(M0, 'Max DD %'):.0f}%), and without the RSI filter {nt(MN, 'Max DD %'):.0f}%. With fixed targets the "
    f"account is almost always in cash and earns 0–1.5% a year.",
    f"<b>Entries come later and stops are wider.</b> The MACD cross comes {delay.delay_months.median():.0f} months "
    f"(median) after the StochRSI cross, so price has moved off the low. Median stop distance widens from "
    f"{nt(P0, 'Median stop %'):.1f}% to {nt(M0, 'Median stop %'):.1f}%, which means smaller positions for the same 1% risk.",
    f"<b>The 200-day market filter changes little here</b> (no target {nt(M0, 'CAGR %'):.1f}% / "
    f"{nt(M0, 'Max DD %'):.0f}% to {nt('+ MACD, 200-DMA filter', 'CAGR %'):.1f}% / "
    f"{nt('+ MACD, 200-DMA filter', 'Max DD %'):.0f}%): the MACD condition already avoids most entries in weak markets.",
]
FIND2 = [
    f"<b>MACD ranking changes almost nothing.</b> It keeps the same signals and only reorders them when slots are "
    f"short. {same} of the {int(nt(P0, 'Trades'))} no-target trades are identical. CAGR {nt(RK, 'CAGR %'):.1f}% "
    f"against {nt(P0, 'CAGR %'):.1f}%, drawdown {nt(RK, 'Max DD %'):.0f}% against {nt(P0, 'Max DD %'):.0f}%; with "
    f"fixed targets it is better in some, worse in others. That is noise, the same as the slot-ranking study found for "
    f"every rule except 12-month return and trend strength.",
    f"<b>Weekly MACD confirmation is the most interesting result, but it rests on few trades.</b> No target: "
    f"{nt(WK, 'CAGR %'):.1f}% / {nt(WK, 'Max DD %'):.0f}% alone, and {nt(WF, 'CAGR %'):.1f}% / "
    f"{nt(WF, 'Max DD %'):.0f}% with the 200-day market filter, from only {int(nt(WF, 'Trades'))} trades. The filtered "
    f"version has the best CAGR-to-drawdown of anything tested so far (plain strategy {nt(P0, 'CAGR %'):.1f}% / "
    f"{nt(P0, 'Max DD %'):.0f}%). Win rate is low ({nt(WF, 'Win %'):.0f}%): a few long trends pay for many small stops.",
    f"<b>Why the market filter matters so much here:</b> weekly MACD crosses below zero fire often during bear-market "
    f"rallies. Without the filter the drawdown is {nt(WK, 'Max DD %'):.0f}%; with it {nt(WF, 'Max DD %'):.0f}%. With "
    f"fixed targets the weekly version loses money (about 0% to −1.5% CAGR) and should be ignored.",
    f"<b>Periods:</b> weekly MACD with the filter made {nt(WF, 'CAGR 2000-12'):.1f}% in 2000–12 and "
    f"{nt(WF, 'CAGR 2013-26'):.1f}% in 2013–26 (plain: {nt(P0, 'CAGR 2000-12'):.1f}% and {nt(P0, 'CAGR 2013-26'):.1f}%). "
    f"<b>It is not steady.</b> Almost all of the return comes after 2013; before that it was close to flat. The plain "
    f"strategy is the mirror image. Top 5 trades: {top5:.0f}% of the weekly version's net profit. A strategy that "
    f"depends on one period and a handful of winners is fragile.",
]
REC = [
    f"<b>Weekly MACD with the 200-day filter is worth a closer look, not live money.</b> {int(nt(WF, 'Trades'))} "
    f"trades in 26 years is too few. Next: run it on other universes (NIFTY 50, Midcap 150) and check how many of its "
    f"why it did nothing before 2013. If it holds, a paper-trading log is the next step.",
    "<b>Drop MACD ranking.</b> If slot ranking is pursued, use 12-month return (slot-ranking study).",
    "<b>Do not replace the current strategy with this one.</b> The edge per trade is real but there are not enough "
    "trades to use the capital, and 59–78 trades are too few to trust.",
    "<b>Possible use: as a ranking or sizing signal, not a gate.</b> When several plain StochRSI signals compete for a "
    "slot, prefer the ones where the monthly MACD is turning up below zero, or give them a larger risk (for example "
    "1.25% instead of 1%). That keeps the trade count and uses the better win rate.",
    "Do not loosen the conditions (window length, MACD settings) until it 'works'; with this few trades any tuning "
    "would just fit the past.",
]

def mrow(k, ex):
    r = C[(C.Version == k) & (C.Exit == ex)].iloc[0]
    return [k, ex.replace("Target ", ""), f"{r['CAGR %']:.1f}", f"{r['Max DD %']:.0f}", f"{r.Trades}", f"{r['Win %']:.0f}",
            f"{r['Avg R']:.2f}", f"{r['Loss streak']}", f"{r['Underwater yrs']:.1f}", f"{r['Avg open (of 8)']:.1f}"]

HDR = ["Version", "Exit", "CAGR %", "Max DD %", "Trades", "Win %", "Avg R", "Loss streak", "Underwater yrs", "Avg open"]
W = [46 * mm, 15 * mm, 13 * mm, 15 * mm, 13 * mm, 12 * mm, 13 * mm, 15 * mm, 19 * mm, 14 * mm]
head_rows = [HDR] + [mrow(k, "No target") for k in RUNS]
all_rows = [HDR] + [mrow(k, ex) for ex in EXITS for k in RUNS if ex != "No target"]
fun_rows = [["Condition (monthly candles, 2000 onwards, 499 stocks)", "Candles"]] + \
           [[i, f"{int(v):,}"] for i, v in funnel.items()]
per_rows = [["Version", "Exit", "CAGR 2000–12", "Trades", "CAGR 2013–26", "Trades"]] + \
           [[k, ex.replace("Target ", ""), f"{g(k, ex, 'CAGR 2000-12'):.1f}%", f"{g(k, ex, 'Trades 2000-12')}",
             f"{g(k, ex, 'CAGR 2013-26'):.1f}%", f"{g(k, ex, 'Trades 2013-26')}"]
            for k in [P0, M0, MN, "Weekly MACD", "Weekly MACD, 200-DMA filter", "MACD ranking"] for ex in ["No target", "Target 30%"]]
tf = fills(M0, "No target").sort_values("entry_date")
trade_rows = [["Stock", "Entry", "Exit", "Entry Rs", "Exit Rs", "Stop %", "R"]] + \
             [[r.symbol.replace(".NS", ""), f"{r.entry_date:%d %b %Y}",
               "open" if pd.isna(r.exit_date) else f"{r.exit_date:%d %b %Y}", f"{r.entry:,.1f}", f"{r.exit:,.1f}",
               f"{(r.entry - r.stop) / r.entry * 100:.1f}", f"{r.R:+.1f}"] for r in tf.itertuples()]

story = [
    Paragraph("MACD with the StochRSI Pullback", H1),
    Paragraph("NIFTY 500 · 2000 to 2026 · 1% risk per trade · 8 slots · Sharekhan delivery costs + 0.1% slippage per side", SUB),
    Paragraph("Data: actual traded prices (split/bonus adjusted, not dividend adjusted). Today's index members only, so "
              "results carry survivorship bias. Research, not financial advice.", SM),
    Paragraph("The rule tested", H2)] + bl([
    "<b>Monthly StochRSI (14,14,3,3)</b>: %K crosses above %D with %D below 30. Same as the current strategy.",
    "<b>Monthly MACD (12,26,9)</b> crosses above its signal line <b>while the MACD line is below zero</b>, in the same "
    "month as the StochRSI cross or within the next 3 months. The month of the MACD cross is the signal month.",
    "<b>Filters at the signal month</b>: close above EMA61 on the monthly (last completed month), weekly and daily "
    "charts, and monthly RSI(14) above 50. A second version drops the RSI filter.",
    "<b>Entry</b>: buy-stop above the signal month's high, valid the next month. <b>Stop</b>: previous week's low. "
    "<b>Exits</b>: no target (monthly close below EMA61) or targets of 8, 15, 20, 30%.",
    "The monthly-MACD-above-zero condition from the first proposal was dropped: it contradicts a cross below zero on the "
    "same chart.",
    "<b>Weekly MACD version</b>: the monthly StochRSI cross (completed month) sets up; the trigger is a <b>weekly</b> MACD "
    "cross above its signal line below zero within 13 weeks of that month's end. Buy-stop above that week's high for one "
    "week. Monthly RSI &gt; 50, EMA61 on monthly/weekly/daily, previous-week-low stop, no-target exit on a monthly "
    "close below EMA61: all the same as the current strategy.",
    "<b>MACD ranking version</b>: the current strategy's signals unchanged. When more signals arrive than free slots, "
    "take first those whose monthly MACD histogram is rising while MACD is below zero, then those rising above zero, "
    "then the rest; ties by tightest stop (the current rule)."]) + [
    Paragraph("Answer", H2)] + bl([FIND2[1], FIND2[0], FIND[0], FIND[4]]) + [
    Paragraph("Headline: no-target exit", H2),
    table(head_rows, W, num_from=1, fs=7),
    Paragraph("Avg R = average trade result as a multiple of the money risked (net of costs). Loss streak = most losing "
              "trades in a row. Underwater yrs = longest time below a previous equity high.", SM),
    Image(str(p_eq), width=172 * mm, height=134 * mm),
    KeepTogether([Paragraph("Where the signals go: the funnel", H2), table(fun_rows, [130 * mm, 25 * mm], fs=7.5),
                  Paragraph("Each line adds one condition to the line above (lines 2–4 are counted alone). The last line is "
                            "the current strategy for scale.", SM)]),
    KeepTogether([Paragraph("Entry timing", H2), Image(str(p_dl), width=172 * mm, height=62 * mm),
                  Paragraph(f"Median stop distance: plain {nt(P0, 'Median stop %'):.1f}%, with MACD "
                            f"{nt(M0, 'Median stop %'):.1f}%. Average close above the monthly EMA61 at the signal: "
                            f"{delay.close_vs_ema61_pct.mean():.1f}%.", SM)]),
    KeepTogether([Paragraph("Per-trade quality", H2), Image(str(p_r), width=172 * mm, height=62 * mm)]),
    KeepTogether([Paragraph("All fixed-target exits", H2), table(all_rows, W, num_from=1, fs=7)]),
    KeepTogether([Paragraph("Two periods", H2), table(per_rows, [42 * mm, 18 * mm, 24 * mm, 16 * mm, 24 * mm, 16 * mm]),
                  Paragraph("Each period on its own, using the same equity curve. With 20–40 trades per period, "
                            "differences are mostly luck.", SM)]),
    Paragraph("What the study shows", H2), Paragraph("Monthly MACD gate", P)] + bl(FIND) + [
    Paragraph("Weekly MACD gate and MACD ranking", P)] + bl(FIND2) + [
    Paragraph("Recommendation", H2)] + bl(REC) + [
    PageBreak(), Paragraph("Appendix: every trade, StochRSI + MACD, no-target exit", H2),
    table(trade_rows, [32 * mm, 24 * mm, 24 * mm, 22 * mm, 22 * mm, 16 * mm, 14 * mm], num_from=3, fs=7)]

story += ids.pdf_section(list(RUNS.values()), H2)
SimpleDocTemplate(str(OUT / "report.pdf"), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                  bottomMargin=16 * mm, title="MACD with the StochRSI pullback").build(story)
for p in charts:
    p.unlink()
print(OUT / "report.pdf")
print(C[C.Exit.isin(["No target", "Target 30%"])].round(2).to_string())
