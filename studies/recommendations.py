"""Recommendations summary -> results/studies/recommendations/recommendations.json (read by site.py) + report.pdf.
Edit the tables here; figures are point-in-time NIFTY 500 (NIFTY500_PIT) unless stated.
"""
import json, sys
from datetime import date
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle

OUT = ROOT / "results" / "studies" / "recommendations"
OUT.mkdir(parents=True, exist_ok=True)

REC = {
    "intro": "Figures are from historical (point-in-time) NIFTY 500 membership unless noted, include costs, and "
             "start from 2000. Expect live results somewhat lower.",
    "sections": [
        {"title": "Your choice", "mine": True,
         "head": ["ID", "Strategy", "CAGR", "Max DD", "Status"],
         "rows": [["S63387f09", "Sde394f26 at 1% risk, long only, no hedges; NIFTY 500 index market filter; time stop "
                                "needs 0.25R at day 25", "15.8%", "−26.5%", "Your strategy (adopted 21 Nov 2026)"],
                  ["S1704ed9f", "Same with the original 0.5R time stop", "14.9%", "−26.5%", "Previous choice"],
                  ["Sde394f26", "The original: NIFTY 50 market filter, 0.5R time stop", "13.7%", "−27%",
                   "First choice, kept for comparison"]],
         "notes": ["Entry: monthly StochRSI pullback; close above EMA 61 on monthly, weekly and daily; RSI above 50; "
                   "NIFTY 500 index above its 200-day average (previous close).",
                   "Exits: stop at the previous week's low; sell at the next open if the trade is not 0.25R up 25 days "
                   "after entry; otherwise hold until a week closes with the weekly Supertrend(10, 3) bearish (sold at the next open; a trade bought while it is already bearish is sold after its first week). No holding cap.",
                   "Sizing: 1% risk per trade on current equity, 10 slots, 20% position cap; halve size at a 10% drawdown, "
                   "pause 21 days at 15%. Idle cash in a liquid fund. No NIFTY futures hedges.",
                   "The worst drawdown (May–June 2006 crash) can't be cut by an entry filter; plan for about −27% to −30%."]},
        {"title": "Recommended",
         "head": ["Rank", "ID", "Strategy", "CAGR", "Max DD", "Best for"],
         "rows": [["1", "S150d745e", "Sde394f26 at 0.5% risk, long only", "11.1%", "−20%",
                   "Most investors; a −20% worst case"],
                  ["2", "S762fa364", "Same + RS ranking", "12.8%", "−25%", "NIFTY 500 traders who can accept −25%"],
                  ["3", "Sde394f26", "Same at 1% risk", "13.7%", "−27%", "A higher pain limit (about −50%)"],
                  ["4", "Sf594c67c", "Sde394f26 + weekly short book (stock futures)", "14.1%", "−28%",
                   "Large accounts (₹50 lakh+) trading large caps; crash insurance"]],
         "notes": ["Shared core rules. Entry: monthly StochRSI pullback; close above EMA 61 on monthly, weekly and "
                   "daily; RSI above 50; NIFTY above its 200-day average.",
                   "Stop: the previous week's low. Exits: weekly Supertrend turns bearish, or the 25-day time stop.",
                   "Risk controls: 20% position cap; halve size at a 10% drawdown, pause 21 days at 15%. Idle cash in "
                   "a liquid fund."]},
        {"title": "Useful additions",
         "head": ["Idea", "Why"],
         "rows": [["NIFTY 200 Momentum 30 index fund for 30–40% of capital",
                   "Owns the momentum effect with clean, point-in-time index data"],
                  ["NIFTY futures hedge or puts when NIFTY is below its 200-day average",
                   "Simpler crash protection than a short book, for smaller accounts"],
                  ["Universe: NIFTY 500", "Broad enough for signals; liquid enough to trade"]]},
        {"title": "Not recommended",
         "head": ["ID", "Strategy", "Result", "Why not"],
         "rows": [["Sc84b59b8 / S29186978", "Momentum rotation", "23% / −60% to −69%",
                   "Still partly survivorship bias; drawdown too deep"],
                  ["Scaa0a5e0, Sa15d9d9c, S1bb9f7b0", "Compounded stacks", "13–19% / −39% to −43%",
                   "Drawdowns most people abandon"],
                  ["S7c315ace", "Original main strategy", "10.9% / −37%", "Worse risk/return than S150d745e"],
                  ["—", "NIFTY 750 / microcaps", "Edge vanishes with any liquidity filter", "Couldn't be traded in size"],
                  ["—", "IT-only, finance-only, IT + finance", "7.8–12.3% (today's lists)", "Too few signals; a sector bet"],
                  ["—", "Short book alone", "~0% without cash interest", "Insurance only, not a profit source"],
                  ["—", "Idle cash in a NIFTY ETF, 3×ATR chandelier trail, regime sizing",
                   "Higher drawdown or lower return", "Failed testing"],
                  ["Se32915a5", "High win-rate strategy", "8.2% / −57%", "High win rate, poor returns"]]},
        {"title": "Before real money",
         "head": ["Step", "Action"],
         "rows": [["1", "Paper-trade S150d745e for 6 months, journaling every signal and fill"],
                  ["2", "Choose the risk level so the backtest's worst drawdown is about half of what you could "
                        "actually sit through"],
                  ["3", "Keep the drawdown rule switched on, always"]]}],
    "footer": "Research and education only, not investment advice."}

if __name__ == "__main__":
    REC["date"] = f"{date.today():%d %b %Y}"
    _rp = ROOT / "results" / "studies" / "ruin" / "ruin.json"
    if _rp.exists():  # your strategy: ₹10 lakh over 5-year periods and drawdown odds (studies/ruin_report.py)
        _r = json.load(open(_rp))
        REC["sections"][1:1] = [
            {"title": "Your strategy: ₹10 lakh over each 5-year period", "mine": True, "pdf_only": True, "head": _r["win"][0],
             "rows": _r["win"][1:], "notes": [f"{a}: {b}" for a, b in _r["roll"][1:]]},
            {"title": "₹10 lakh: your strategy vs Sde394f26", "mine": True, "pdf_only": True, "head": _r["cmp"][0],
             "rows": _r["cmp"][1:], "notes": [f"{a}: Sde394f26 {b}, S63387f09 {c}" for a, b, c in _r["cmproll"][1:]]},
            {"title": "Your strategy: risk of ruin", "mine": True, "pdf_only": True, "head": _r["dd"][0], "rows": _r["dd"][1:],
             "notes": ["From 20,000 resampled 20-year histories (monthly returns, 12-month blocks)."] + _r["facts"]
                      + ["Going bust is effectively impossible while the rules are followed; never add leverage or margin."]}]
    json.dump(REC, open(OUT / "recommendations.json", "w"), indent=1, ensure_ascii=False)
    ss = getSampleStyleSheet()
    DARK, GREY = "#0f172a", "#64748b"
    H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=18, leading=22, alignment=0, textColor=colors.HexColor(DARK))
    H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=13, textColor=colors.HexColor(DARK), spaceBefore=12, spaceAfter=5)
    SUB = ParagraphStyle("SUB", parent=ss["Normal"], fontSize=9, textColor=colors.HexColor(GREY), spaceAfter=4)
    TC = ParagraphStyle("TC", parent=ss["Normal"], fontSize=8, leading=10)
    TH = ParagraphStyle("TH", parent=TC, textColor=colors.white, fontName="Helvetica-Bold")
    BL = ParagraphStyle("BL", parent=ss["Normal"], fontSize=8.6, leading=11.5, leftIndent=10)
    W = {5: [18 * mm, 70 * mm, 15 * mm, 15 * mm, 68 * mm], 2: [70 * mm, 116 * mm], 4: [38 * mm, 50 * mm, 42 * mm, 56 * mm], 6: [11 * mm, 20 * mm, 55 * mm, 15 * mm, 15 * mm, 70 * mm]}
    story = [Paragraph("Strategy recommendations", H1), Paragraph(f"{REC['intro']} Updated {REC['date']}.", SUB)]
    for sec in REC["sections"]:
        widths = [12 * mm, 174 * mm] if sec["title"] == "Before real money" else [45 * mm, 30 * mm, 35 * mm, 30 * mm, 46 * mm] if "₹10 lakh" in sec["title"] else [40 * mm, 30 * mm, 26 * mm, 30 * mm, 26 * mm, 34 * mm] if "vs Sde394f26" in sec["title"] else W[len(sec["head"])]
        rows = [[Paragraph(h, TH) for h in sec["head"]]] + [[Paragraph(c, TC) for c in r] for r in sec["rows"]]
        tb = Table(rows, colWidths=widths, repeatRows=1)
        st = [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(DARK)), ("VALIGN", (0, 0), (-1, -1), "TOP"),
              ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
              ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
        if sec["title"] == "Recommended":
            st.append(("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#dcfce7")))
        if sec.get("mine"):
            st += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#b45309")),
                   ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#fef3c7")), ("BOX", (0, 0), (-1, -1), 1.2, colors.HexColor("#b45309"))]
        tb.setStyle(TableStyle(st))
        story += [Paragraph(sec["title"], H2), tb]
        story += [Paragraph(n, BL, bulletText="•") for n in sec.get("notes", [])]
    story.append(Paragraph(REC["footer"], SUB))
    SimpleDocTemplate(str(OUT / "report.pdf"), pagesize=A4, leftMargin=12 * mm, rightMargin=12 * mm, topMargin=12 * mm,
                      bottomMargin=12 * mm, title="Strategy recommendations").build(story)
    print("wrote", OUT / "report.pdf")
