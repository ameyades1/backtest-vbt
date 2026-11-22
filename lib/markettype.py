"""Van Tharp-style market types: direction (bull / sideways / bear) x volatility (quiet / volatile), per day.

Broad market = NIFTY 50 (Sensex scaled in before NIFTY's history, as lib.engine.nifty_close), same series all runs.
  Direction:  13-week (65 trading-day) change of the index: above +5% bull, below -5% bear, otherwise sideways.
  Volatility: 20-day standard deviation of daily returns, against its own rolling 3-year median
              (volatile if above). Rolling, so no future data is used.
A day's type uses closes up to the previous day, so a trade is filed under the type known when it was bought.
"""
import numpy as np
import pandas as pd

TYPES = [f"{d} {v}" for d in ("Bull", "Sideways", "Bear") for v in ("quiet", "volatile")]
_T = None


def types() -> pd.Series:
    global _T
    if _T is None:
        from .engine import nifty_close
        n = nifty_close().dropna()
        ch = n.pct_change(65)
        vol = n.pct_change().rolling(20).std()
        med = vol.rolling(756, min_periods=252).median()
        d = np.where(ch > .05, "Bull", np.where(ch < -.05, "Bear", "Sideways"))
        v = np.where(vol > med, "volatile", "quiet")
        t = pd.Series([f"{a} {b}" for a, b in zip(d, v)], index=n.index)
        _T = t[ch.notna() & med.notna()].shift(1).dropna()
    return _T


def breakdown(equity: pd.Series, trades: pd.DataFrame) -> list[list[str]]:
    """equity: daily equity; trades: closed trades with entry_date, pnl, risk (from lib.metrics.closed)."""
    t = types()
    e = equity.dropna()
    r = e.pct_change().dropna()
    ty = t.reindex(r.index, method="ffill")
    nf = __import__("lib.engine", fromlist=["x"]).nifty_close().reindex(e.index, method="ffill").pct_change().reindex(r.index)
    et = t.reindex(pd.to_datetime(trades.entry_date), method="ffill").to_numpy()
    R = (trades.pnl / trades.risk.replace(0, np.nan)).to_numpy()
    rows = [["Market type", "Days %", "Strategy / yr", "NIFTY / yr", "Trades", "Win %", "Expectancy R", "Share of R"]]
    tot = np.nansum(R)
    for k in TYPES:
        m = (ty == k).to_numpy()
        n = m.sum()
        ann = lambda x: (np.prod(1 + x[m]) ** (252 / n) - 1) * 100 if n else np.nan
        sel = et == k
        rr = R[sel]
        rows.append([k, f"{n / len(r) * 100:.0f}", f"{ann(r.to_numpy()):+.1f}%", f"{ann(nf.fillna(0).to_numpy()):+.1f}%",
                     f"{sel.sum()}", f"{(rr > 0).mean() * 100:.0f}" if len(rr) else "–",
                     f"{np.nanmean(rr):+.2f}" if len(rr) else "–",
                     f"{np.nansum(rr) / tot * 100:.0f}%" if len(rr) and tot else "–"])
    return rows


NOTE = ("Each day is typed from NIFTY 50 (Sensex before 2007) up to the previous close. Bull / bear: 13-week change above "
        "+5% / below −5%, otherwise sideways. Volatile: 20-day volatility above its rolling 3-year median. Strategy / yr and "
        "NIFTY / yr = annualised return on the days of that type. Trades are filed by the type on their entry day; Share of "
        "R = that type's part of all R earned. NIFTY / yr in bear-volatile is often positive: it holds the sharp rebounds "
        "that follow falls.")


def for_run(run) -> list[list[str]]:
    """Breakdown for a run directory's no-target exit (results/<name>/<universe>)."""
    from pathlib import Path
    from . import metrics
    run = Path(run)
    S = pd.read_csv(run / "summary.csv", index_col=0)
    m = metrics.compute(pd.read_csv(run / "fills_none.csv"), S.loc["No target"], "2000-01-01")
    e = pd.read_csv(run / "equity.csv", index_col=0, parse_dates=True)["No target"]
    return breakdown(e, m["_closed"])


def flowables(rows, h2=None, title="Market types (Van Tharp)", note_style=None):
    """reportlab flowables: heading, table, note."""
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Table, TableStyle, KeepTogether
    ss = getSampleStyleSheet()
    h2 = h2 or ParagraphStyle("mtH2", parent=ss["Heading2"], fontSize=12, spaceBefore=8, spaceAfter=4)
    sm = note_style or ParagraphStyle("mtSM", parent=ss["Normal"], fontSize=7.6, leading=9.6, textColor=colors.HexColor("#64748b"))
    tb = Table(rows, colWidths=[32 * mm, 15 * mm, 23 * mm, 21 * mm, 15 * mm, 14 * mm, 23 * mm, 20 * mm], repeatRows=1)
    st = [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8), ("FONT", (0, 1), (-1, -1), "Helvetica", 8),
          ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
          ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]), ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
          ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
    for i, r in enumerate(rows[1:], 1):
        if r[6].startswith("-") or r[6].startswith("−"):
            st.append(("TEXTCOLOR", (6, i), (6, i), colors.HexColor("#b91c1c")))
    tb.setStyle(TableStyle(st))
    return [KeepTogether([Paragraph(title, h2), tb, Paragraph(NOTE, sm)])]


def compact(names, limit=40) -> list[list[str]] | None:
    """One row per strategy: annualised return and expectancy R in each market type (no-target exit, PIT NIFTY 500
    run if present, else the first universe run)."""
    from pathlib import Path
    from . import ids
    root = Path(__file__).resolve().parents[1] / "results"
    m = ids.by_name()
    rows = [["ID"] + [t.replace("Sideways", "Side") for t in TYPES]]
    for n in list(dict.fromkeys(names))[:limit]:
        d = root / n / "nifty500_pit"
        if not (d / "fills_none.csv").exists():
            cand = sorted(p for p in (root / n).glob("*") if (p / "fills_none.csv").exists()) if (root / n).exists() else []
            if not cand:
                continue
            d = cand[0]
        try:
            b = for_run(d)
        except Exception:
            continue
        rows.append([ids.short(m[n]) if n in m else n[-12:]] + [f"{r[2]} · {r[6]}R" for r in b[1:]])
    return rows if len(rows) > 1 else None


def compact_flowables(names, h2_style, fs=7.0):
    from reportlab.lib import colors
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Table, TableStyle, KeepTogether
    rows = compact(names)
    if not rows:
        return []
    tb = Table(rows, colWidths=[20 * mm] + [26 * mm] * 6, repeatRows=1)
    tb.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", fs), ("FONT", (0, 1), (-1, -1), "Helvetica", fs),
        ("FONT", (0, 1), (0, -1), "Courier", fs - .6), ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    sm = ParagraphStyle("mtc", fontName="Helvetica", fontSize=6.8, leading=8.6, textColor=colors.HexColor("#64748b"))
    return [KeepTogether([Paragraph("Market types (Van Tharp): return per year · expectancy per trade", h2_style), tb,
                          Paragraph("No-target exit. " + NOTE, sm)])]


def big(run, title="Market types (Van Tharp)"):
    """Large-type version for the textbook-style notes (lib.bookstyle)."""
    from . import bookstyle as bs
    from reportlab.platypus import Paragraph
    rows = for_run(run)
    rows[0] = ["Market type", "Days %", "Strategy / yr", "NIFTY / yr", "Trades", "Win %", "Exp. R", "R share"]
    return [Paragraph(title, bs.H2), bs.table(rows, [w * 2.8346 for w in (38, 17, 25, 22, 18, 16, 16, 18)]),
            Paragraph("Exp. R = expectancy per trade; R share = that type's share of all R earned. " + NOTE, bs.SM)]
