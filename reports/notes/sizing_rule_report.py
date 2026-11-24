"""Build reports/notes/sizing_rule.pdf: how S44984096 sizes trades (1% of equity + drawdown rule), with how often
the rule triggered, computed from results/stexit/A_flip_capentry/nifty500_pit/equity.csv."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import pandas as pd
import lib.pdffont  # noqa: F401  (DejaVu glyphs for ₹ and −)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle

OUT = ROOT / "reports" / "notes" / "sizing_rule.pdf"
from lib import bookstyle as bs
from lib.bookstyle import H1, SUB, H2, P, SM, bl, table
B = bs.N
DARK, GREY, AMBER = bs.INK, bs.GREY, bs.AMBER


# replay the rule on the saved equity curve (same logic as lib/portfolio.py, previous close)
e = pd.read_csv(ROOT / "results/stexit/A_flip_capentry/nifty500_pit/equity.csv", index_col=0, parse_dates=True).iloc[:, 0].dropna()
prev = e.shift(1).dropna()
pk, halved, used, left, nh, npz, hs, ps, state = 0, False, False, 0, 0, 0, [], [], {}
for d, v in prev.items():
    pk = max(pk, v); x = (1 - v / pk) * 100
    if v >= pk:
        halved = used = False
    if x >= 10 and not halved:
        halved = True; hs.append(d)
    if x >= 15 and not used:
        used, left = True, 21; ps.append(d)
    if left > 0:
        left -= 1; npz += 1
    elif halved:
        nh += 1
    state[d] = "half" if halved else "full"
maxdd = (e / e.cummax() - 1).min() * 100
from lib import portfolio
_ent = pd.to_datetime(portfolio.read_fills(ROOT / "results/stexit/A_flip_capentry/nifty500_pit/fills_none.csv")["entry_date"])
ntr = len(_ent)
nhalf = sum(state.get(d) == "half" for d in _ent)

story = [Paragraph("Position sizing and the drawdown rule", H1),
         Paragraph("S44984096 (your choice): 1% risk, 10 slots, 20% position cap (at entry and at month end), halve at −10%, pause 21 days at −15%. "
                   "Logic as coded in lib/portfolio.py.", SUB),
         Paragraph("Part 1: normal sizing, 1% of current equity", H2)] + bl([
    "Each new trade risks <b>1% of the account value at the previous day's close</b>, open positions marked to market.",
    "Quantity = risk ÷ (entry − stop). ₹10 lakh account, stock at ₹500 with stop ₹460: risk ₹10,000, so "
    "₹10,000 ÷ ₹40 = 250 shares (₹1.25 lakh).",
    "Because it is a share of <i>current</i> equity, risk shrinks as the account falls (₹9 lakh → ₹9,000).",
    "If the stop is very close, the position would be large: it is limited to 20% of equity when bought (and by cash), and at each month-end "
    "a position worth more than 20% of equity is trimmed back to 20%."])
story += [Paragraph("Part 2: the drawdown rule", H2)] + bl([
    "<b>Equity high (peak)</b>: the highest closing value the account has reached.",
    "<b>At a 10% fall from the peak, risk is halved</b>: new trades are sized at <b>0.5% of current equity</b>. Peak "
    "₹20 lakh, account ₹18 lakh: a new trade risks 0.5% × ₹18 lakh = ₹9,000 instead of ₹20,000 at the peak.",
    "<b>Open positions are not touched</b>: same size, stop and exits. Only new entries are smaller.",
    "<b>Half risk stays on until the account closes at a new high</b>, not when it recovers to −5%.",
    "<b>At a 15% fall, new trades stop for 21 trading days</b> (about a month). Signals in that month are skipped, not "
    "queued. Open positions run normally.",
    "<b>The pause happens once per drawdown.</b> No second pause at −20% or −25%; after the pause, trades resume at "
    "half risk. Both the half-risk state and the one pause reset only at a new equity high."])
story += [Paragraph("Walk-through: ₹20 lakh peak", H2),
          table([["Account", "Status", "Risk on a new trade"],
                 ["₹20.0 L (peak)", "Normal", "1% = ₹20,000"], ["₹18.6 L (−7%)", "Normal", "1% = ₹18,600"],
                 ["₹18.0 L (−10%)", "Half risk", "0.5% = ₹9,000"], ["₹17.0 L (−15%)", "Paused 21 trading days", "No new trades"],
                 ["₹16.5 L, pause ends", "Half risk", "0.5% = ₹8,250"],
                 ["₹19.5 L (−2.5%)", "Still half risk", "0.5% = ₹9,750"],
                 ["₹20.1 L (new high)", "Back to normal", "1% = ₹20,100"]], [45 * mm, 60 * mm, 50 * mm])]
story += [Paragraph("How often it triggered, 2006–2026", H2)] + bl([
    f"<b>Half risk started {len(hs)} times:</b> " + ", ".join(f"{d:%b %Y}" for d in hs) + ".",
    f"<b>The 21-day pause happened {len(ps)} times:</b> " + ", ".join(f"{d:%b %Y}" for d in ps) + ".",
    f"<b>The account was at half risk on {nh / len(prev) * 100:.0f}% of trading days</b> and paused on {npz} days: "
    "recoveries to a new high often take a year or more."])
story += [Paragraph("What it means", H2)] + bl([
    f"The rule is a large part of why the worst drawdown stayed at {maxdd:.1f}%: losses slow down as they build.",
    f"The price: {nhalf} of {ntr} trades ({nhalf / ntr * 100:.0f}%) were entered while risk was halved, so much of "
    "the time the strategy really ran at 0.5% risk, not 1%, and earned less during long recoveries. Part of the CAGR "
    "is traded for safety.",
    "In live trading, follow it mechanically: compute the peak from your own account statement each day, and size "
    "the next trade from the previous close."])
from lib import markettype
story += markettype.big(ROOT / "results" / "stexit" / "A_flip_capentry" / "nifty500_pit")
story.append(Paragraph("Research and education only, not investment advice.", SUB))
bs.build(OUT, story, "Position sizing and the drawdown rule")
print("wrote", OUT)
