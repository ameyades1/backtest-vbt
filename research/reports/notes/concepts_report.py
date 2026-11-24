"""Concepts and metrics explained (plain language, formulas, intuition, history) -> reports/notes/concepts.pdf

    python reports/notes/concepts_report.py

Every example number is computed live from S44984096 (stexit/A_flip_capentry, point-in-time NIFTY 500), so the book
stays in step with the data. Worked example trade: Persistent Systems, July 2020 - May 2022.
"""
import json, os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import lib.pdffont  # noqa: F401
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle, Image,
                                KeepTogether, PageBreak, NextPageTemplate)
from reportlab.platypus.tableofcontents import TableOfContents
from lib import metrics, markettype, portfolio, ids
from lib.indicators import resample, ema, rsi, stoch_rsi, atr, sma
from lib.engine import nifty_close
from lib import data

OUT = ROOT / "reports" / "notes"
IMG = OUT / "_concepts"; IMG.mkdir(exist_ok=True)
RUN = ROOT / "results" / "stexit" / "A_flip_capentry" / "nifty500_pit"
SID = "S44984096"

# ---------------- fonts and styles ----------------
_DV = "/usr/share/fonts/truetype/dejavu/"
_MPL = os.path.join(matplotlib.get_data_path(), "fonts", "ttf")
for nm, f in [("Serif", "DejaVuSerif.ttf"), ("Serif-Bold", "DejaVuSerif-Bold.ttf"), ("Mono", "DejaVuSansMono.ttf")]:
    p = _DV + f if os.path.exists(_DV + f) else os.path.join(_MPL, f)
    pdfmetrics.registerFont(TTFont(nm, p))
from reportlab.lib.fonts import addMapping
addMapping("Serif", 0, 0, "Serif"); addMapping("Serif", 1, 0, "Serif-Bold")
addMapping("Serif", 0, 1, "Serif"); addMapping("Serif", 1, 1, "Serif-Bold")

INK, GREY, AMBER = "#0f172a", "#64748b", "#b45309"
BOX = {"plain": ("#eff6ff", "#2563eb", "In plain words"), "rule": ("#fffbeb", AMBER, "Our rule"),
       "ex": ("#f0fdf4", "#16a34a", "Example from your strategy"), "warn": ("#fef2f2", "#dc2626", "Watch out"),
       "why": ("#f5f3ff", "#7c3aed", "Why it was invented"), "formula": ("#f8fafc", "#334155", "Formula")}
B = ParagraphStyle("B", fontName="Serif", fontSize=12, leading=17.5, spaceAfter=7, textColor=colors.HexColor(INK))
BI = ParagraphStyle("BI", parent=B, spaceAfter=3)
BUL = ParagraphStyle("BUL", parent=B, leftIndent=14, bulletIndent=3, spaceAfter=3)
H1 = ParagraphStyle("H1", fontName="Helvetica-Bold", fontSize=26, leading=31, textColor=colors.HexColor(AMBER), spaceAfter=10)
H2 = ParagraphStyle("H2", fontName="Helvetica-Bold", fontSize=18, leading=22, textColor=colors.HexColor(INK), spaceBefore=12,
                    spaceAfter=6)
H3 = ParagraphStyle("H3", fontName="Helvetica-Bold", fontSize=14, leading=18, textColor=colors.HexColor(INK), spaceBefore=8,
                    spaceAfter=4)
LAB = ParagraphStyle("LAB", fontName="Helvetica-Bold", fontSize=10, leading=13, spaceAfter=2)
FM = ParagraphStyle("FM", fontName="Mono", fontSize=11, leading=16, textColor=colors.HexColor(INK))
SM = ParagraphStyle("SM", fontName="Helvetica", fontSize=9.5, leading=12.5, textColor=colors.HexColor(GREY))
CAP = ParagraphStyle("CAP", parent=SM, spaceBefore=2, spaceAfter=8)
TC = ParagraphStyle("TC", fontName="Helvetica", fontSize=10, leading=13)
TH = ParagraphStyle("TH", parent=TC, fontName="Helvetica-Bold", textColor=colors.white)
W = A4[0] - 40 * mm


def P(t, st=B):
    return Paragraph(t, st)


def box(kind, *items):
    bg, edge, label = BOX[kind]
    inner = [Paragraph(label.upper(), ParagraphStyle("l", parent=LAB, textColor=colors.HexColor(edge)))]
    for it in items:
        if isinstance(it, str):
            inner.append(Paragraph(it, FM if kind == "formula" else BI))
        elif isinstance(it, list):
            inner += [Paragraph(x, BUL, bulletText="•") for x in it]
        else:
            inner.append(it)
    t = Table([[inner]], colWidths=[W])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), colors.HexColor(bg)),
                           ("LINEBEFORE", (0, 0), (0, -1), 3.5, colors.HexColor(edge)),
                           ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                           ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7)]))
    return KeepTogether([t, Spacer(1, 7)])


def table(rows, widths, hl=None):
    data_ = [[Paragraph(str(c), TH) for c in rows[0]]] + [[Paragraph(str(c), TC) for c in r] for r in rows[1:]]
    t = Table(data_, colWidths=widths, repeatRows=1)
    st = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(INK)), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
          ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]
    if hl:
        st.append(("BACKGROUND", (0, hl), (-1, hl), colors.HexColor("#fef3c7")))
    t.setStyle(TableStyle(st))
    return KeepTogether([t, Spacer(1, 8)])


def img(path, h_mm, cap=None):
    out = [Image(str(path), width=W, height=h_mm * mm)]
    if cap:
        out.append(Paragraph(cap, CAP))
    return KeepTogether(out)


def concept(title, plain=None, why=None, formula=None, body=None, rule=None, ex=None, warn=None, extra=None):
    """One concept, always in the same order."""
    fl = [Paragraph(title, H2)]
    if plain:
        fl.append(box("plain", *([plain] if isinstance(plain, str) else plain)))
    for b in (body or []):
        fl.append(b if not isinstance(b, str) else P(b))
    if formula:
        fl.append(box("formula", *([formula] if isinstance(formula, str) else formula)))
    if why:
        fl.append(box("why", *([why] if isinstance(why, str) else why)))
    if rule:
        fl.append(box("rule", *([rule] if isinstance(rule, str) else rule)))
    if ex:
        fl.append(box("ex", *([ex] if isinstance(ex, str) else ex)))
    for x in (extra or []):
        fl.append(x)
    if warn:
        fl.append(box("warn", *([warn] if isinstance(warn, str) else warn)))
    return fl


# ---------------- live numbers ----------------
S = pd.read_csv(RUN / "summary.csv", index_col=0).loc["No target"]
START = json.load(open(RUN / "config.json"))["period"]["start"]
M = metrics.compute(pd.read_csv(RUN / "fills_none.csv"), S, START)
C = M["_closed"].copy()
C["R"] = C.pnl / C.risk.replace(0, np.nan)
R = C.R.dropna()
EQ = pd.read_csv(RUN / "equity.csv", index_col=0, parse_dates=True)["No target"].dropna()
DD = EQ / EQ.cummax() - 1
YRS = (EQ.index[-1] - EQ.index[0]).days / 365.25
NX = nifty_close().reindex(EQ.index, method="ffill").dropna()
N_CAGR = ((NX.iloc[-1] / NX.iloc[0]) ** (1 / YRS) - 1) * 100
N_DD = (NX / NX.cummax() - 1).min() * 100
uw = (DD < 0).astype(int); UW = uw.groupby((uw == 0).cumsum()).sum().max() / 252
RND = pd.read_csv(ROOT / "results" / "studies" / "skipped" / "random.csv")
RE = RND[RND.tag == "E"]
MT = markettype.breakdown(EQ, M["_closed"])
X10 = R.drop(R.nlargest(10).index)
cfg = json.load(open(RUN / "config.json"))
f2 = lambda x: f"{x:,.2f}"

# ---------------- worked example: Persistent Systems ----------------
SYM, ENT, EXT = "PERSISTENT.NS", pd.Timestamp("2020-07-20"), pd.Timestamp("2022-05-16")
fr = pd.read_csv(RUN / "fills_none.csv", parse_dates=["entry_date", "exit_date"])
tr = fr[(fr.symbol == SYM) & (fr.entry_date == ENT)].iloc[0]
QTY, EP, SP, XP = int(tr.qty), float(tr.entry), float(tr.stop), float(tr.exit)
RISK1 = QTY * (EP - SP); PNL = (tr.proceeds - tr.cost); TR_R = PNL / RISK1
dly = data.ohlcv_for(SYM, "2010-01-01")[["Open", "High", "Low", "Close", "Volume"]].dropna()
wk = resample(dly, "W"); mo = resample(dly, "M")


def st_line(bars, n=10, m=3.0):
    a = atr(bars, n).to_numpy(); hl2 = ((bars.High + bars.Low) / 2).to_numpy(); c = bars.Close.to_numpy()
    ub, lb = hl2 + m * a, hl2 - m * a; fu, fl = ub.copy(), lb.copy(); bull = np.zeros(len(c), bool); line = np.full(len(c), np.nan)
    for i in range(1, len(c)):
        if np.isnan(a[i]):
            continue
        fu[i] = ub[i] if (np.isnan(fu[i - 1]) or ub[i] < fu[i - 1] or c[i - 1] > fu[i - 1]) else fu[i - 1]
        fl[i] = lb[i] if (np.isnan(fl[i - 1]) or lb[i] > fl[i - 1] or c[i - 1] < fl[i - 1]) else fl[i - 1]
        bull[i] = (c[i] > fu[i - 1]) if not bull[i - 1] else not (c[i] < fl[i - 1])
        line[i] = fl[i] if bull[i] else fu[i]
    return pd.Series(line, bars.index), pd.Series(bull, bars.index)


plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "axes.grid": True,
                     "grid.alpha": .25, "axes.titleweight": "bold", "axes.titlesize": 11.5, "axes.titlelocation": "left"})
CH = {}
from matplotlib.ticker import FixedLocator, NullFormatter, NullLocator


def logfmt(ax, ticks, fmt=lambda v: f"₹{v:,.0f}"):
    ax.set_yscale("log"); ax.yaxis.set_major_locator(FixedLocator(ticks)); ax.yaxis.set_minor_locator(NullLocator())
    ax.yaxis.set_minor_formatter(NullFormatter()); ax.yaxis.set_major_formatter(lambda v, _: fmt(v))


def save(fig, name):
    p = IMG / f"{name}.png"; fig.tight_layout(); fig.savefig(p, dpi=170); plt.close(fig); CH[name] = p


# 1. weekly price, EMA61, Supertrend with entry / stop / exit
w0, w1 = "2019-06-01", "2022-09-30"
stl, stb = st_line(wk)
e61w = ema(wk.Close, 61)
ww = wk[w0:w1]
fig, ax = plt.subplots(figsize=(8, 4))
ax.plot(ww.index, ww.Close, color=INK, lw=1.4, label="Weekly close")
ax.plot(ww.index, e61w[w0:w1], color="#2563eb", lw=1.2, label="EMA 61 (weekly)")
sl = stl[w0:w1]; sb = stb[w0:w1]
ax.plot(sl.index, sl.where(sb), color="#16a34a", lw=1.6, label="Supertrend (10, 3) - bullish")
ax.plot(sl.index, sl.where(~sb), color="#dc2626", lw=1.6, label="Supertrend - bearish")
ax.scatter([ENT], [EP], s=70, color=AMBER, zorder=5); ax.annotate(f"Buy ₹{EP:,.0f}", (ENT, EP), (10, 25), textcoords="offset points", color=AMBER, fontweight="bold")
ax.hlines(SP, ENT - pd.Timedelta(days=60), ENT + pd.Timedelta(days=120), color="#dc2626", ls="--", lw=1)
ax.annotate(f"Stop ₹{SP:,.0f}", (ENT + pd.Timedelta(days=125), SP), color="#dc2626", va="center", fontsize=9)
ax.scatter([EXT], [XP], s=70, color="#dc2626", zorder=5); ax.annotate(f"Sell ₹{XP:,.0f}", (EXT, XP), (-80, 25), textcoords="offset points", color="#dc2626", fontweight="bold")
logfmt(ax, [250, 350, 500, 750, 1000, 1500, 2000, 2500]); ax.legend(frameon=False, fontsize=8.5, loc="upper left")
ax.set_title("Persistent Systems, weekly: the whole trade")
save(fig, "trade")

# 2. monthly: close + EMA61 + RSI + StochRSI
m0, m1 = "2016-01-01", "2021-12-31"
r_m, k_m, d_m = stoch_rsi(mo.Close); e61m = ema(mo.Close, 61)
fig, axs = plt.subplots(3, 1, figsize=(8, 6.4), sharex=True, gridspec_kw={"height_ratios": [2.2, 1, 1.2]})
mm_ = mo[m0:m1]
axs[0].plot(mm_.index, mm_.Close, color=INK, lw=1.4, label="Monthly close"); axs[0].plot(mm_.index, e61m[m0:m1], color="#2563eb", lw=1.2, label="EMA 61 (monthly)")
logfmt(axs[0], [250, 350, 500, 750, 1000, 1500, 2000]); axs[0].legend(frameon=False, fontsize=8.5); axs[0].set_title("Persistent Systems, monthly: the setup")
axs[1].plot(r_m[m0:m1].index, r_m[m0:m1], color="#7c3aed", lw=1.3); axs[1].axhline(50, color=GREY, ls="--", lw=1); axs[1].set_ylabel("RSI 14"); axs[1].set_ylim(20, 90)
axs[2].plot(k_m[m0:m1].index, k_m[m0:m1], color="#0891b2", lw=1.3, label="%K"); axs[2].plot(d_m[m0:m1].index, d_m[m0:m1], color=AMBER, lw=1.1, label="%D")
axs[2].axhline(30, color="#dc2626", ls="--", lw=1); axs[2].set_ylabel("StochRSI"); axs[2].legend(frameon=False, fontsize=8.5, loc="upper left")
for a in axs:
    a.axvline(pd.Timestamp("2020-06-30"), color=AMBER, lw=1, alpha=.7)
axs[0].annotate("Setup: June 2020", (pd.Timestamp("2020-06-30"), 1400), (-115, 0), textcoords="offset points", color=AMBER, fontweight="bold", fontsize=9.5)
save(fig, "monthly")
SETUP = mo.loc["2020-06"].index[0] if len(mo.loc["2020-06"]) else None
RSI_SET, K_SET, D_SET = (r_m.loc[SETUP], k_m.loc[SETUP], d_m.loc[SETUP]) if SETUP is not None else (np.nan,) * 3
K_PREV = k_m.shift(1).loc[SETUP] if SETUP is not None else np.nan

# 3. ATR illustration (weekly)
a10 = atr(wk, 10)
fig, axs = plt.subplots(2, 1, figsize=(8, 4.2), sharex=True, gridspec_kw={"height_ratios": [1.6, 1]})
ww2 = wk["2019-06-01":"2022-09-30"]
axs[0].vlines(ww2.index, ww2.Low, ww2.High, color=GREY, lw=2); axs[0].plot(ww2.index, ww2.Close, color=INK, lw=1)
axs[0].set_title("Weekly bars (high to low) and the ATR that measures them"); axs[0].yaxis.set_major_formatter(lambda v, _: f"₹{v:,.0f}")
axs[1].plot(a10["2019-06-01":"2022-09-30"], color=AMBER, lw=1.5); axs[1].set_ylabel("ATR 10 (₹)")
save(fig, "atr")
ATR_ENT = a10.asof(ENT)

# 4. market filter
n5 = data.load(["^CRSLDX"])["Close"]["^CRSLDX"].dropna()
s200 = sma(n5, 200)
x0, x1 = "2018-01-01", "2021-06-30"
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.plot(n5[x0:x1], color=INK, lw=1.2, label="NIFTY 500 index"); ax.plot(s200[x0:x1], color=AMBER, lw=1.6, label="200-day average")
below = (n5 < s200)[x0:x1]
ax.fill_between(below.index, n5[x0:x1].min() * .95, n5[x0:x1].max() * 1.02, where=below, color="#dc2626", alpha=.08, label="Below: no new buys")
ax.legend(frameon=False, fontsize=8.5, loc="upper left"); ax.set_title("The market filter: NIFTY 500 against its 200-day average")
save(fig, "filter")

# 5. R-multiple histogram
fig, ax = plt.subplots(figsize=(8, 3.4))
bins = [-4, -3, -2, -1.5, -1, -.5, 0, .5, 1, 2, 3, 5, 10, 20, 50, 150]
cnt, _ = np.histogram(R.clip(-3.99, 149), bins=bins)
lab = [f"{bins[i]:g} to {bins[i+1]:g}" for i in range(len(bins) - 1)]
ax.bar(range(len(cnt)), cnt, color=["#dc2626" if bins[i + 1] <= 0 else "#16a34a" for i in range(len(cnt))])
ax.set_xticks(range(len(cnt))); ax.set_xticklabels(lab, rotation=45, ha="right", fontsize=8.5); ax.set_ylabel("Trades")
ax.set_title(f"{SID}: every closed trade in R (1R = the planned loss)")
save(fig, "rhist")

# 6. equity vs NIFTY and drawdown
fig, axs = plt.subplots(2, 1, figsize=(8, 5), sharex=True, gridspec_kw={"height_ratios": [1.7, 1]})
axs[0].plot(EQ / EQ.iloc[0] * 10, color=AMBER, lw=1.5, label=f"{SID} ({S['CAGR %']:.1f}%/yr)")
axs[0].plot(NX / NX.iloc[0] * 10, color=GREY, lw=1.1, ls="--", label=f"NIFTY 50 ({N_CAGR:.1f}%/yr)")
logfmt(axs[0], [10, 30, 100, 300, 1000], lambda v: f"₹{v:,.0f} L"); axs[0].legend(frameon=False, fontsize=9, loc="upper left")
axs[0].set_title(f"₹10 lakh from {EQ.index[0]:%B %Y} (log scale)")
axs[1].fill_between(DD.index, DD * 100, 0, color=AMBER, alpha=.5, label=SID)
axs[1].plot((NX / NX.cummax() - 1) * 100, color=GREY, lw=.9, label="NIFTY 50")
axs[1].set_ylabel("Drawdown %"); axs[1].legend(frameon=False, fontsize=8.5, loc="lower left")
save(fig, "equity")

# 7. market-type timeline
T = markettype.types()[START:]
nn = nifty_close().reindex(T.index, method="ffill")
colmap = {"Bull quiet": "#86efac", "Bull volatile": "#16a34a", "Sideways quiet": "#cbd5e1", "Sideways volatile": "#64748b",
          "Bear quiet": "#fca5a5", "Bear volatile": "#dc2626"}
fig, ax = plt.subplots(figsize=(8, 3.6))
ax.plot(nn, color=INK, lw=1); logfmt(ax, [1000, 2000, 5000, 10000, 20000], lambda v: f"{v:,.0f}")
lo, hi = nn.min() * .9, nn.max() * 1.1
for k, c_ in colmap.items():
    ax.fill_between(T.index, lo, hi, where=(T == k), color=c_, alpha=.45, lw=0, label=k)
ax.set_ylim(lo, hi); ax.legend(frameon=False, fontsize=7.8, ncol=3, loc="upper left"); ax.set_title("NIFTY 50 coloured by market type")
save(fig, "mtline")

# 8. random-pick box (reuse study chart if present), time stop / plateau
fig, ax = plt.subplots(figsize=(8, 2.8))
ax.hist(RE.CAGR, bins=30, color=AMBER, alpha=.85); ax.axvline(S["CAGR %"], color=INK, lw=2)
ax.annotate(f"The one backtest path: {S['CAGR %']:.1f}%", (S["CAGR %"], ax.get_ylim()[1] * .85), (8, 0), textcoords="offset points", fontsize=9)
ax.set_xlabel("CAGR % across 200 random-pick runs"); ax.set_title("Random-pick check: same rules, different luck")
save(fig, "random")

# ---------------- the book ----------------
story = []
toc = TableOfContents()
toc.levelStyles = [ParagraphStyle("t0", fontName="Helvetica-Bold", fontSize=13, leading=20, leftIndent=0),
                   ParagraphStyle("t1", fontName="Helvetica", fontSize=11, leading=16, leftIndent=14, textColor=colors.HexColor(GREY))]


class Doc(BaseDocTemplate):
    def afterFlowable(self, f):
        if isinstance(f, Paragraph) and f.style.name in ("H1", "H2"):
            lvl = 0 if f.style.name == "H1" else 1
            if lvl == 0 or getattr(self, "_h2toc", True):
                self.notify("TOCEntry", (lvl, f.getPlainText(), self.page))


def chapter(t):
    return [PageBreak(), Paragraph(t, H1)]


# cover
story += [Spacer(1, 50 * mm), P("Trading concepts, explained", ParagraphStyle("cv", parent=H1, fontSize=34, leading=40)),
          P("R, expectancy, SQN, drawdowns, market types and every indicator in your strategy, in plain words, with the "
            "formulas, the intuition and where each idea came from.", ParagraphStyle("cv2", parent=B, fontSize=15, leading=22)),
          Spacer(1, 10 * mm),
          P(f"Every example uses your chosen strategy <b>{SID}</b> on point-in-time NIFTY 500 data, {EQ.index[0]:%B %Y} to "
            f"{EQ.index[-1]:%B %Y}, computed when this book was built. Worked example: Persistent Systems, July 2020 to May 2022.", B),
          Spacer(1, 60 * mm), P("Research and education only. Not investment advice.", SM),
          PageBreak(), P("Contents", H1), toc]

# ---- chapter 1: the trade, start to finish
story += chapter("1. One trade, start to finish")
story += [P(f"Before the definitions, here is one real trade from the backtest. Every concept in this book shows up in it. "
            f"In June 2020 Persistent Systems gave a monthly setup. It was bought on {ENT:%d %B %Y} at ₹{EP:,.2f}, with a stop "
            f"at ₹{SP:,.2f}, the previous week's low. It was held for almost two years and sold on {EXT:%d %B %Y} at "
            f"₹{XP:,.2f}, when the weekly Supertrend turned bearish."),
          img(CH["trade"], 100, "Green line: Supertrend while bullish, the rope that trails the price. It turned red in May 2022 and "
                                "the trade was sold at the next open."),
          table([["Step", "What happened", "Number"],
                 ["Risk per share", "Entry minus stop", f"₹{EP - SP:,.2f}"],
                 ["Shares", "Sized so the loss to the stop is about 1% of equity", f"{QTY:,}"],
                 ["1R (rupees at risk)", "Shares × risk per share", f"₹{RISK1:,.0f}"],
                 ["Profit after costs", "Sale proceeds minus purchase cost", f"₹{PNL:,.0f}"],
                 ["Result in R", "Profit ÷ 1R", f"{TR_R:+.1f}R"],
                 ["Return on the position", "Profit ÷ cost", f"{tr.proceeds / tr.cost * 100 - 100:+.0f}%"]],
                [40 * mm, 90 * mm, W - 130 * mm]),
          P(f"That single trade earned about {TR_R:.0f} times the money that was put at risk. Most trades do the opposite: they "
            f"lose about 1R and are forgotten. The whole strategy is built to make that trade-off: many small, controlled losses, "
            f"and a few very large wins.")]

# ---- chapter 2: the indicators
story += chapter("2. The indicators")
story += [P("An indicator is just a calculation on past prices that answers one simple question. Each one below has: "
            "the question it answers, how it is worked out, why someone invented it, and exactly how your strategy uses it.")]

story += concept(
    "Moving averages: SMA and EMA",
    plain=["A moving average is the <b>average price over the last N bars</b>, recalculated every bar, so it slides along "
           "with the chart. It smooths away the day-to-day noise and shows the general direction.",
           "<b>SMA</b> (simple) treats every one of the N bars the same. <b>EMA</b> (exponential) gives more weight to recent "
           "bars, so it turns sooner when the trend changes."],
    formula=["SMA(N) = (P1 + P2 + ... + PN) ÷ N", "EMA today = α × Price today + (1 − α) × EMA yesterday",
             "α = 2 ÷ (N + 1)      for N = 61, α ≈ 0.032"],
    body=["Think of the EMA as a running average with a memory that fades. Yesterday's EMA already contains all the "
          "older prices; each new bar nudges it by about 3% (for N = 61) towards today's price. A price far above its "
          "EMA has been rising faster than its own recent history: that is an uptrend."],
    why=["Moving averages were used by traders and statisticians long before computers; they were the easiest way to "
         "draw a trend through noisy data by hand. The exponential form came from engineering, where it was used to "
         "smooth signals cheaply: it needs only yesterday's value and today's price, not a whole window of history.",
         "The number 61 is a trader's choice from the Fibonacci-style family (21, 61, 200) popular with Indian trend "
         "followers. It is not special mathematically; it is slow enough to ignore noise on monthly, weekly and daily charts."],
    rule="Buy only if the close is above EMA 61 on the <b>monthly</b>, the <b>weekly</b> and the <b>daily</b> chart. All "
         "three timeframes must agree that the trend is up.",
    ex=f"Persistent Systems, June 2020: the monthly close was ₹{mo.Close.loc[SETUP]:,.0f} against a monthly EMA 61 of "
       f"₹{e61m.loc[SETUP]:,.0f}. Price was well above its long-term average, so the trend filter passed.",
    warn=["A moving average always lags: it confirms a trend after it has started, never at the bottom.",
          "In a sideways market price crosses the average back and forth; that is why the strategy needs other filters too."])

story += concept(
    "RSI: Relative Strength Index",
    plain=["RSI is a <b>speedometer for a stock</b>. It compares the size of recent up-moves with the size of recent "
           "down-moves and turns the answer into a number from 0 to 100.",
           "Above 50: the up-moves have been bigger, buyers are winning. Below 50: sellers are winning. Near 70 or 30: "
           "the move has been unusually one-sided."],
    formula=["Average gain = Wilder average of the up-moves over 14 bars", "Average loss = Wilder average of the down-moves",
             "RS  = Average gain ÷ Average loss", "RSI = 100 − 100 ÷ (1 + RS)",
             "Wilder average: today = yesterday + (today's move − yesterday) ÷ 14"],
    body=["If gains and losses are equal, RS = 1 and RSI = 50. If there were only gains, RS is huge and RSI approaches 100. "
          "If there were only losses, RS = 0 and RSI = 0. The formula just squeezes the ratio of gains to losses into a "
          "fixed 0 to 100 scale, so every stock can be read the same way."],
    why=["Invented by J. Welles Wilder Jr. and published in 1978 in <i>New Concepts in Technical Trading Systems</i>. Wilder "
         "was a mechanical engineer turned commodity trader. Plain momentum (today's price minus the price N days ago) "
         "jumps around and has no fixed range, so you cannot say what is 'high'. He wanted a smooth momentum measure, "
         "bounded between 0 and 100, that could be compared across any market."],
    rule="Monthly RSI(14) must be above 50: the stock must already have positive momentum. We never buy a stock that is "
         "being pushed down.",
    ex=f"Persistent, June 2020: monthly RSI was {RSI_SET:.1f}, just above 50: momentum had cooled during the dip but was "
       f"still positive.",
    warn="'RSI above 70 means sell' is a common myth. In strong trends RSI can stay above 70 for months. We use RSI only as "
         "a momentum check, not as a sell signal.")

story += concept(
    "StochRSI: the setup",
    plain=["StochRSI is a <b>speedometer of the speedometer</b>. It asks: compared with its own highs and lows of the last "
           "14 bars, where is RSI now? Near the bottom of its range (0) or the top (100)?",
           "For a strong stock, a dip in StochRSI is a <b>pause for breath</b>. When it turns back up from below 30, the "
           "pause is ending and the trend is resuming. That is our buying moment."],
    formula=["Stoch = (RSI − lowest RSI of 14 bars) ÷ (highest RSI − lowest RSI)",
             "%K = 3-bar average of Stoch × 100", "%D = 3-bar average of %K",
             "Setup: %K crosses above %D while %D is below 30 (oversold), on a monthly bar"],
    body=["RSI for a strong stock often spends years between 50 and 70 and never reaches 30, so 'oversold RSI' almost never "
          "happens in the stocks we want. StochRSI stretches RSI's own recent range to fill 0 to 100, so even a small dip "
          "in momentum shows up clearly as a low reading."],
    why=["Introduced by Tushar Chande and Stanley Kroll in <i>The New Technical Trader</i> (1994). They applied George Lane's "
         "Stochastic oscillator (1950s, which places the price within its recent high-low range) to RSI instead of price. "
         "The goal was a more sensitive indicator that gives timely signals even when RSI is stuck in the middle of its range."],
    rule=["On the monthly chart: %K crosses above %D while %D is still below 30, with RSI above 50 and price above EMA 61.",
          "Settings are the platform defaults: RSI 14, Stoch 14, %K 3, %D 3. The oversold level 30 is looser than the more "
          "common 20; tests showed 30 works better here (15.9% CAGR against 13.8% at 20 in the 2000–2026 research runs)."],
    ex=f"Persistent, June 2020: StochRSI %K jumped from {K_PREV:.0f} to {K_SET:.0f} and crossed above %D, which was "
       f"{D_SET:.2f}, just below 30. RSI was {RSI_SET:.1f}, just above 50. A strong stock that had paused, turning up again: a setup.",
    extra=[img(CH["monthly"], 125, "Top: monthly price and EMA 61. Middle: RSI with the 50 line. Bottom: StochRSI with the "
                                   "30 line. The amber line marks the June 2020 setup.")],
    warn="StochRSI is fast and noisy on its own. It only works here because the trend filters (EMA 61, RSI above 50, the "
         "market filter) make sure we are buying a dip in an uptrend, not catching a falling knife.")

story += concept(
    "ATR: Average True Range",
    plain="ATR measures <b>how much a stock normally moves in one bar</b>, in rupees. A stock with a weekly ATR of ₹40 "
          "usually swings about ₹40 a week. It says nothing about direction, only about size.",
    formula=["True range = the largest of:", "    High − Low", "    |High − previous close|", "    |Low − previous close|",
             "ATR(N) = Wilder average of the true range over N bars"],
    body=["The 'true' in true range handles gaps. If a stock closed at ₹100 and opened the next day at ₹110 and traded "
          "between 110 and 112, the high-low range is only ₹2, but the stock really moved ₹12. True range counts the ₹12."],
    why="Also from Wilder (1978). Commodity futures often gapped or hit limit moves, so the simple daily range understated "
        "how much a position could really move against you. Wilder needed a volatility measure for setting stops and sizing "
        "positions that included those gaps.",
    rule="ATR is used inside the Supertrend exit: weekly ATR averaged over 10 weeks. It is not used for sizing; position "
         "size comes from the stop at the previous week's low.",
    ex=f"Persistent, week of entry: weekly ATR(10) was about ₹{ATR_ENT:,.0f}, about {ATR_ENT / EP * 100:.0f}% of the price.",
    extra=[img(CH["atr"], 95, "Grey bars: each week's high-to-low range. Amber: the 10-week ATR that averages them. "
                             "ATR rises when the stock becomes jumpy and falls when it calms down.")])

story += concept(
    "Supertrend: the exit",
    plain=["Supertrend is a <b>safety rope that follows the price up but never comes down</b>. It hangs below the price at "
           "a distance of 3 × ATR. As the price rises the rope is pulled up; when the price falls, the rope stays where it is.",
           "When a weekly close falls through the rope, the trend is broken: the indicator flips from bullish (green) to "
           "bearish (red), and we sell."],
    formula=["Middle = (High + Low) ÷ 2", "Lower band = Middle − 3 × ATR(10)",
             "Upper band = Middle + 3 × ATR(10)",
             "While bullish: line = the higher of (today's lower band, yesterday's line)",
             "Flip to bearish when the close falls below the line; then the line",
             "follows the upper band downwards in the same way"],
    body=["Because the rope is measured in ATRs, it adapts to the stock: a calm stock gets a short rope and a jumpy one a "
          "longer rope, so normal wiggles do not shake you out. Because it only ratchets one way, it locks in more of the "
          "gain as the trend extends."],
    why=["Credited to the French trader Olivier Seban, it became popular in the 2000s and is now a default on almost every "
         "Indian charting platform. It belongs to the family of volatility trailing stops that goes back to Wilder's own "
         "'volatility stop' (1978) and Chuck LeBeau's Chandelier exit: give the trade room in proportion to its normal "
         "movement, then trail it.",
         "The (10, 3) setting is the standard default. Tests found (14, 3) slightly better (Sa1f19d11), but the result is "
         "sensitive to the multiplier, so the default was kept."],
    rule=["Weekly Supertrend(10, 3). Sell at the next open after a weekly close in which it turns from bullish to bearish "
          "<b>after</b> the purchase.",
          "A trade bought while the Supertrend is already bearish is held until it turns bullish and then bearish again "
          "(or until the stop or time stop)."],
    ex=f"Persistent: the Supertrend stayed bullish for almost two years, through several 10–15% dips, and flipped in May "
       f"2022. Sold at ₹{XP:,.0f}: {TR_R:+.0f}R.",
    warn="Supertrend gives back part of the gain by design: it sells only after the trend has turned. Selling earlier "
         "'to protect profits' is how the big winners, which pay for all the losers, get cut short.")

story += concept(
    "The 200-day average: market filter",
    plain="The 200-day average of the NIFTY 500 index is the market's <b>long-term mood line</b>. Above it, the weather is "
          "fair and we take new trades. Below it, storms are more likely and we take no new trades.",
    formula=["SMA200 = average of the last 200 daily closes of the NIFTY 500 index",
             "New buys allowed only if yesterday's close > yesterday's SMA200"],
    why="The 200-day average is the most widely used long-term trend line in markets; fund managers and the financial "
        "press watch it. Studies of trend timing (for example Mebane Faber's 2007 paper, using the very similar 10-month "
        "average) found that staying out of the market below it avoided most of the worst bear-market losses at the cost "
        "of some missed rebounds.",
    rule=["No new entries while the NIFTY 500 index is below its 200-day average (previous close). Open trades are not "
          "sold because of it; they keep their own stops and exits.",
          "Before mid-2006, when the NIFTY 500's average first exists in the data, NIFTY 50 / Sensex is used instead."],
    extra=[img(CH["filter"], 88, "Shaded: days with the index below its average, when no new trades were taken (2018 "
                                "mid-caps fall, the March 2020 crash).")],
    warn="The filter cannot cut a sudden crash that starts from a high (May 2006): the index is still above its average "
         "when the fall begins. It mainly helps in long, grinding bear markets.")

story += concept(
    "The stop: previous week's low",
    plain="The stop is the price at which we admit the trade is wrong and get out. Ours is the <b>low of the previous "
          "week</b>: if the stock breaks below last week's low, the dip we bought has turned into a fall.",
    formula=["Stop = lowest price of the last completed week before entry",
             "Risk per share = Entry − Stop", "Placed as a stop-loss order on entry; never moved down"],
    why="A structural stop: it is placed where the chart says the idea is wrong, not at an arbitrary percentage. A "
        "percentage stop (say 8%) is too tight for jumpy stocks and too loose for calm ones.",
    ex=f"Persistent: the previous week's low was ₹{SP:,.2f}, {(EP - SP) / EP * 100:.1f}% below the entry. "
       f"The median stop across all trades is {S['Median stop %']:.1f}%.",
    warn="Stops are not guaranteed. If a stock gaps down below the stop (results, bad news), you are sold at the open, "
         f"below the stop. The worst trade in the backtest lost {R.min():.1f}R, not 1R, for that reason.")

story += concept(
    "The time stop",
    plain="If a trade has done <b>nothing useful in 25 trading days</b>, we sell it. A good trade in this strategy usually "
          "starts working quickly; one that just sits there ties up money and a slot.",
    formula=["After 25 trading days: if (Close − Entry) < 0.25 × (Entry − Stop), sell at the next open",
             "i.e. the trade must be at least 0.25R in profit by day 25"],
    why="Time stops come from the trading literature on trend following: a trend trade is a bet that something will "
        "happen soon. If it has not, the reason for the trade is weaker, and the money is better used elsewhere.",
    rule="25 days, 0.25R. Tests of 20, 25 and 30 days with 0.25R and 0.5R all gave 15–17% CAGR, so the exact numbers "
         "are not critical: it is a robust rule, not a fitted one.")

story += concept(
    "Idle cash, costs and slippage",
    plain=["When fewer than 10 positions are open, the spare cash sits in a <b>liquid fund</b> (or LiquidBeES). The "
           "backtest credits it 6.5% a year. Without this, the strategy earns about 3.5 points a year less.",
           "Every trade pays <b>costs</b>: STT, brokerage, exchange charges, GST, SEBI fee and stamp duty, plus 0.1% "
           "<b>slippage</b> (the gap between the price you wanted and the price you got)."],
    formula=["Cash interest per day = (1 + 6.5%)^(1/252) − 1",
             f"Costs as a share of gross profit (this strategy): {M['cost_pct']:.0f}%"],
    warn="A backtest without costs is fiction. Zero-brokerage delivery (e.g. Zerodha) added about 1.9 points a year in "
         "the tests.")

# ---- chapter 3: risk building blocks
story += chapter("3. Risk and position size")
story += concept(
    "R: the unit of risk",
    plain=["<b>R is the money you lose if the stop is hit.</b> It is decided before the trade, from the entry and the "
           "stop. Everything else is then measured in R.",
           "A profit of 3 times what you risked is <b>+3R</b>. A normal stop-out is <b>−1R</b>. A gap through the stop "
           "might be −1.5R."],
    formula=["1R = (Entry − Stop) × Shares", "R-multiple of a trade = Profit or loss ÷ 1R"],
    body=["R is <b>not</b> the reward-to-risk ratio. A reward-to-risk ratio is a plan made before the trade (target "
          "distance ÷ stop distance). An R-multiple is the actual result after the trade. Our strategy has no target, so "
          "it has no fixed reward-to-risk ratio; the trend exit decides how many R a winner makes."],
    why="Popularised by Van K. Tharp in <i>Trade Your Way to Financial Freedom</i> (1998). Measuring in R lets you compare "
        "trades of different sizes, stocks and years on one scale, and separates the quality of the system from the size "
        "of the bets.",
    ex=f"Persistent: 1R was ₹{RISK1:,.0f} and the trade made {TR_R:+.1f}R.")

story += concept(
    "Risk per trade and position size",
    plain="We decide how much we are willing to lose first (1% of the account), then work out how many shares that "
          "allows. Position size comes from the stop, never the other way round.",
    formula=["Rupees at risk = 1% × current equity", "Shares = Rupees at risk ÷ (Entry − Stop)",
             "Capped so the position is at most 20% of equity when bought"],
    ex=f"With ₹10 lakh: ₹10,000 at risk. A ₹500 stock with a stop at ₹465 has ₹35 risk per share, so 285 shares (₹1.43 lakh). "
       f"With the stop at ₹490 (₹10 risk) the formula says 1,000 shares (₹5 lakh), but the 20% cap limits it to ₹2 lakh.",
    rule=["1% risk per trade, at most 10 open positions, no position above 20% of equity when bought (and trimmed to 20% "
          "at month end).",
          f"Cash-capped entries (the cap or the cash ran out before the full size): {S['Cash-capped entries %']:.0f}% of trades."],
    warn="A tight stop makes a big position. The 20% cap exists because a stock that gaps 50% on a tight-stop position "
         "could otherwise cost far more than 1R.")

story += concept(
    "The drawdown rule",
    plain="When the account falls 10% from its highest point, we halve the risk per trade (0.5%). At a 15% fall we stop "
          "new trades for 21 days. Full size comes back only at a new equity high.",
    formula=["Drawdown = Equity ÷ highest equity so far − 1",
             "Drawdown ≤ −10%: risk 0.5% per trade", "Drawdown ≤ −15%: no new trades for 21 days",
             "New equity high: back to 1%"],
    why="A rule from professional risk management: when a system is out of step with the market, bet less until it "
        "proves itself again. It shrinks losses in the bad stretches at the cost of a slower recovery. The full logic is in "
        "the separate sizing note (sizing_rule.pdf).")

# ---- chapter 4: per-trade statistics
story += chapter("4. Trade statistics")
story += [img(CH["rhist"], 88, f"{len(R)} closed trades. Most cluster just below 0R (small losses and time stops); a long "
                               f"tail of winners reaches {R.max():.0f}R.")]
story += concept(
    "Win rate, average win and average loss",
    plain="Win rate is simply the share of trades that made money after costs. On its own it says almost nothing: a "
          "system can win 90% of the time and still lose money, or win 23% of the time and make a lot.",
    formula=["Win % = winning trades ÷ all closed trades", "Average win % = average return of the winners",
             "Average loss % = average return of the losers"],
    ex=f"{SID}: {M['win']:.0f}% winners ({M['n_win']} of {M['trades']}). Average win {M['avg_win']:+.1f}%, average loss "
       f"{M['avg_loss']:+.1f}%. Median trade {S['Median trade %']:+.1f}%: the typical trade loses a little.")

story += concept(
    "Payoff ratio",
    plain="How big the average win is compared with the average loss. A payoff of 3 means wins are three times the size "
          "of losses.",
    formula="Payoff = Average win % ÷ |Average loss %|",
    ex=f"{SID}: {M['payoff']:.1f}. Wins are about {M['payoff']:.0f} times larger than losses, which is why a 23% win rate "
       f"is enough.",
    body=["Win rate and payoff pull against each other. Tight targets give a high win rate and a low payoff; letting "
          "winners run gives a low win rate and a high payoff. Neither is better on its own; expectancy combines them."])

story += concept(
    "Expectancy",
    plain="What you can expect to make, <b>on average, per trade, for every rupee you risk</b>. It is the single most "
          "important number for a trading system: positive means the system makes money over many trades.",
    formula=["Expectancy (in R) = average of all R-multiples",
             "             = Win% × Average win (R) − Loss% × Average loss (R)"],
    body=[f"Check with {SID}: {M['win'] / 100:.2f} × {C.R[C.R > 0].mean():.1f}R − {1 - M['win'] / 100:.2f} × "
          f"{-C.R[C.R <= 0].mean():.2f}R ≈ {M['exp_r']:+.2f}R per trade."],
    ex=[f"Expectancy {M['exp_r']:+.2f}R: on average each trade makes 2.3 times what it risks.",
        f"Without the 10 best trades it is {X10.mean():+.2f}R: still positive, but the big winners carry most of the result."],
    why="Expectancy is the trader's version of 'expected value' from probability theory. Van Tharp put it at the centre "
        "of system design: you cannot judge a system by its win rate or its best trades, only by what it makes per unit "
        "risked, over many trades.",
    warn="Tharp also stressed opportunity: a 0.5R system that trades 200 times a year can beat a 3R system that trades "
         f"5 times. {SID} trades about {M['tpy']:.0f} times a year.")

story += concept(
    "Profit factor, losing streaks and the rest",
    formula=["Profit factor = Gross profit ÷ |Gross loss|",
             "Max losing streak = most losing trades in a row (by exit date)",
             "Trades per year = closed trades ÷ years"],
    body=[f"Profit factor {M['pf']:.2f}: for every ₹1 lost, ₹{M['pf']:.2f} was won. Above 1.5 is healthy for a trend system.",
          f"Max losing streak {M['streak']} trades. With 1 trade in 4 winning, long streaks are normal: the chance of 20 "
          f"losses in a row in a run of 400 trades is high. Plan for it before it happens.",
          f"Median holding period {S['Median hold days']:.0f} days (most trades end at the time stop or the stop); average "
          f"{S['Avg hold days']:.0f} days (the winners are held for one to three years)."])

# ---- chapter 5: SQN
story += chapter("5. Van Tharp's System Quality Number (SQN)")
story += concept(
    "SQN",
    plain=["Expectancy tells you how much a system makes per trade. SQN tells you <b>how reliably</b> it makes it. A high "
           "SQN means results arrive steadily; a low SQN means they are lumpy and depend on a few big trades.",
           "It is like a signal-to-noise ratio: the average result (signal) divided by how scattered the results are "
           "(noise), scaled up by the number of trades."],
    formula=["SQN = (Average R ÷ Standard deviation of R) × √N", "N = number of trades, capped at 100"],
    body=["Why √N: the more trades you have, the more confident you can be that a positive average is real and not luck. "
          "This is the same maths as a t-statistic in statistics. Tharp capped N at 100 so that a system cannot look "
          "excellent simply by trading very often."],
    why="Developed by Van K. Tharp and described in <i>The Definitive Guide to Position Sizing</i> (2008). He used it to "
        "rate systems and to decide how aggressively they can be sized: the higher the SQN, the more risk per trade the "
        "system can carry for a given drawdown.",
    extra=[table([["SQN", "Tharp's rating"], ["1.6 – 1.9", "Poor, but tradable"], ["2.0 – 2.4", "Average"],
                  ["2.5 – 2.9", "Good"], ["3.0 – 5.0", "Excellent"], ["5.1 – 6.9", "Superb"], ["7 and above", "'Holy grail'"]],
                 [40 * mm, 60 * mm], hl=1)],
    ex=[f"{SID}: average R {M['exp_r']:+.2f}, standard deviation {M['r_sd']:.1f}R. SQN = {M['exp_r']:.2f} ÷ {M['r_sd']:.1f} "
        f"× √100 = <b>{M['sqn']:.1f}</b> (poor but tradable). On all {M['trades']} trades: {M['sqn_all']:.1f}.",
        "The low score comes from the big winners: a +137R trade makes the spread of results very wide. SQN treats a "
        "huge win as 'noise' just like a huge loss."],
    warn=["SQN penalises trend-following systems for their best feature. Read it together with expectancy and the "
          "worst trade: our losses are tightly controlled (average loss about 1R); it is the wins that are scattered.",
          "The practical lesson is the same as Tharp's: a low-SQN system must be traded at modest risk (1%), and you must "
          "take every signal, because missing a few big winners changes everything."])

# ---- chapter 6: account level
story += chapter("6. Account results")
story += [img(CH["equity"], 115, f"Top: ₹10 lakh invested in {EQ.index[0]:%B %Y}. Bottom: how far each was below its own peak.")]
story += concept(
    "CAGR: compound annual growth rate",
    plain="The steady yearly growth rate that would turn the starting amount into the final amount. It smooths a bumpy "
          "path into one number.",
    formula="CAGR = (Final equity ÷ Starting equity)^(1 ÷ years) − 1",
    ex=f"{SID}: {S['CAGR %']:.1f}% a year over {YRS:.1f} years, against {N_CAGR:.1f}% for NIFTY 50 (price only, no "
       f"dividends). ₹10 lakh would have become about ₹{10 * EQ.iloc[-1] / EQ.iloc[0] / 100:,.1f} crore.",
    warn="CAGR hides the path. Two systems with the same CAGR can have very different drawdowns. It is also a "
         "consequence of position size: the same system at 2% risk shows a different CAGR.")

story += concept(
    "Maximum drawdown and time under water",
    plain="Drawdown is how far the account is below its highest point so far. The maximum drawdown is the worst such fall. "
          "Time under water is how long it took to get back to the old high.",
    formula=["Drawdown(t) = Equity(t) ÷ highest equity up to t − 1", "Max drawdown = the most negative drawdown"],
    ex=f"{SID}: {S['Max DD %']:.1f}% (May–June 2006). NIFTY 50: {N_DD:.0f}% (2008). Longest time under water: about "
       f"{UW:.1f} years.",
    why="Drawdown is what makes traders quit. A risk manager reads it before CAGR: the question is not 'how much can I "
        "make?' but 'how much can I lose before it comes back, and can I sit through it?'")

story += concept(
    "CAGR / DD (MAR ratio)",
    plain="Return per unit of pain: how many points of yearly return you get for each point of worst drawdown.",
    formula="CAGR / DD = CAGR % ÷ |Max drawdown %|",
    ex=f"{SID}: {M['mar']:.2f}. Above 0.5 is good for a long-only stock strategy; NIFTY 50 buy-and-hold is about "
       f"{N_CAGR / -N_DD:.2f}.",
    why="Named after <i>Managed Accounts Reports</i>, a newsletter that ranked commodity trading advisers by return "
        "divided by maximum drawdown.")

story += concept(
    "Deployed %, slots and skipped signals",
    formula=["Deployed % = value of open positions ÷ equity, averaged over all days",
             "Skipped = signals not taken (slots full, cash used up, or a pause)"],
    body=[f"{SID} is {S['Avg deployed %']:.0f}% invested on an average day and fully invested (all 10 slots used) on "
          f"{S['Days all slots full %']:.0f}% of days. It holds no positions at all on {S['Days with 0 positions %']:.0f}% of days.",
          f"{int(S['Signals skipped'])} signals were skipped because the slots were full. Which ones got taken is partly "
          f"luck; that is what the random-pick check measures."])

# ---- chapter 7: market types
story += chapter("7. Market types")
story += concept(
    "Direction × volatility",
    plain=["Every day is given two labels. <b>Direction</b>: has the market gone up, down or nowhere over the last three "
           "months? <b>Volatility</b>: are daily moves bigger or smaller than usual? Together they make six market types.",
           "The point is to see <b>where a strategy earns and where it bleeds</b>, so you know what to expect in each kind "
           "of market."],
    formula=["13-week change = NIFTY close ÷ close 65 trading days earlier − 1",
             "Bull: above +5%    Sideways: −5% to +5%    Bear: below −5%",
             "Volatility = standard deviation of daily returns over 20 days",
             "Volatile: above its own median of the last 3 years; Quiet: at or below",
             "Uses data up to the previous close only"],
    why="Van Tharp argued that no system works in every market, and that a trader should know which 'market type' a system "
        "is built for. He classified markets by direction and volatility. The ±5% and 3-year-median thresholds here are "
        "simple, round choices, not tuned to the results.",
    extra=[img(CH["mtline"], 88, "Green: bull markets. Grey: sideways. Red: bear. Darker shades are volatile."),
           table([["Type", "What it looks like", "Examples"],
                  ["Bull quiet", "Steady grind up, small daily moves", "2003–04, 2017, 2023–24"],
                  ["Bull volatile", "Strong rally with big swings", "2009 recovery, late 2020"],
                  ["Sideways quiet", "Drifting in a range", "Range-bound months"],
                  ["Sideways volatile", "Choppy: big swings, no progress", "2011, 2015–16, 2018–19"],
                  ["Bear quiet", "Slow bleed", "Parts of 2011–12"],
                  ["Bear volatile", "Crash, then sharp rebounds", "2008, March–May 2020, May 2006"]],
                 [36 * mm, 70 * mm, W - 106 * mm])])
story += [P("Your strategy by market type", H3), table(MT, [32 * mm, 15 * mm, 23 * mm, 21 * mm, 15 * mm, 14 * mm, 22 * mm, W - 142 * mm]),
          P("<b>How to read it.</b> Days % is the share of trading days of each type. Strategy / yr and NIFTY / yr are the "
            "returns earned on those days, annualised. Trades, win % and expectancy are for trades <i>bought</i> on days "
            "of that type. Share of R is that type's part of all R earned."),
          box("ex", ["Bull markets and quiet sideways markets earn almost all the R.",
                     "Choppy, volatile sideways markets are where trades lose (expectancy below zero), but the account "
                     "still beats NIFTY there by losing less: exits and the market filter keep it out of the damage. "
                     "That is where most of the lead over the index comes from.",
                     "In bear markets the filter keeps the strategy mostly in cash. It avoids the crash days and also "
                     "misses the sharp rebounds, which is why NIFTY shows a positive return in 'bear volatile'."]),
          box("warn", "Labels look backwards, so turning points are blurred: the first rebound days after a crash are still "
                      "'bear', and the first days of a fall may still be 'bull'.")]

# ---- chapter 8: robustness
story += chapter("8. Is it real? Robustness checks")
story += concept(
    "Backtest traps",
    plain=["<b>Look-ahead bias</b>: using information you would not have had at the time (for example today's close to "
           "decide today's trade). Every rule here uses the previous close or completed bars.",
           "<b>Survivorship bias</b>: testing only on today's index members, which are by definition the winners. This "
           "backtest uses <b>point-in-time</b> NIFTY 500 membership: a stock can be bought only while it was in the "
           "index at that time.",
           "<b>Overfitting</b>: tuning rules until they fit the past perfectly. Signs: many parameters, results that "
           "collapse when a setting is nudged, and great numbers that never repeat live."])
story += concept(
    "Random-pick check",
    plain="On many days there are more signals than free slots, so the backtest has to choose. The random-pick check "
          "reruns the whole backtest 200 times, choosing at random among same-day signals each time. It shows how much "
          "of the result is the rules and how much is the luck of which signals were filled.",
    extra=[img(CH["random"], 70)],
    ex=f"{SID}: median {RE.CAGR.median():.1f}% CAGR (5th–95th percentile {RE.CAGR.quantile(.05):.1f}–"
       f"{RE.CAGR.quantile(.95):.1f}%), median drawdown {RE.DD.median():.1f}%. The single backtest path ({S['CAGR %']:.1f}%) "
       f"is inside the range, so it was not a lucky outlier.",
    warn="When comparing two strategies, compare their random-pick distributions, not their single paths. Most 'improvements' "
         "that looked like +2 points on one path were within the luck range.")
story += concept(
    "Neighbours: plateau or peak?",
    plain="A good setting has good neighbours. If 25 days works and 20 and 30 days work almost as well, the rule sits on a "
          "<b>plateau</b>: robust. If one setting is great and its neighbours are poor, it sits on a <b>peak</b>: probably "
          "fitted to the past.",
    ex=["Time stop: 20, 25 and 30 days with 0.25R or 0.5R all gave 15–17%. A plateau.",
        "Supertrend: at ATR 10, multipliers 2 to 4 all gave about 16%. A plateau. At ATR 14, multiplier 3 gave 18% but "
        "2.5 gave 15%. A peak, so (14, 3) was not adopted.",
        "StochRSI oversold (2000–2026 research runs): 30 gave 15.9%, 25 gave 14.0% and 20 gave 13.8%. A slope: the setting matters."])
story += concept(
    "Walk-forward and rolling windows",
    plain="Split the history into periods (2000–04, 2005–09, and so on) and check the strategy in each. A real edge works "
          "in most periods; a fitted one works in one and fails in the others. Rolling 5-year windows ask the same "
          "question from every possible start day.")
story += concept(
    "Risk of ruin and the bootstrap",
    plain="The bootstrap builds thousands of alternative histories by shuffling the strategy's monthly returns in "
          "12-month blocks, then measures the worst drawdown in each. It estimates how bad things could get in a future "
          "that is like the past but in a different order.",
    formula=["Repeat 20,000 times: pick random 12-month blocks of monthly returns until 20 years are filled",
             "Record the worst drawdown and the final value of each history"],
    why="The bootstrap was introduced by the statistician Bradley Efron in 1979. Using blocks (rather than single months) "
        "keeps the streaks and clusters that real markets have.",
    ex="Results for your strategy are in the risk-of-ruin report (results/studies/ruin/report.pdf).")

# ---- chapter 9: glossary
story += chapter("9. Quick reference")
gl = [["Term", "Meaning", f"{SID}"],
      ["R", "Rupees lost if the stop is hit: (entry − stop) × shares", "≈1% of equity"],
      ["R-multiple", "Trade result ÷ R", f"best {R.max():.0f}R, worst {R.min():.1f}R"],
      ["Expectancy", "Average R per trade", f"{M['exp_r']:+.2f}R"],
      ["Win %", "Share of trades that made money", f"{M['win']:.0f}%"],
      ["Payoff", "Average win % ÷ average loss %", f"{M['payoff']:.1f}"],
      ["Profit factor", "Gross profit ÷ gross loss", f"{M['pf']:.2f}"],
      ["SQN", "Average R ÷ std dev of R × √(N, max 100)", f"{M['sqn']:.1f}"],
      ["CAGR", "Steady yearly growth rate", f"{S['CAGR %']:.1f}%"],
      ["Max drawdown", "Worst fall from a peak", f"{S['Max DD %']:.1f}%"],
      ["CAGR / DD", "Return per unit of drawdown", f"{M['mar']:.2f}"],
      ["Losing streak", "Most losses in a row", f"{M['streak']}"],
      ["Trades / yr", "Closed trades per year", f"{M['tpy']:.0f}"],
      ["Deployed %", "Average share of equity invested", f"{S['Avg deployed %']:.0f}%"],
      ["Costs % of gross", "Fees and slippage ÷ profit before costs", f"{M['cost_pct']:.0f}%"],
      ["EMA 61", "Weighted average of 61 bars; trend filter on M, W, D", "close above"],
      ["RSI 14", "Up-moves vs down-moves, 0–100", "monthly above 50"],
      ["StochRSI", "RSI within its own 14-bar range", "monthly %K crosses %D, %D < 30"],
      ["ATR", "Average size of a bar, gaps included", "weekly, 10 bars"],
      ["Supertrend", "Trailing rope 3 ATR below price", "weekly (10, 3), exit on flip"],
      ["200-day average", "Long-term market trend line", "NIFTY 500, entries only above"],
      ["Time stop", "Exit if not 0.25R up after 25 days", "25 days, 0.25R"],
      ["Market type", "Direction (13 weeks ±5%) × volatility (20 days vs 3-year median)", "6 types"],
      ["Random-pick median", "Median CAGR over 200 runs with random signal choice", f"{RE.CAGR.median():.1f}%"]]
story += [table(gl, [34 * mm, 92 * mm, W - 126 * mm]),
          P(f"Strategy {SID} ({ids.by_name().get('stexit/A_flip_capentry', '')}). Built from {RUN.relative_to(ROOT).as_posix()}.", SM),
          P("Rebuild: python reports/notes/concepts_report.py", SM),
          P("Research and education only; not investment advice.", SM)]


def page(cv, d):
    cv.saveState()
    if d.page > 1:
        cv.setFont("Helvetica", 8.5); cv.setFillColor(colors.HexColor(GREY))
        cv.drawString(20 * mm, 12 * mm, "Trading concepts, explained")
        cv.drawRightString(A4[0] - 20 * mm, 12 * mm, f"{d.page}")
        cv.setStrokeColor(colors.HexColor(AMBER)); cv.setLineWidth(1.2)
        cv.line(20 * mm, A4[1] - 13 * mm, A4[0] - 20 * mm, A4[1] - 13 * mm)
    else:
        cv.setFillColor(colors.HexColor(AMBER)); cv.rect(0, A4[1] - 18 * mm, A4[0], 18 * mm, fill=1, stroke=0)
    cv.restoreState()


doc = Doc(str(OUT / "concepts.pdf"), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
          bottomMargin=18 * mm, title="Trading concepts, explained", author="backtest")
doc.addPageTemplates([PageTemplate(id="p", frames=[Frame(20 * mm, 18 * mm, W, A4[1] - 36 * mm, id="f")], onPage=page)])
doc.multiBuild(story)
print("wrote", OUT / "concepts.pdf")
