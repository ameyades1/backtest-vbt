"""Build reports/notes/strategy_guide.pdf: step-by-step trading guide for Sf5b94362 (your choice).

Every rule here is written from the code that ran the backtest (lib/engine.py, lib/portfolio.py, run_strategy.py,
strategies/stexit/A_flip.json). Also bundled at the front of each replay workbook (studies/replay.py).
"""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import lib.pdffont  # noqa: F401  (DejaVu glyphs for ₹ and −)
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, PageBreak, KeepTogether
from lib import costs

OUT = ROOT / "reports" / "notes" / "strategy_guide.pdf"
DARK, GREY, AMBER = "#0f172a", "#64748b", "#b45309"
ss = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=ss["Title"], textColor=colors.HexColor(DARK), fontSize=19, alignment=0, spaceAfter=2)
SUB = ParagraphStyle("sub", parent=ss["Normal"], textColor=colors.HexColor(GREY), fontSize=9, spaceAfter=6)
H2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=colors.HexColor(AMBER), fontSize=13, spaceBefore=9, spaceAfter=3)
H3 = ParagraphStyle("h3", parent=ss["Heading3"], textColor=colors.HexColor(DARK), fontSize=10.5, spaceBefore=5, spaceAfter=2)
P = ParagraphStyle("p", parent=ss["Normal"], fontSize=9.3, leading=13, spaceAfter=3)
N = ParagraphStyle("n", parent=P, leftIndent=14, bulletIndent=2, spaceAfter=2)
SM = ParagraphStyle("sm", parent=P, fontSize=8, leading=10.5, textColor=colors.HexColor(GREY))
bl = lambda xs: [Paragraph(x, N, bulletText="•") for x in xs]
num = lambda xs: [Paragraph(x, N, bulletText=f"{i}.") for i, x in enumerate(xs, 1)]


def table(rows, widths):
    rows = [[Paragraph(c, P) if isinstance(c, str) else c for c in r] for r in rows]
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(AMBER)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#fef3c7")]),
        ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5)]))
    return t


buy, sell = costs.side_costs("sharekhan", "delivery")


def build(path=OUT):
    s = [Paragraph("Sf5b94362 trading guide", H1),
         Paragraph("Your strategy, step by step: entry, stop, exits, risk, drawdown and money management. Written from the "
                   "code that produced the backtest (17.0% CAGR / −28.4% max drawdown, point-in-time NIFTY 500, 2000–2026; "
                   "random-pick median 16.3%). Research and education only, not investment advice.", SUB),
         Paragraph("The strategy in one paragraph", H2),
         Paragraph("Buy NIFTY 500 stocks in a long-term uptrend when their monthly momentum turns up after a pullback, but only "
                   "while the broad market (NIFTY 500 index) is above its 200-day average. Risk 1% of the account per trade "
                   "with a stop at the previous week's low. Cut trades that go nowhere after 25 days; otherwise hold until the "
                   "weekly Supertrend turns bearish, which can be years. Hold at most 10 stocks, no stock above 20% of the "
                   "account, and cut risk in half when the account is 10% below its high. About 1 trade in 4 wins; a few "
                   "multi-year winners pay for everything.", P),
         Paragraph("Your calendar", H2),
         table([["When", "What you do"],
                ["Last trading day of the month, after the close",
                 "Scan for setups (Step 1). Trim any position above 20% of equity (Step 7). Update the equity high and the "
                 "drawdown status (Step 6)."],
                ["Before the first trading day of the month", "Place buy-stop orders for every setup (Step 2)."],
                ["Every trading day, after the close",
                 "Check the market filter for tomorrow. Note fills; record each new trade's stop and its 25-day date. Check "
                 "any trade that reaches its 25-day date (Step 4)."],
                ["Every Friday, after the close", "Update the weekly Supertrend of each open position (Step 5). Note the "
                 "week's low (it becomes the stop for any fill next week)."],
                ["Every Monday open", "Sell any position whose weekly Supertrend turned bearish on Friday."]],
               [52 * mm, 126 * mm])]

    s += [PageBreak(), Paragraph("Step 1: find setups (month end)", H2),
          Paragraph("On the last trading day of the month, after the close, check each stock that is in the NIFTY 500. A stock is "
                    "a setup only if <b>all</b> of these hold on the completed charts:", P)] + num([
        "<b>Monthly Stochastic RSI (14, 14, 3, 3)</b>: %K crosses above %D this month (%K was at or below %D last month, and is "
        "above it now), <b>and %D is below 30</b>. This is the pullback turning up.",
        "<b>Monthly close above the monthly EMA 61.</b>",
        "<b>Last completed weekly close above the weekly EMA 61.</b> If the month ends mid-week, use the previous Friday's week.",
        "<b>Daily close above the daily EMA 61</b> on the month's last day.",
        "<b>Monthly RSI(14) above 50.</b>"]) + [
        Paragraph("Write down for each setup: the monthly <b>high</b> (your buy-stop level) and last week's low (a first "
                  "estimate of the stop). The weekly Supertrend does <b>not</b> matter for entry.", P),
        Paragraph("Step 2: place the buy-stop orders (next month)", H2)] + num([
        "For each setup, a <b>buy-stop at the setup month's high</b>, valid for the whole next calendar month. Cancel it at "
        "month end if it has not filled; a new setup needs a new monthly signal.",
        "<b>Market filter</b>: the order may fill only on a day when the <b>NIFTY 500 index closed above its 200-day simple "
        "average the day before</b>. If the index closed below, pull (or do not place) all buy-stops for the next day.",
        "The stock must be a NIFTY 500 member on the fill day.",
        "<b>Fill price</b>: the buy-stop level; if the stock opens above it (gap), you buy at the open.",
        "Skip a setup if you already hold that stock."]) + [
        Paragraph("Step 3: the stop and the position size (fill day)", H2)] + num([
        "<b>Stop = low of the last completed week</b> before the fill day. It is fixed for the life of the trade: never "
        "moved up, never widened. Place it as a stop-loss order (GTT) right after the fill.",
        "<b>Risk budget</b> = 1% of yesterday's closing equity (cash + open positions at their closes) × the drawdown "
        "multiplier (1, ½ or 0 — Step 6).",
        "<b>Shares</b> = risk budget ÷ (entry − stop), rounded down.",
        "If the cost (shares × price, plus about 0.6% costs) is more than your cash, buy only what the cash allows.",
        "If several orders fill on the same day, fill first the one with the <b>tightest stop in percent</b>.",
        "Maximum <b>10 positions</b>. A buy-stop that triggers while all 10 are held is skipped and not retried that month; "
        "the other buy-stops stay live and can fill later in the month if a slot frees up.",
        "If the stock closes at or below the stop on the fill day itself, sell at that close.",
        "<b>Caution: the 20% cap is not applied at entry.</b> A very tight stop gives a very large position: in the "
        "backtest 13 of 414 entries were above 20% of the account and one was 80%, until trimmed at month end. That is "
        "what was tested; capping each entry at 20% is safer for gap risk but has not been tested yet."]) + [
        KeepTogether([Paragraph("Worked example", H3),
                      Paragraph("Equity yesterday ₹10,00,000, full risk. Setup month high ₹500 → buy-stop ₹500. Last week's low "
                                "₹460 → stop ₹460. Risk ₹10,000; distance ₹40; shares = 10,000 ÷ 40 = <b>250</b> (₹1.25 lakh, "
                                "12.5% of the account). If the stock gaps open at ₹510: distance ₹50 → 200 shares.", P)])]

    s += [PageBreak(), Paragraph("Step 4: the 25-day time stop", H2)] + num([
        "Mark the date <b>25 calendar days after entry</b>.",
        "On the first trading day on or after that date, look at <b>the previous day's close</b>. If it is below "
        "<b>entry + 0.25 × (entry − stop)</b>, sell at that day's open.",
        "If it is at or above that level, the time stop is passed for good: the trade now runs until the stop or the "
        "Supertrend exit.",
        "Example: entry ₹500, stop ₹460 (R = ₹40). The level is ₹510. Close below ₹510 at day 25 → sell next open."]) + [
        Paragraph("Step 5: the Supertrend exit (weekly)", H2)] + num([
        "Each Friday, compute the <b>weekly Supertrend(10, 3)</b> (ATR 10, multiplier 3) on the stock's weekly chart.",
        "Sell at the <b>next Monday's open</b> only when it <b>turns</b> from bullish to bearish <b>after your entry</b>.",
        "If it was already bearish when you bought, do nothing until it has turned bullish and then bearish again. In "
        "the meantime the stop and the time stop protect you.",
        "There is no profit target and no holding limit. Winners may run 2–4 years: do not sell them early."]) + [
        Paragraph("Order of checks each day", H3)] + num([
        "Time stop due today and failed → sell at the open.",
        "Stock opens at or below the stop → sell at the open (gap).",
        "Supertrend turned bearish last Friday → sell at the open.",
        "Price trades down to the stop during the day → sold at the stop."])

    s += [PageBreak(), Paragraph("Step 6: risk and the drawdown rule", H2)] + bl([
        "<b>Equity</b> = cash + all open positions at the day's closing prices. <b>Equity high</b> = the highest closing "
        "equity so far.",
        "<b>Drawdown</b> = how far yesterday's equity is below the equity high, in %.",
        "<b>Below 10%</b>: full risk, 1% per new trade.",
        "<b>10% or more below the high: half risk</b>, 0.5% per new trade. It stays on until equity closes at a <b>new "
        "high</b> (not when it recovers to −5%).",
        "<b>15% or more below the high: no new trades for 21 trading days</b>, once per drawdown. Signals in that period "
        "are skipped, not saved. After the pause, trade at half risk. No second pause until after a new high.",
        "Open positions are never resized by this rule: their stops and exits continue as normal."]) + [
        table([["Account (peak ₹20 L)", "Status", "Risk on a new trade"],
               ["₹18.6 L (−7%)", "Full risk", "1% = ₹18,600"], ["₹18.0 L (−10%)", "Half risk", "0.5% = ₹9,000"],
               ["₹17.0 L (−15%)", "Paused 21 trading days", "none"], ["₹19.5 L (−2.5%)", "Still half risk", "0.5% = ₹9,750"],
               ["₹20.1 L (new high)", "Full risk again", "1% = ₹20,100"]], [55 * mm, 60 * mm, 60 * mm]),
        Paragraph("Step 7: money management", H2)] + bl([
        "<b>Position cap</b>: on the last trading day of each month, any position worth more than <b>20% of equity</b> "
        "is trimmed back to 20% at the close. The rest of it keeps its stop and exits.",
        "<b>Idle cash</b> sits in a liquid fund (the backtest assumes 6.5% a year).",
        "<b>No leverage, no margin, no shorts, no F&O hedges.</b>",
        f"<b>Costs in the backtest</b>: Sharekhan delivery brokerage 0.3%, STT 0.1% each side, stamp duty, exchange and "
        f"SEBI fees, GST, plus 0.1% slippage per side: about {(buy + sell) * 100 + 0.2:.1f}% per round trip. A discount "
        "broker cuts this sharply.",
        "<b>Tax</b> is not in the backtest: short-term gains (under a year) 20%, long-term 12.5% above the exemption.",
        "Keep a journal: every setup, fill, skip, stop and exit, with the reason."]) + [
        Paragraph("What to expect", H2)] + bl([
        "About <b>25% of trades win</b>; the average loss is about −6.6%, the average win about +82%. Losing streaks of "
        "20–30 trades happen.",
        "The top 10 trades in 26 years made all of the net profit; never cut a big winner early.",
        "Drawdowns of −25% to −30% happen; the account was at half risk about half of the time.",
        "Calendar years from −21% (2008) to +105% (2014); flat or slightly negative years are common."]) + [
        Paragraph("Research and education only, not investment advice.", SM)]
    SimpleDocTemplate(str(path), pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm,
                      bottomMargin=14 * mm, title="Sf5b94362 trading guide").build(s)
    return path


if __name__ == "__main__":
    print("wrote", build())
