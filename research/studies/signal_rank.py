"""Ranking StochRSI and EMA61 signals with MACD and candlestick patterns.

    python studies/signal_rank.py [--random 100]

1. Signal level: every signal the engine produces (before any slot limit), its result in R and its score at
   the entry day. Does a higher score mean a better trade? Independent of slot luck.
2. Portfolio level: each ranking rule vs the current rule (tightest stop), 12-month return, and the spread of
   N random rankings. No-target and 15% target, with and without the 200-day filter.
Writes results/studies/signal_rank/ (signals.csv, rules.csv, random.csv, report.pdf).
"""
import argparse, json, sys
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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image, KeepTogether
from lib import engine, portfolio, market, scores, ids
from lib.costs import fee_per_side
from run_strategy import engine_cfg, load_dailies

ap = argparse.ArgumentParser()
ap.add_argument("--random", type=int, default=100)
A = ap.parse_args()
OUT = ROOT / "results" / "studies" / "signal_rank"
OUT.mkdir(parents=True, exist_ok=True)
BLUE, GREY, DARK, RED, GREEN = "#2563eb", "#64748b", "#0f172a", "#dc2626", "#15803d"
STRATS = {"StochRSI pullback": "stochrsi_pullback/monthly_prev_week_stop",
          "EMA61 breakout": "ema61_breakout/monthly_weekly_stop"}
EXITS = [None, 15]
START = "2000-01-01"
fee, slip = fee_per_side("sharekhan", "delivery"), 0.001
closes, dailies = load_dailies("NIFTY500")

print("scores...", flush=True)
SC = {"MACD": scores.table({"type": "macd_turn"}, dailies),
      "Pattern": scores.table({"type": "weekly_pattern", "weeks": 2}, dailies)}
SC["MACD + pattern"] = SC["MACD"].fillna(0) + SC["Pattern"].fillna(0)
c = closes.ffill()
mom = (c / c.shift(252) - 1).shift(1)
SC["MACD + pattern, 12m tiebreak"] = SC["MACD + pattern"] + 0.9 * mom.rank(axis=1, pct=True).fillna(0)
SC["12-month return"] = mom
RULES = ["Tightest stop (current)", "12-month return", "MACD", "Pattern", "MACD + pattern", "MACD + pattern, 12m tiebreak"]


def at(tab, t):
    try:
        return tab.at[t.entry_date, t.symbol]
    except KeyError:
        return np.nan


def prun(trades, rule, seed=None):
    if rule == "Tightest stop (current)":
        kw = dict(rank="tightest")
    elif rule == "Random":
        kw = dict(rank="random", seed=seed)
    elif rule == "12-month return":
        kw = dict(rank="score", score=SC[rule])
    else:
        kw = dict(rank="score_tightest", score=SC[rule])
    curve, fills, sk = portfolio.run(trades, closes, 100_000, 0.01, 8, fee, slip, start=START, **kw)
    sm = portfolio.summary(curve, fills, sk, 100_000, 8)
    eq = curve["equity"]
    yrs = lambda s, t: eq[s:t]
    cg = lambda e: ((e.iloc[-1] / e.iloc[0]) ** (365.25 / (e.index[-1] - e.index[0]).days) - 1) * 100
    return {"CAGR %": sm["CAGR %"], "Max DD %": sm["Max DD %"], "Win %": sm["Win %"], "Trades": sm["Trades taken"],
            "CAGR 2000-12": cg(yrs("2000", "2012")), "CAGR 2013-26": cg(yrs("2013", None))}, \
        {(f.symbol, f.entry_date) for f in fills}, eq


sig_rows, rule_rows, rand_rows, curves = [], [], [], {}
mk = market.regime(200)
for sname, path in STRATS.items():
    cfg = json.load(open(ROOT / "strategies" / f"{path}.json"))
    for filt in [False, True]:
        for tg in EXITS:
            ec = engine_cfg(cfg, tg)
            if filt:
                ec["entry"] = {**ec["entry"], "day_filters": {**ec["entry"].get("day_filters", {}), "market_sma": 200}}
            trades = [t for s, df in dailies.items() for t in engine.simulate(df, s, ec, mk if filt else None)
                      if t.entry_date >= pd.Timestamp(START)]
            ex = "No target" if tg is None else f"Target {tg}%"
            fl = "200-DMA filter" if filt else "no filter"
            print(sname, fl, ex, len(trades), flush=True)
            # 1. signal level (unfiltered only: the filter just removes signals)
            if not filt:
                last = closes.ffill().iloc[-1]
                for t in trades:
                    px = t.exit if t.exit is not None else last.get(t.symbol, np.nan)
                    sig_rows.append({"Strategy": sname, "Exit": ex, "symbol": t.symbol, "entry_date": t.entry_date,
                                     "R": (px - t.entry) / (t.entry - t.stop), "ret %": (px / t.entry - 1) * 100,
                                     **{k: at(SC[k], t) for k in ["MACD", "Pattern", "MACD + pattern"]}})
            # 2. portfolio level
            base_set = None
            for rule in RULES:
                r, got, eq = prun(trades, rule)
                if rule == RULES[0]:
                    base_set = got
                rule_rows.append({"Strategy": sname, "Filter": fl, "Exit": ex, "Rule": rule, **r,
                                  "Trades changed": len(got - base_set)})
                if tg is None and not filt:
                    curves[(sname, rule)] = eq
            if tg is None:
                for seed in range(A.random):
                    r, _, _ = prun(trades, "Random", seed)
                    rand_rows.append({"Strategy": sname, "Filter": fl, "Exit": ex, "Seed": seed, **r})
SIG, R, RND = pd.DataFrame(sig_rows), pd.DataFrame(rule_rows), pd.DataFrame(rand_rows)
SIG.to_csv(OUT / "signals.csv", index=False); R.to_csv(OUT / "rules.csv", index=False); RND.to_csv(OUT / "random.csv", index=False)

# ---------------- report ----------------
charts = []


def style(ax):
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.tick_params(colors=GREY, length=0, labelsize=7.5)
    ax.grid(axis="y", color="#e2e8f0", zorder=0)


def save(fig, name):
    p = OUT / f"_{name}.png"; fig.tight_layout(); fig.savefig(p); plt.close(fig); charts.append(p); return p


def bucket(df, col):
    out = []
    for v, g in df.groupby(df[col].round(0)):
        r = g["R"].clip(-3, None)
        out.append([f"{v:.0f}", f"{len(g):,}", f"{(g['R'] > 0).mean() * 100:.0f}%", f"{r.mean():.2f}",
                    f"± {1.96 * r.std() / np.sqrt(len(g)):.2f}", f"{g['R'].median():.2f}", f"{g['ret %'].median():.1f}%"])
    return out


# signal-level chart: mean R (15% target, so outliers do not dominate) by combined score
fig, axs = plt.subplots(1, 2, figsize=(7.2, 2.8), dpi=200, sharey=True)
for ax, s in zip(axs, STRATS):
    g = SIG[(SIG.Strategy == s) & (SIG.Exit == "Target 15%")].dropna(subset=["MACD + pattern"])
    st = g.groupby("MACD + pattern")["R"].agg(["mean", "std", "count"])
    ax.bar(st.index, st["mean"], yerr=1.96 * st["std"] / np.sqrt(st["count"]), color=BLUE, capsize=3, zorder=3)
    for x, n in zip(st.index, st["count"]):
        ax.text(x, 0, f"n={n}", ha="center", va="bottom", fontsize=6.5, color="white" if st["mean"][x] > .05 else GREY)
    ax.axhline(0, color=GREY, lw=.6)
    ax.set_xlabel("MACD + pattern score", fontsize=7, color=GREY)
    ax.set_title(f"{s}: avg R per signal (15% target)", loc="left", fontsize=8.5, fontweight="bold", color=DARK)
    style(ax)
p_sig = save(fig, "signal")

fig, axs = plt.subplots(2, 2, figsize=(7.2, 4.6), dpi=200)
for i, s in enumerate(STRATS):
    for j, fl in enumerate(["no filter", "200-DMA filter"]):
        ax = axs[i, j]
        rd = RND[(RND.Strategy == s) & (RND.Filter == fl)]["CAGR %"]
        ax.hist(rd, bins=20, color="#cbd5e1", zorder=2)
        rr = R[(R.Strategy == s) & (R.Filter == fl) & (R.Exit == "No target")]
        for k, (rule, col) in enumerate(zip(RULES, [DARK, GREEN, "#d97706", "#9333ea", BLUE, RED])):
            v = rr[rr.Rule == rule]["CAGR %"].iloc[0]
            ax.axvline(v, color=col, lw=1.4, label=rule if i == 0 and j == 0 else None, zorder=3)
        ax.set_title(f"{s}, {fl}", loc="left", fontsize=8, fontweight="bold", color=DARK)
        ax.set_xlabel("CAGR % (no target)", fontsize=7, color=GREY)
        style(ax)
fig.legend(frameon=False, fontsize=6.5, loc="lower center", ncol=3)
fig.tight_layout(rect=(0, .1, 1, 1))
p_rand = OUT / "_rand.png"; fig.savefig(p_rand); plt.close(fig); charts.append(p_rand)

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


SHDR = ["Score", "Signals", "Win %", "Avg R", "95% band", "Median R", "Median return"]
SW = [16 * mm, 18 * mm, 15 * mm, 15 * mm, 18 * mm, 18 * mm, 22 * mm]
sig_tabs = []
for s in STRATS:
    for ex in ["No target", "Target 15%"]:
        g = SIG[(SIG.Strategy == s) & (SIG.Exit == ex)]
        for col in ["MACD", "Pattern", "MACD + pattern"]:
            sig_tabs.append(KeepTogether([Paragraph(f"{s} · {ex} · {col} score", P),
                                          table([SHDR] + bucket(g.dropna(subset=[col]), col), SW)]))


def pct_rank(s, fl, v):
    rd = RND[(RND.Strategy == s) & (RND.Filter == fl)]["CAGR %"]
    return (rd < v).mean() * 100


RH = ["Rule", "CAGR %", "Max DD %", "Win %", "Trades", "Changed", "vs random", "2000–12", "2013–26"]
RW = [52 * mm, 14 * mm, 15 * mm, 12 * mm, 13 * mm, 15 * mm, 16 * mm, 14 * mm, 14 * mm]
port_tabs = []
for s in STRATS:
    for fl in ["no filter", "200-DMA filter"]:
        for ex in ["No target", "Target 15%"]:
            rr = R[(R.Strategy == s) & (R.Filter == fl) & (R.Exit == ex)]
            rows = [RH] + [[r.Rule, f"{r['CAGR %']:.1f}", f"{r['Max DD %']:.0f}", f"{r['Win %']:.0f}", f"{r.Trades}",
                            f"{r['Trades changed']}",
                            f"{pct_rank(s, fl, r['CAGR %']):.0f}th pct" if ex == "No target" else "–",
                            f"{r['CAGR 2000-12']:.1f}", f"{r['CAGR 2013-26']:.1f}"] for _, r in rr.iterrows()]
            port_tabs.append(KeepTogether([Paragraph(f"{s} · {fl} · {ex}", P), table(rows, RW)]))

# findings, computed
def sig_gap(s, ex, col, hi, lo=0):
    g = SIG[(SIG.Strategy == s) & (SIG.Exit == ex)].dropna(subset=[col])
    a, b = g[g[col].round(0) >= hi]["R"].clip(-3, None), g[g[col].round(0) <= lo]["R"].clip(-3, None)
    se = np.sqrt(a.var() / len(a) + b.var() / len(b))
    return a.mean(), b.mean(), (a.mean() - b.mean()) / se, len(a), len(b)


NTR = R[R.Exit == "No target"].copy()
NTR["pct"] = [pct_rank(r.Strategy, r.Filter, r["CAGR %"]) for _, r in NTR.iterrows()]
cand = NTR[NTR.Rule.str.contains("MACD|Pattern")]
beat95 = cand[cand.pct >= 95]
FIND = []
for s in STRATS:
    a, b, z, na, nb = sig_gap(s, "Target 15%", "MACD + pattern", 2)
    pa, pb, pz, _, _ = sig_gap(s, "Target 15%", "Pattern", 1)
    FIND.append(f"<b>{s}, signal level:</b> with a 15% target, signals scoring 2–3 averaged {a:.2f}R against {b:.2f}R for "
                f"score 0 ({na} vs {nb} signals; difference {z:.1f} standard errors). Pattern alone: {pa:.2f}R with a "
                f"pattern vs {pb:.2f}R without ({pz:.1f} s.e.). "
                + ("A real but modest edge." if z >= 2 else "Not distinguishable from noise."))
FIND.append(f"<b>Portfolio level:</b> {len(beat95)} of {len(cand)} MACD/pattern rankings (no target) beat the 95th "
            f"percentile of random rankings"
            + (": " + "; ".join(f"{r.Strategy} {r.Filter}, {r.Rule} ({r['CAGR %']:.1f}%)" for _, r in beat95.iterrows())
               if len(beat95) else "") + ". "
            f"They change {int(cand['Trades changed'].min())}–{int(cand['Trades changed'].max())} trades versus the "
            f"current rule, so most CAGR differences are path luck.")
m12 = NTR[NTR.Rule == "12-month return"]
FIND.append("<b>12-month return</b> (the slot-ranking study's best rule) for reference: "
            + "; ".join(f"{r.Strategy} {r.Filter} {r['CAGR %']:.1f}% ({r.pct:.0f}th pct)" for _, r in m12.iterrows()) + ".")

REC = [
    "<b>Keep the current rule (tightest stop).</b> Neither MACD nor candlestick patterns carry information about which "
    "of our signals will do better, and the portfolio results sit inside the range of random rankings.",
    "<b>Do not adopt 12-month return either.</b> It stood out only for the unfiltered StochRSI strategy; with the "
    "200-day filter and on the EMA61 breakout it is inside the random range. The earlier slot-ranking result was "
    "most likely luck.",
    "<b>Slot ranking is not where the edge is.</b> Rankings change only 7–32 of 110–150 trades. Effort is better spent "
    "on exits and on risk when the market turns (for example tightening stops below the 200-day average).",
]
story = [
    Paragraph("Ranking Signals with MACD and Candlestick Patterns", H1),
    Paragraph("StochRSI pullback (prev-week stop) and EMA61 breakout (weekly stop) · NIFTY 500 · 2000 to 2026 · 1% risk "
              "· 8 slots · Sharekhan delivery costs + 0.1% slippage", SUB),
    Paragraph("Data: actual traded prices (split/bonus adjusted). Today's index members only (survivorship bias). "
              "Research, not financial advice.", SM),
    Paragraph("What was tested", H2)] + bl([
    "The signals are unchanged; only the order in which competing signals get a free slot changes.",
    "<b>MACD score</b>: monthly MACD (12,26,9) of the last completed month. 2 = histogram rising while MACD is below "
    "zero, 1 = rising above zero, 0 = falling.",
    "<b>Pattern score</b>: 1 if TA-Lib found a bullish engulfing, hammer, morning star or piercing line on either of the "
    "last 2 completed weekly candles before the entry day.",
    "<b>MACD + pattern</b>: the sum (0–3). Ties by tightest stop, or in a second version by 12-month return.",
    "Baselines: the current rule (tightest stop), 12-month return, and " + f"{A.random}" + " random rankings.",
    "Signal-level test: every signal the engine produces, before the 8-slot limit, scored and grouped. R = result "
    "divided by the initial risk, before costs; open trades valued at the last close. With no target a few huge "
    "winners dominate averages, so the 15% target is the cleaner test; R is capped at −3 for gaps."]) + [
    Paragraph("Answer", H2)] + bl(FIND) + [Paragraph("Recommendation", H2)] + bl(REC) + [
    Image(str(p_sig), width=172 * mm, height=67 * mm),
    Paragraph("Bars: average R per signal at each score, with 95% bands. Overlapping bands mean the score does not "
              "separate good from bad signals.", SM),
    Image(str(p_rand), width=172 * mm, height=110 * mm),
    Paragraph("Grey: CAGR of the random rankings. Lines: each rule.", SM),
    Paragraph("Portfolio results", H2),
    Paragraph("Changed = trades taken that the current rule did not take. vs random = percentile among random rankings "
              "(no-target exit only).", SM)] + port_tabs + [
    Paragraph("Signal-level detail", H2)] + sig_tabs
story += ids.pdf_section([b + sfx for b in STRATS.values() for sfx in ["", "_nifty200"]] + sorted(n for n in ids.by_name() if "_rank" in n and any(n.startswith(b + "_") for b in STRATS.values())), H2)
SimpleDocTemplate(str(OUT / "report.pdf"), pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=16 * mm,
                  bottomMargin=16 * mm, title="Signal ranking: MACD and patterns").build(story)
for p in charts:
    p.unlink()
print(OUT / "report.pdf")
for f in FIND:
    print("-", f)
