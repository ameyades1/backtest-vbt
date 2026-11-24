"""Morning report for the overnight study -> results/studies/overnight/report.pdf (+ all_runs.csv).

Reads results for every job in results/studies/overnight/jobs_all.json (or jobs.json). In-sample = 2000-2018,
hold-out = 2019 onwards, both measured on each run's equity curve.
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
import lib.pdffont  # noqa: F401  (DejaVu glyphs for ₹ and −)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Image, KeepTogether, PageBreak
from lib import ids, engine, portfolio
from lib.costs import fee_per_side

OUT = ROOT / "results" / "studies" / "overnight"
GREY, DARK, BLUE = "#64748b", "#0f172a", "#2563eb"
jf = OUT / "jobs_all.json" if (OUT / "jobs_all.json").exists() else OUT / "jobs.json"
JOBS = json.load(open(jf))
IDS = ids.by_name()
MAIN = "stochrsi_pullback/monthly_prev_week_stop"
EMA = "ema61_breakout/monthly_weekly_stop"
HIWIN = "ema61_breakout/monthly_candle_stop"
UNIS = ["NIFTY500", "NIFTY50", "NIFTY100", "MIDCAP150", "SMALLCAP250"]


def cagr(e):
    e = e.dropna()
    if len(e) < 2 or e.iloc[0] <= 0:
        return np.nan
    return ((e.iloc[-1] / e.iloc[0]) ** (365.25 / max((e.index[-1] - e.index[0]).days, 1)) - 1) * 100


def mdd(e):
    e = e.dropna()
    return ((e / e.cummax()) - 1).min() * 100 if len(e) else np.nan


def fid(ex):
    return "none" if ex == "No target" else ex.split()[1].rstrip("%")


ROWS = {}


def load_run(name, uni):
    k = (name, uni)
    if k in ROWS:
        return ROWS[k]
    d = ROOT / "results" / name / uni.lower()
    if not (d / "summary.csv").exists():
        ROWS[k] = []
        return []
    sm = pd.read_csv(d / "summary.csv", index_col=0)
    eq = pd.read_csv(d / "equity.csv", index_col=0, parse_dates=True)
    out = []
    for ex in sm.index:
        e = eq[ex].dropna()
        f = portfolio.read_fills(d / f"fills_{fid(ex)}.csv") if (d / f"fills_{fid(ex)}.csv").exists() else pd.DataFrame()
        pnl = (f.proceeds - f.cost) if len(f) else pd.Series(dtype=float)
        pos = pnl[pnl > 0].sort_values(ascending=False)
        ins, hold = e[:"2018-12-31"], e["2019-01-01":]
        r = sm.loc[ex]
        out.append({"name": name, "id": ids.short(IDS[name]) if name in IDS else "", "universe": uni, "exit": ex,
                    "CAGR": r["CAGR %"], "DD": r["Max DD %"], "MAR": r["CAGR %"] / -r["Max DD %"] if r["Max DD %"] < 0 else np.nan,
                    "Trades": int(r["Trades taken"]), "Win": r["Win %"],
                    "Top5": pos.head(5).sum() / pnl.sum() * 100 if pnl.sum() > 0 else np.nan,
                    "CAGR_in": cagr(ins), "DD_in": mdd(ins), "CAGR_out": cagr(hold), "DD_out": mdd(hold)})
        o = out[-1]
        o["MAR_in"] = o["CAGR_in"] / -o["DD_in"] if o["DD_in"] < 0 else np.nan
        o["MAR_out"] = o["CAGR_out"] / -o["DD_out"] if o["DD_out"] < 0 else np.nan
    ROWS[k] = out
    return out


def get(name, uni="NIFTY500", ex="No target"):
    for r in load_run(name, uni):
        if r["exit"] == ex:
            return r
    return None


for j in JOBS:
    load_run(j["name"], j["universe"])
for b in [MAIN, MAIN + "_nifty200", EMA, EMA + "_nifty200", HIWIN, HIWIN + "_nifty200"]:
    load_run(b, "NIFTY500")
ALL = pd.DataFrame([r for v in ROWS.values() for r in v])
ALL.to_csv(OUT / "all_runs.csv", index=False)

# ---------------- phase 1 extras: walk-forward, top trades, Monte Carlo ----------------
import run_strategy as R
closes, dailies = R.load_dailies("NIFTY500")
fee, slip = fee_per_side("sharekhan", "delivery"), 0.001
from lib import market
WIN = [("2000", "2004"), ("2005", "2009"), ("2010", "2014"), ("2015", "2019"), ("2020", "2026")]
wf_rows = [["Strategy"] + [f"{a}–{b[-2:]}" for a, b in WIN]]
mc_rows = [["Strategy", "Max DD actual", "MC DD 5%", "MC DD median", "MC DD 95%", "Loss streak 95%"]]
top_rows = [["Strategy", "CAGR", "without top 5", "without top 10"]]
rng = np.random.default_rng(1)
for b in [MAIN, MAIN + "_nifty200"]:
    cfg = json.load(open(ROOT / "strategies" / f"{b}.json"))
    ec = R.engine_cfg(cfg, None)
    mk = market.regime(200) if "market_sma" in ec.get("entry", {}).get("day_filters", {}) else None
    trades = [t for s, df in dailies.items() for t in engine.simulate(df, s, ec, mk)]
    row = [ids.short(IDS[b]) + " " + ("main + 200-DMA" if "nifty200" in b else "main")]
    for a, z in WIN:
        cw = closes[:f"{z}-12-31"]
        tw = [t for t in trades if pd.Timestamp(f"{a}-01-01") <= t.entry_date <= pd.Timestamp(f"{z}-12-31")]
        curve, fills, sk = portfolio.run(tw, cw, 100_000, 0.01, 8, fee, slip, "tightest", f"{a}-01-01")
        row.append(f"{cagr(curve['equity']):.1f}% / {mdd(curve['equity']):.0f}%")
    wf_rows.append(row)
    f = portfolio.read_fills(ROOT / "results" / b / "nifty500" / "fills_none.csv", parse_dates=["entry_date", "exit_date"])
    pnl = (f.proceeds - f.cost).to_numpy()
    yrs = (pd.Timestamp("2026-11-01") - pd.Timestamp("2000-01-01")).days / 365.25
    cg = lambda tot: ((100_000 + tot) / 100_000) ** (1 / yrs) * 100 - 100 if 100_000 + tot > 0 else -100
    srt = np.sort(pnl)[::-1]
    top_rows.append([row[0], f"{cg(pnl.sum()):.1f}%", f"{cg(pnl.sum() - srt[:5].sum()):.1f}%",
                     f"{cg(pnl.sum() - srt[:10].sum()):.1f}%"])
    dds, sts = [], []
    for _ in range(1000):
        p = rng.permutation(pnl)
        eqp = 100_000 + np.cumsum(p)
        pk = np.maximum.accumulate(np.concatenate([[100_000], eqp]))[1:]
        dds.append(((eqp - pk) / pk).min() * 100)
        best = cur = 0
        for x in p:
            cur = cur + 1 if x <= 0 else 0; best = max(best, cur)
        sts.append(best)
    act = get(b)["DD"]
    mc_rows.append([row[0], f"{act:.0f}%", f"{np.percentile(dds, 5):.0f}%", f"{np.median(dds):.0f}%",
                    f"{np.percentile(dds, 95):.0f}%", f"{np.percentile(sts, 95):.0f}"])

# ---------------- PDF ----------------
ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=17, leading=21, alignment=0, textColor=colors.HexColor(DARK), spaceAfter=2)
SUB = ParagraphStyle("SUB", parent=ss["Normal"], fontSize=9, textColor=colors.HexColor(GREY))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12.5, textColor=colors.HexColor(DARK), spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("P", parent=ss["Normal"], fontSize=9.2, leading=13, spaceAfter=4)
BL = ParagraphStyle("BL", parent=P, leftIndent=10, spaceAfter=2)
SM = ParagraphStyle("SM", parent=P, fontSize=7.8, leading=10, textColor=colors.HexColor(GREY))
TC = ParagraphStyle("TC", parent=SM, fontSize=6.8, leading=8, textColor=colors.HexColor(DARK))
bl = lambda xs: [Paragraph(x, BL, bulletText="•") for x in xs]


def table(rows, widths, num_from=1, fs=6.8):
    rows = [[Paragraph(str(c), TC) if (i > 0 and j == 0 and isinstance(c, str) and len(c) > 28) else c
             for j, c in enumerate(r)] for i, r in enumerate(rows)]
    tb = Table(rows, colWidths=widths, repeatRows=1)
    tb.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", fs), ("FONT", (0, 1), (-1, -1), "Helvetica", fs),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(DARK)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("ALIGN", (num_from, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 1.8), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.8)]))
    return tb


def fmt(v, f="{:.1f}"):
    return "–" if v is None or (isinstance(v, float) and np.isnan(v)) else f.format(v)


HDR = ["ID", "Strategy", "Exit", "CAGR", "Max DD", "CAGR/DD", "Trades", "Win %", "Top-5 %", "In: CAGR/DD",
       "Out: CAGR/DD"]
W = [15 * mm, 52 * mm, 15 * mm, 11 * mm, 12 * mm, 13 * mm, 11 * mm, 10 * mm, 12 * mm, 15 * mm, 15 * mm]


def line(r, short=None):
    return [r["id"], short or r["name"], r["exit"].replace("Target ", ""), fmt(r["CAGR"]), fmt(r["DD"], "{:.0f}"),
            fmt(r["MAR"], "{:.2f}"), f"{r['Trades']}", fmt(r["Win"], "{:.0f}"), fmt(r["Top5"], "{:.0f}"),
            f"{fmt(r['CAGR_in'])} / {fmt(r['DD_in'], '{:.0f}')}", f"{fmt(r['CAGR_out'])} / {fmt(r['DD_out'], '{:.0f}')}"]


def block(names, exits=("No target",), uni="NIFTY500", strip=""):
    rows = [HDR]
    for n in names:
        for ex in exits:
            r = get(n, uni, ex)
            if r:
                rows.append(line(r, n.replace(strip, "…") if strip else n))
    return table(rows, W)


story = [Paragraph("Overnight Study", H1),
         Paragraph("Robustness of the main strategy · sizing rules · fixing the 74% win-rate strategy · new indicators. "
                   "NIFTY 500 unless stated · from 2000 · Sharekhan delivery costs + 0.1% slippage", SUB),
         Paragraph("In = 2000–2018 (used to rank), Out = 2019 onwards (hold-out), both from each run's own equity curve. "
                   "Top-5 % = share of net profit from the 5 best trades. Today's index members only (survivorship "
                   "bias). Research, not financial advice.", SM)]

# summary: best by phase
NT = ALL[(ALL.universe == "NIFTY500")]
main_r, main_f = get(MAIN), get(MAIN + "_nifty200")
summ = []
summ.append(f"<b>Main strategy</b>: {main_r['id']} {fmt(main_r['CAGR'])}% / {fmt(main_r['DD'], '{:.0f}')}%; with the 200-day "
            f"entry filter {main_f['id']} {fmt(main_f['CAGR'])}% / {fmt(main_f['DD'], '{:.0f}')}%.")
p4 = NT[NT.name.isin({j["name"] for j in JOBS if j["phase"].startswith("4")})].dropna(subset=["MAR_in"])
p4 = p4[p4.Trades >= 50].sort_values("MAR_in", ascending=False)
if len(p4):
    b = p4.iloc[0]
    summ.append(f"<b>Best new-indicator variant (in-sample)</b>: {b['id']} {b['name']} ({b['exit']}): in "
                f"{fmt(b['CAGR_in'])}% / {fmt(b['DD_in'], '{:.0f}')}%, hold-out {fmt(b['CAGR_out'])}% / "
                f"{fmt(b['DD_out'], '{:.0f}')}%.")
p2 = NT[NT.name.str.contains("_size_")].sort_values("MAR", ascending=False)
if len(p2):
    b = p2.iloc[0]
    summ.append(f"<b>Best sizing rule</b>: {b['id']} {b['name']}: {fmt(b['CAGR'])}% / {fmt(b['DD'], '{:.0f}')}%.")
p3 = NT[NT.name.str.startswith(HIWIN) & (NT.name != HIWIN)].sort_values("MAR", ascending=False)
if len(p3):
    b = p3.iloc[0]
    summ.append(f"<b>Best fix for the 74% win-rate strategy</b>: {b['id']} {b['name']} ({b['exit']}): "
                f"{fmt(b['CAGR'])}% / {fmt(b['DD'], '{:.0f}')}%, win {fmt(b['Win'], '{:.0f}')}%.")
NOTES = [
    "<b>The main strategy's edge is real but fragile.</b> It earns 10-11% a year on NIFTY 50, NIFTY 100 and Midcap 150 "
    "as well (6-8% on Smallcap 250), so it is not a NIFTY 500 accident. But removing its 5 best trades cuts CAGR from "
    "11% to under 5%, and removing 10 leaves about 0-1%. Started fresh in each 5-year window it made 5-9% a year "
    "until 2019 and 32% after 2020; the 200-DMA version lost 7% a year with a 62% drawdown in 2015-19.",
    "<b>Parameters are a plateau, not a peak.</b> EMA 55/61/89, oversold 30/40 and RSI 40/50 all give 10.5-12.4% "
    "CAGR. EMA34, EMA144 and RSI 60 are clearly worse. Entering 1-2 days late costs little. Good: 61/30/50 is not a "
    "lucky choice.",
    "<b>Sizing rules do not cut the drawdown.</b> Drawdown halving, VIX, breadth and NIFTY-based half sizing all leave "
    "the drawdown at 38-43% and cost 0.7-2 points of CAGR. With the 200-DMA entry filter, NIFTY-based sizing changes "
    "nothing (no entries happen below the average anyway). Risk per trade scales CAGR (0.75%: 10.7%, 2%: 14.5% with "
    "the filter) with only a small rise in drawdown, because a few positions dominate either way.",
    "<b>Best new idea: a 2 x ATR stop on the main strategy (Sd07eb46e)</b>: 12.3% / -30% on NIFTY 500 against "
    "11.8% / -39%. But the hold-out (2019+) is weak (2.1% / -28%) and on Midcap/Smallcap the drawdown is 53%. "
    "Worth a closer look, not a switch.",
    "<b>Supertrend exit (S3f9854aa)</b> gives the shallowest drawdowns of the trend strategies (-16% to -28% on every "
    "universe) at 5.5-9% CAGR, with 3x more trades and less dependence on a few winners (top-5 share 60%). The most "
    "robust risk-reducing change found so far.",
    "<b>Breakouts with a 2R target</b> (Donchian 55 / 52-week high, with the market filter) are steady but small: "
    "about 4.5-5% CAGR with a -12% drawdown, 47% wins, and profits spread over many trades (top-5 share 8-20%).",
    "<b>The 74% win-rate strategy</b>: R-multiple targets fix the payoff (3R: 4.1% / -11%, 49% wins) and more slots "
    "raise CAGR (24 slots, 30% target: 5.1% / -23%), but nothing tested gets it above about 5% a year.",
    "<b>No new trigger beats StochRSI.</b> Williams %R, CCI, EMA21 touch and daily RSI(2) pullbacks, and Donchian, "
    "Bollinger and relative-strength breakouts, all land at or below 10% with similar or deeper drawdowns.",
]
story += [Paragraph("Headlines (computed)", H2)] + bl(summ) + [Paragraph("Reviewer's notes", H2)] + bl(NOTES)

# phase 1
story += [PageBreak(), Paragraph("Phase 1 · Is the main strategy's edge real?", H2),
          Paragraph("Walk-forward: fresh ₹1 lakh in each window, same rules (CAGR / max drawdown)", P),
          table(wf_rows, [40 * mm] + [26 * mm] * 5),
          Paragraph("Remove the best trades (no-target exit; simple sum of trade P&amp;L)", P),
          table(top_rows, [50 * mm, 25 * mm, 30 * mm, 30 * mm]),
          Paragraph("Monte Carlo: 1,000 reshuffles of the closed-trade order (fixed ₹ risk, one trade after another). "
                    "<b>Caution:</b> this counts only realised P&amp;L. The real drawdowns come from open positions "
                    "falling in value before they are closed, so these figures badly understate the risk; use the "
                    "actual and walk-forward drawdowns instead. The losing-streak figure is still meaningful.", P),
          table(mc_rows, [40 * mm, 24 * mm, 22 * mm, 24 * mm, 22 * mm, 26 * mm]),
          Paragraph("Other universes", P)]
urows = [HDR]
for b in [MAIN, MAIN + "_nifty200"]:
    for u in UNIS:
        r = get(b, u)
        if r:
            urows.append(line(r, f"{b.split('/')[1]} @{u}"))
story += [table(urows, W), Paragraph("EMA span (Fibonacci 34/55/89/144; 61 = current) and other parameters", P)]
for b in [MAIN, MAIN + "_nifty200"]:
    names = [b + s for s in ["_ema34", "_ema55", "", "_ema89", "_ema144", "_os20", "_os40", "_rsi40", "_rsi60",
                             "_delay1", "_delay2"]]
    story.append(block(names, strip=""))

# phase 2
story += [PageBreak(), Paragraph("Phase 2 · Sizing rules", H2)]
for b in [MAIN, MAIN + "_nifty200", EMA, EMA + "_nifty200"]:
    story.append(block([b] + [f"{b}_size_{k}" for k in ["dd", "mkt", "breadth", "vix", "ddmkt"]]))
story.append(Paragraph("Risk per trade", P))
story.append(block([b + s for b in [MAIN, MAIN + "_nifty200"] for s in ["_risk0p75", "", "_risk1p5", "_risk2p0"]]))

# phase 3
story += [PageBreak(), Paragraph("Phase 3 · The 74% win-rate strategy (ema61_breakout/monthly_candle_stop)", H2)]
for b in [HIWIN, HIWIN + "_nifty200"]:
    story.append(Paragraph(b, P))
    story.append(block([b] + [f"{b}_slots{n}" for n in [12, 16, 20, 24]] + [f"{b}_maxstop{m}" for m in [8, 10, 12, 15]],
                       exits=("Target 8%", "Target 15%")))
    story.append(block([f"{b}_rtargets", f"{b}_combo"],
                       exits=("No target", "Target 1R", "Target 1.5R", "Target 2R", "Target 3R", "Target P1.5R")))

# phase 4
story += [PageBreak(), Paragraph("Phase 4 · New indicators (ranked by in-sample CAGR/DD, at least 50 trades)", H2)]
r4 = [HDR] + [line(r) for _, r in p4.iterrows()]
story.append(table(r4, W))
fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=200)
ax.scatter(p4.MAR_in, p4.MAR_out, s=12, color=BLUE, zorder=3)
for _, r in p4.head(5).iterrows():
    ax.annotate(r["id"], (r.MAR_in, r.MAR_out), fontsize=6, color=DARK)
if main_f:
    ax.scatter([main_f["MAR_in"]], [main_f["MAR_out"]], s=30, color="#dc2626", zorder=4, label="main + 200-DMA")
ax.axhline(0, color=GREY, lw=.5); ax.set_xlabel("In-sample CAGR/DD (2000–18)", fontsize=7)
ax.set_ylabel("Hold-out CAGR/DD (2019+)", fontsize=7); ax.legend(frameon=False, fontsize=7)
for sp in ("top", "right"):
    ax.spines[sp].set_visible(False)
ax.tick_params(labelsize=7)
fig.tight_layout(); pimg = OUT / "_p4.png"; fig.savefig(pimg); plt.close(fig)
story += [Image(str(pimg), width=172 * mm, height=76 * mm),
          Paragraph("Each dot: one new-indicator run. A strategy that holds up sits near the diagonal; one that falls "
                    "towards zero in the hold-out was probably fitted to the past.", SM)]
top5 = json.load(open(OUT / "top5.json")) if (OUT / "top5.json").exists() else []
if top5:
    story.append(Paragraph("Top 5 on other universes (stage 2)", P))
    rows = [HDR]
    for n in top5:
        for u in UNIS:
            r = get(n, u)
            if r:
                rows.append(line(r, f"{n.split('/')[-1]} @{u}"))
    story.append(table(rows, W))
story += ids.pdf_section(sorted({j["name"] for j in JOBS} | {MAIN, EMA, HIWIN}), H2)
SimpleDocTemplate(str(OUT / "report.pdf"), pagesize=A4, leftMargin=14 * mm, rightMargin=14 * mm, topMargin=14 * mm,
                  bottomMargin=14 * mm, title="Overnight study").build(story)
pimg.unlink()
print(OUT / "report.pdf")
for s_ in summ:
    print("-", s_)
