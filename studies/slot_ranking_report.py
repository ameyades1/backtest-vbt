"""Build results/studies/slot_ranking/report.pdf from studies/slot_ranking.py output."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from lib import ids
import lib.pdffont  # noqa: F401  (DejaVu glyphs for ₹ and −)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, PageBreak

D = ROOT / "results" / "studies" / "slot_ranking"
OUT = D / "report.pdf"
R = pd.read_csv(D / "rules.csv")
X = pd.read_csv(D / "random.csv")
EQ = pd.read_csv(D / "equity_main.csv", index_col=0, parse_dates=True)
MAIN = "StochRSI pullback, prev-week stop"
CUR = "Tightest stop (current)"
BLUE, GREY, DARK, RED, GREEN, LIGHT = "#2563eb", "#64748b", "#0f172a", "#dc2626", "#15803d", "#cbd5e1"
PAL = {"Tightest stop (current)": DARK, "Widest stop": "#a855f7", "6-month return": "#2563eb",
       "12-month return": "#0891b2", "Trend strength": "#16a34a", "Liquidity": "#ea580c", "Low volatility": "#db2777"}


def pct(strategy, v, col="CAGR %"):
    x = X.loc[X.Strategy == strategy, col]
    return (x < v).mean() * 100


R["CAGR pct vs random"] = [pct(s, v) for s, v in zip(R.Strategy, R["CAGR %"])]
R["DD pct vs random"] = [pct(s, v, "Max DD %") for s, v in zip(R.Strategy, R["Max DD %"])]   # higher = shallower
m = R[R.Strategy == MAIN]
mn = m[m["Sector cap"] == "none"].set_index("Rule")
mc = m[m["Sector cap"] != "none"].set_index("Rule")
xm = X[X.Strategy == MAIN]
q = xm["CAGR %"].quantile([.05, .25, .5, .75, .95])
qd = xm["Max DD %"].quantile([.05, .5, .95])
cur = mn.loc[CUR]
best = mn["CAGR %"].idxmax()
best_mar = mn["CAGR/DD"].idxmax()
nr = len(xm)


def style(ax):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=GREY, length=0, labelsize=8)
    ax.grid(axis="y", color="#e2e8f0", zorder=0)


charts = []


def save(fig, name):
    p = D / f"_{name}.png"; fig.tight_layout(); fig.savefig(p); plt.close(fig); charts.append(p); return p


fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=200)
ax.hist(xm["CAGR %"], bins=30, color=LIGHT, zorder=2, label=f"{nr} random rankings")
for rule, r in mn.iterrows():
    ax.axvline(r["CAGR %"], color=PAL[rule], lw=1.6, zorder=3, label=f"{rule}: {r['CAGR %']:.1f}%")
ax.xaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax.legend(frameon=False, fontsize=6.8, loc="upper left")
ax.set_title("CAGR: each ranking rule against luck alone", loc="left", fontsize=10.5, fontweight="bold", color=DARK)
ax.set_ylabel("Random runs", color=GREY, fontsize=8)
p_hist = save(fig, "hist")

fig, ax = plt.subplots(figsize=(7.2, 3.4), dpi=200)
ax.scatter(-xm["Max DD %"], xm["CAGR %"], s=8, color=LIGHT, zorder=2, label="Random rankings")
for rule, r in mn.iterrows():
    ax.scatter(-r["Max DD %"], r["CAGR %"], s=46, color=PAL[rule], zorder=3, label=rule, edgecolor="white")
for rule, r in mc.iterrows():
    ax.scatter(-r["Max DD %"], r["CAGR %"], s=46, color=PAL[rule], marker="D", zorder=3, edgecolor="white")
ax.set_xlabel("Max drawdown (%)  — further right is worse", color=GREY, fontsize=8)
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%"); ax.xaxis.set_major_formatter(lambda v, _: f"-{v:.0f}%")
ax.legend(frameon=False, fontsize=6.8, loc="lower right", ncol=2)
ax.set_title("Return against drawdown (circles: no cap, diamonds: 2-per-sector cap)", loc="left",
             fontsize=10.5, fontweight="bold", color=DARK)
style(ax); p_sc = save(fig, "scatter")

fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=200)
for rule in RULES if (RULES := list(mn.index)) else []:
    e = EQ[rule].dropna()
    ax.plot(e.index, e / 1e5, color=PAL[rule], lw=1.9 if rule in (CUR, best) else 1.0,
            alpha=1 if rule in (CUR, best) else .7, label=rule)
ax.set_yscale("log"); ax.yaxis.set_major_formatter(lambda v, _: f"Rs {v:g}L")
ax.legend(frameon=False, fontsize=7, loc="upper left", ncol=2)
ax.set_title("Equity by ranking rule (no sector cap)", loc="left", fontsize=10.5, fontweight="bold", color=DARK)
style(ax); p_eq = save(fig, "equity")

fig, ax = plt.subplots(figsize=(7.2, 2.8), dpi=200)
for rule in [CUR, best] if best != CUR else [CUR]:
    e = EQ[rule].dropna()
    ax.plot(e.index, (e / e.cummax() - 1) * 100, color=PAL[rule], lw=1.4, label=rule)
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax.legend(frameon=False, fontsize=8, loc="lower left")
ax.set_title("Drawdown: current rule against the highest-CAGR rule", loc="left", fontsize=10.5, fontweight="bold", color=DARK)
style(ax); p_dd = save(fig, "dd")

strats = list(dict.fromkeys(R.Strategy))
fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=200)
w = 0.11
for i, rule in enumerate(PAL):
    v = [R[(R.Strategy == s) & (R.Rule == rule) & (R["Sector cap"] == "none")]["CAGR %"].iat[0] for s in strats]
    ax.bar(np.arange(len(strats)) + (i - 3) * w, v, w, color=PAL[rule], label=rule, zorder=2)
for j, s in enumerate(strats):
    x = X.loc[X.Strategy == s, "CAGR %"]
    ax.plot([j - .42, j + .42], [x.median()] * 2, color=RED, lw=1.2, ls="--", zorder=3)
    ax.fill_between([j - .42, j + .42], x.quantile(.05), x.quantile(.95), color=RED, alpha=.08, zorder=1)
ax.set_xticks(range(len(strats)), [s.replace(", ", "\n") for s in strats], fontsize=7.5)
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax.legend(frameon=False, fontsize=6.5, loc="upper right", ncol=2)
ax.set_title("Same rules on three strategies (red: random median and 5–95% band)", loc="left",
             fontsize=10.5, fontweight="bold", color=DARK)
style(ax); p_rob = save(fig, "robust")

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=17, leading=21, alignment=0, textColor=colors.HexColor(DARK), spaceAfter=2)
SUB = ParagraphStyle("SUB", parent=ss["Normal"], fontSize=9, textColor=colors.HexColor(GREY))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12.5, textColor=colors.HexColor(DARK), spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("P", parent=ss["Normal"], fontSize=9.5, leading=13.5, spaceAfter=4)
BL = ParagraphStyle("BL", parent=P, leftIndent=10, spaceAfter=2)
SM = ParagraphStyle("SM", parent=P, fontSize=8, leading=10.5, textColor=colors.HexColor(GREY))
TC = ParagraphStyle("TC", parent=SM, textColor=colors.HexColor(DARK))


def table(rows, widths, num_from=1):
    tb = Table(rows, colWidths=widths, repeatRows=1)
    tb.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.6), ("FONT", (0, 1), (-1, -1), "Helvetica", 7.6),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(DARK)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("ALIGN", (num_from, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return tb


bl = lambda xs: [Paragraph(x, BL, bulletText="•") for x in xs]


def g(strategy, rule, cap="none"):
    return R[(R.Strategy == strategy) & (R.Rule == rule) & ((R["Sector cap"] == "none") == (cap == "none"))].iloc[0]


C2 = "StochRSI pullback, candle-low stop"; BR = "EMA61 breakout, candle-low stop"
m12, tsn = mn.loc["12-month return"], mn.loc["Trend strength"]
c12, ctr, ccur = g(C2, "12-month return"), g(C2, "Trend strength"), g(C2, CUR)
b12, bcur, bliq = g(BR, "12-month return"), g(BR, CUR), g(BR, "Liquidity")
xb = X[X.Strategy == BR]["CAGR %"]
capd = mc["CAGR %"] - mn["CAGR %"]
FINDINGS = [
    f"<b>The ranking rule matters much less than expected.</b> {nr} random rankings of the main strategy give a CAGR "
    f"between {q[.05]:.1f}% and {q[.95]:.1f}% (90% of runs), median {q[.5]:.1f}%. The current tightest-stop rule "
    f"({cur['CAGR %']:.1f}%) sits at the {cur['CAGR pct vs random']:.0f}th percentile: no better than luck. The narrow spread suggests most "
    f"skipped signals arrive when no slot is free at all, so ranking only chooses between the few signals that "
    f"arrive on a day when a slot opens.",
    f"<b>Momentum ranking is the one consistent improvement on the pullback strategies.</b> Ranking by 12-month "
    f"return gives {m12['CAGR %']:.1f}% (beats {m12['CAGR pct vs random']:.0f}% of random runs) and trend strength "
    f"{tsn['CAGR %']:.1f}% ({tsn['CAGR pct vs random']:.0f}%), against {cur['CAGR %']:.1f}% today, with a drawdown no "
    f"worse ({m12['Max DD %']:.0f}%). On the candle-low version they give {c12['CAGR %']:.1f}% and "
    f"{ctr['CAGR %']:.1f}% against {ccur['CAGR %']:.1f}%. The gain is real but small: under 1 point a year.",
    f"<b>A 2-per-sector cap does not help at 8 slots.</b> On the main strategy it changed CAGR by "
    f"{capd.min():+.1f} to {capd.max():+.1f} points and deepened most drawdowns to about "
    f"{mc['Max DD %'].median():.0f}%. Without a cap the most traded industry already holds only "
    f"{mn['Top sector share %'].min():.0f}–{mn['Top sector share %'].max():.0f}% of trades, so there is little "
    f"concentration to remove.",
    f"<b>Stop size carries no edge.</b> Widest-stop-first ({mn.loc['Widest stop', 'CAGR %']:.1f}%) does as well as "
    f"tightest-stop-first ({cur['CAGR %']:.1f}%). Taking the largest positions first was never an advantage.",
    f"<b>The EMA61 breakout does not follow the pattern.</b> Its random spread is wider ({xb.quantile(.05):.1f}% to "
    f"{xb.quantile(.95):.1f}%) and the current rule sits at the {bcur['CAGR pct vs random']:.0f}th percentile. "
    f"12-month return gives {b12['CAGR %']:.1f}% (only the {b12['CAGR pct vs random']:.0f}th percentile) but cuts the "
    f"drawdown from {bcur['Max DD %']:.0f}% to {b12['Max DD %']:.0f}%; liquidity gives {bliq['CAGR %']:.1f}% with "
    f"{bliq['Max DD %']:.0f}%. No rule wins on all three strategies by a margin larger than luck.",
    f"<b>A few trades still decide everything.</b> The single best trade makes "
    f"{mn['Best trade share of P&L %'].min():.0f}–{mn['Best trade share of P&L %'].max():.0f}% of total profit in the "
    f"main strategy, whichever rule is used. Missing or catching one such trend matters more than any ranking.",
]
RECOMMEND = [
    "<b>Use 12-month return as the default ranking</b> for the pullback strategies. It is simple, matches the "
    "trend-following idea, never made results worse here, and ranks near the top of the random runs. Treat it as "
    "a small tilt, not a new edge.",
    "<b>Do not add a sector cap</b> at 8 slots. Revisit it if the number of slots grows.",
    "<b>Spend the next effort elsewhere.</b> Exits (how much profit is given back before the monthly EMA61 exit) "
    "and a market filter (no new entries when NIFTY is below its 200-day average) can move results far more than "
    "slot ranking.",
    "<b>Before adopting momentum ranking,</b> check it on 2000–2012 and 2013–2026 separately.",
]

story = [
    Paragraph("Filling the Slots: Which Signals to Take", H1),
    Paragraph("Rs 1,00,000 · 1% risk per trade · 8 slots · NIFTY 500 (499 stocks) · Jan 2000 – Nov 2026 · "
              "no-target versions · prepared 17 Nov 2026", SUB),
    Paragraph("Data: actual traded prices (split/bonus adjusted, not dividend adjusted). Today's index members only "
              "(survivorship bias). Costs: Sharekhan delivery fees plus 0.1% slippage per side.", SM),
    Spacer(1, 8),
    Paragraph("Question", H2),
    Paragraph(f"The monthly strategies produce far more signals than 8 slots can hold. In the main strategy "
              f"(Stochastic RSI pullback, previous-week stop) {int(cur['Trades'])} trades were taken and "
              f"{int(cur['Skipped']):,} signals skipped. The rule that decides which signals get a slot may matter "
              f"as much as the signal itself. This study tests seven ranking rules, a sector cap, and "
              f"{nr} random rankings that show what luck alone does.", P),
    Paragraph("Answer", H2),
] + bl(FINDINGS[:3]) + [
    Paragraph("How slots are filled today", H2),
    Paragraph("Each trading day, in order: (1) exits close and free their slots and cash; (2) that day's new "
              "signals are ranked; (3) they fill free slots in rank order. A signal that finds no free slot is "
              "skipped for good: it does not wait, and an open trade is never swapped out for a better one. Each "
              "position risks Rs 1,000, so its size is Rs 1,000 ÷ stop distance, cut if cash runs short. Monthly "
              "signals bunch in the first days of a month, so ranking decides most of the portfolio.", P),
    Paragraph("Rules tested", H2),
    table([["Rule", "Takes first"],
           [CUR, Paragraph("Smallest stop distance as % of entry (largest positions). The rule used in every "
                           "result so far.", TC)],
           ["Widest stop", Paragraph("Largest stop distance first. A check: if it does as well, ranking hardly matters.", TC)],
           ["6-month return", Paragraph("Highest return over the last 126 trading days (relative strength; ranking "
                                        "by return against NIFTY gives the same order).", TC)],
           ["12-month return", Paragraph("Highest return over the last 252 trading days.", TC)],
           ["Trend strength", Paragraph("Furthest above its monthly EMA61 (last completed month).", TC)],
           ["Liquidity", Paragraph("Highest 20-day average traded value (Rs).", TC)],
           ["Low volatility", Paragraph("Lowest 14-day ATR as % of price.", TC)],
           ["Random", Paragraph(f"Random order, {nr} seeds for the main strategy and {len(X[X.Strategy != MAIN]) // 2} "
                                f"for each of the others. Shows the spread due to luck.", TC)],
           ["+ sector cap", Paragraph("Any rule above, with at most 2 open positions per NSE industry "
                                      "(signals over the cap are skipped).", TC)]],
          [32 * mm, 142 * mm], num_from=9),
    Paragraph("All scores use prices up to the day before entry, so no future data is used.", SM),
    PageBreak(),
    Paragraph("Main strategy: rules against luck", H2),
    Paragraph(f"The {nr} random rankings give a median CAGR of <b>{q[.5]:.1f}%</b>; 90% of them fall between "
              f"{q[.05]:.1f}% and {q[.95]:.1f}%. Median max drawdown is {qd[.5]:.0f}% "
              f"(5–95%: {qd[.05]:.0f}% to {qd[.95]:.0f}%). This spread comes only from which signals got a slot.", P),
    Image(str(p_hist), width=172 * mm, height=76 * mm),
    Image(str(p_sc), width=172 * mm, height=81 * mm),
]
rows = [["Rule", "Cap", "CAGR %", "Beats random", "Max DD %", "DD better than", "CAGR/DD", "Win %", "Trades",
         "Skipped", "Top sector %"]]
for _, r in m.iterrows():
    rows.append([r.Rule, "2/sector" if r["Sector cap"] != "none" else "–", f"{r['CAGR %']:.1f}",
                 f"{r['CAGR pct vs random']:.0f}%", f"{r['Max DD %']:.0f}", f"{r['DD pct vs random']:.0f}%",
                 f"{r['CAGR/DD']:.2f}", f"{r['Win %']:.0f}", f"{int(r.Trades)}", f"{int(r.Skipped):,}",
                 f"{r['Top sector share %']:.0f}"])
story += [KeepTogether([Paragraph("Full results, main strategy", H2),
                        table(rows, [34 * mm, 14 * mm, 13 * mm, 17 * mm, 15 * mm, 18 * mm, 14 * mm, 11 * mm, 12 * mm,
                                     13 * mm, 15 * mm], num_from=2),
                        Paragraph("Beats random = share of random rankings with a lower CAGR. DD better than = share of "
                                  "random rankings with a deeper drawdown. Top sector % = share of trades in the most "
                                  "traded industry.", SM)]),
          Image(str(p_eq), width=172 * mm, height=76 * mm),
          Image(str(p_dd), width=172 * mm, height=67 * mm),
          PageBreak(),
          Paragraph("Does it hold on other strategies?", H2),
          Image(str(p_rob), width=172 * mm, height=76 * mm)]
rows = [["Strategy", "Rule", "CAGR %", "Beats random", "Max DD %", "CAGR/DD", "With cap: CAGR", "With cap: DD"]]
for s in strats:
    for rule in PAL:
        a = R[(R.Strategy == s) & (R.Rule == rule) & (R["Sector cap"] == "none")].iloc[0]
        b = R[(R.Strategy == s) & (R.Rule == rule) & (R["Sector cap"] != "none")].iloc[0]
        rows.append([Paragraph(s, TC) if rule == CUR else "", rule, f"{a['CAGR %']:.1f}", f"{a['CAGR pct vs random']:.0f}%",
                     f"{a['Max DD %']:.0f}", f"{a['CAGR/DD']:.2f}", f"{b['CAGR %']:.1f}", f"{b['Max DD %']:.0f}"])
    x = X[X.Strategy == s]
    rows.append(["", Paragraph(f"<i>Random median ({len(x)} runs)</i>", TC), f"{x['CAGR %'].median():.1f}", "50%",
                 f"{x['Max DD %'].median():.0f}", f"{x['CAGR/DD'].median():.2f}", "", ""])
story += [table(rows, [38 * mm, 36 * mm, 14 * mm, 18 * mm, 16 * mm, 15 * mm, 19 * mm, 18 * mm], num_from=2),
          Paragraph("What the study shows", H2)] + bl(FINDINGS[3:]) + [
          Paragraph("Recommendation", H2)] + bl(RECOMMEND) + [
          Paragraph("Caveats", H2)] + bl([
              "Survivorship bias: today's NIFTY 500 members. Rules that favour past winners (6- and 12-month return) "
              "may gain most from it, because stocks that later fell out of the index are missing.",
              "One test period. A rule that wins over 27 years can lose for long stretches inside it; check "
              "2000–2012 and 2013–2026 separately before adopting it.",
              "Each strategy has only about 60–120 trades, so differences of 1–2% CAGR between rules are within "
              "the range of luck shown by the random runs.",
              "Industry labels are NSE's current ones, applied to the whole history."]) + [
          Paragraph("How to reproduce", H2),
          Paragraph("<font face='Courier' size='8'>python studies/slot_ranking.py --random 300<br/>"
                    "python studies/slot_ranking_report.py</font>", P),
          Paragraph("Code: studies/slot_ranking.py, lib/portfolio.py (rank, score, seed, sector_cap). "
                    "For research and education only; not investment advice.", SM)]


def footer(c, d):
    c.setFont("Helvetica", 7.5); c.setFillColor(colors.HexColor(GREY))
    c.drawString(18 * mm, 10 * mm, "Slot ranking study")
    c.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {d.page}")


story += ids.pdf_section(["stochrsi_pullback/monthly_prev_week_stop", "stochrsi_pullback/monthly_candle_stop", "ema61_breakout/monthly_candle_stop"], H2)
SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                  bottomMargin=16 * mm, title="Slot Ranking Study").build(story, onFirstPage=footer, onLaterPages=footer)
for p in charts:
    p.unlink()
print(OUT)
