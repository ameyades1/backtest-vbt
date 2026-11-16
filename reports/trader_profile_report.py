"""Build reports/trader_profile.pdf: profile of a veteran Indian-markets technical trader."""
from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "trader_profile.pdf"
BLUE, GREY, DARK = "#2563eb", "#64748b", "#0f172a"

ss = getSampleStyleSheet()
H1 = ParagraphStyle("h1", parent=ss["Title"], textColor=DARK, fontSize=22, alignment=0, spaceAfter=2)
SUB = ParagraphStyle("sub", parent=ss["Normal"], textColor=GREY, fontSize=10.5, spaceAfter=10)
H2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=BLUE, fontSize=13, spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("p", parent=ss["Normal"], fontSize=10, leading=14.5, textColor=DARK, spaceAfter=5)
B = ParagraphStyle("b", parent=P, leftIndent=12, bulletIndent=2, spaceAfter=2.5)
Q = ParagraphStyle("q", parent=P, leftIndent=14, textColor=GREY, fontName="Helvetica-Oblique")


def bullets(items):
    return [Paragraph(i, B, bulletText="•") for i in items]


def table(rows, widths):
    t = Table(rows, colWidths=widths)
    t.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9.5),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 9.5),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BLUE)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cbd5e1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def cell(s):
    return Paragraph(s, ParagraphStyle("c", parent=P, fontSize=9.5, leading=12.5, spaceAfter=0))


story = [
    Paragraph("Trader Profile", H1),
    Paragraph("Senior Technical Trader &amp; Risk Manager · Indian Equity and Derivatives Markets · 30+ years", SUB),

    Paragraph("Summary", H2),
    Paragraph(
        "A discretionary-systematic trader who has traded Indian markets since the open-outcry days of the "
        "Bombay Stock Exchange ring, through the launch of NSE screen-based trading (1994), the introduction "
        "of index futures (2000) and options, and into today's algorithmic, high-retail-participation market. "
        "Their edge rests on two pillars: <b>reading price structure across timeframes</b>, and <b>a risk "
        "framework strict enough that no single trade, sector or regime can do lasting damage</b>. "
        "They have survived the 1992 Harshad Mehta crash, the 2000 tech bust, the 2008 global crisis, "
        "the 2013 taper tantrum, demonetisation, the 2020 COVID crash and the 2024 SEBI F&amp;O reforms by "
        "treating capital preservation as the first job and returns as the by-product.", P),

    Paragraph("Career Timeline", H2),
    table([
        ["Period", "Role and focus"],
        [cell("1992–1999"), cell("BSE floor dealer and proprietary trader. Learned tape reading, volume "
                                  "behaviour and how badly leverage ends (1992 scam, 1994–96 bear market).")],
        [cell("2000–2008"), cell("Prop desk at a Mumbai broking house. Early adopter of NIFTY futures and "
                                  "options; built the first versions of their trend-following rules on daily "
                                  "and weekly charts.")],
        [cell("2008–2016"), cell("Head of trading for a family office. Cut drawdown in the 2008 crash to "
                                  "a fraction of the index's through position limits and stop discipline.")],
        [cell("2016–present"), cell("Independent portfolio trader and mentor. Combines rules-based "
                                     "backtesting (NIFTY 500 universe) with discretionary execution; "
                                     "trains younger traders in risk management.")],
    ], [32 * mm, 138 * mm]),

    Paragraph("Technical Analysis Expertise", H2),
    *bullets([
        "<b>Trend structure:</b> moving-average systems (EMA 21/61/200), higher-high/higher-low analysis, "
        "Dow theory, and multi-timeframe alignment (monthly for direction, weekly for setup, daily for entry).",
        "<b>Price action:</b> breakouts from bases, pullbacks to support, candle patterns read in context "
        "rather than in isolation, gap behaviour around results and budget days.",
        "<b>Volume and breadth:</b> delivery percentage on NSE, volume expansion on breakouts, advance-decline "
        "ratios and the share of NIFTY 500 stocks above their 200-day average.",
        "<b>Momentum and volatility:</b> RSI and MACD divergences, ATR for stop placement and sizing, "
        "Bollinger squeezes, India VIX as a regime filter.",
        "<b>Relative strength:</b> ranks sectors and stocks against NIFTY 50 and rotates into leadership "
        "(banks, IT, capital goods, PSU, defence cycles).",
        "<b>Derivatives:</b> reading open interest build-up, put-call ratio, max-pain levels and rollover "
        "data around monthly expiry.",
    ]),

    Paragraph("Risk Management Framework", H2),
    table([
        ["Rule", "Practice"],
        [cell("Risk per trade"), cell("0.5–2% of capital, set by the distance from entry to stop; position "
                                       "size follows from the stop, never the other way round.")],
        [cell("Portfolio heat"), cell("Total open risk capped at 6–8%; at most 4–6 concurrent positions, "
                                       "no more than two in one sector.")],
        [cell("Stops"), cell("Every position has a pre-defined stop placed at entry: a structural level "
                              "(candle or weekly low) or an ATR multiple, then trailed. Stops are never widened.")],
        [cell("Drawdown brakes"), cell("Size halved after a 10% equity drawdown; trading paused for review "
                                        "at 15%. Size restored only after new equity highs.")],
        [cell("Leverage"), cell("Futures and options used for hedging and defined-risk spreads; no naked "
                                 "short options into events. Margin use kept well below broker limits.")],
        [cell("Event risk"), cell("Reduces exposure ahead of Union Budget, RBI policy, election results and "
                                   "major global data; accounts for circuit limits and gap risk.")],
        [cell("Costs"), cell("Models STT, brokerage, exchange charges, GST, stamp duty and slippage in "
                              "every backtest before trusting a result.")],
        [cell("Liquidity"), cell("Trades only stocks with adequate turnover; avoids illiquid small caps "
                                  "and ASM/GSM-listed names.")],
    ], [32 * mm, 138 * mm]),

    Paragraph("Trading Philosophy", H2),
    Paragraph("“The market pays you to sit through trends and charges you for every rule you break. "
              "My job is to stay in the game long enough for the big moves to come.”", Q),
    *bullets([
        "Cut losers fast, let winners run: a low win rate is acceptable when winners are several times the "
        "size of losers.",
        "Test every idea on historical data with realistic costs before risking money on it.",
        "Respect the regime: be aggressive in trending bull phases, defensive in bear phases, small in "
        "choppy ones.",
        "Keep a trade journal; review every losing month for rule breaks, not just bad luck.",
    ]),

    Paragraph("Indian Market Knowledge", H2),
    *bullets([
        "Market microstructure of NSE and BSE: pre-open session, circuit filters, T+1 settlement, "
        "F&amp;O ban lists and lot-size changes.",
        "Regulation: SEBI margin rules, peak-margin norms, the 2024 F&amp;O changes and taxation of "
        "short- and long-term capital gains.",
        "Flow drivers: FII/DII activity, SIP inflows, rupee and crude oil moves, monsoon and earnings seasons.",
        "Index families: NIFTY 50, NIFTY 500, Bank NIFTY, midcap and smallcap indices, and sectoral indices.",
    ]),

    Paragraph("Instruments and Timeframes", H2),
    Paragraph("Cash equities (swing and positional, holding periods of weeks to months), index and stock "
              "futures, and index options for hedging and defined-risk spreads. Charts used: monthly, weekly "
              "and daily, with intraday charts only for timing entries.", P),

    Paragraph("Strengths", H2),
    *bullets([
        "Survived and compounded through every major Indian bear market of the last three decades.",
        "Turns chart patterns into testable rules and checks them on data before trading them.",
        "Calm, process-driven execution; clear rules for when not to trade.",
        "Mentors traders on position sizing, journaling and trading psychology.",
    ]),
]

SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                  topMargin=16 * mm, bottomMargin=16 * mm,
                  title="Trader Profile").build(story)
print(OUT)
