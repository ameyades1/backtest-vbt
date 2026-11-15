"""Shared 'winners vs losers duration' section for the report builders.

Reads data/trade_duration/{duration,conditional}.csv (examples/trade_duration_study.py) and returns
reportlab flowables built with the calling report's own styles and table function.
"""
from pathlib import Path
import pandas as pd
from reportlab.platypus import Paragraph, KeepTogether

D = Path(__file__).resolve().parent.parent / "data" / "trade_duration"
EXITS = ["No target", "Target 15%", "Target 30%"]


def flowables(stop: str, H2, P, SM, table, mm):
    dur = pd.read_csv(D / "duration.csv")
    cond = pd.read_csv(D / "conditional.csv")
    dur, cond = dur[dur.Stop == stop], cond[cond.Stop == stop]

    def g(exit_, grp, col):
        return float(dur[(dur.Exit == exit_) & (dur.Group == grp)][col].iloc[0])

    rows = [["Exit", "Group", "Trades", "Avg days", "Median days", "Middle 50% (days)", "90th pct days",
             "Avg gain %", "Median gain %"]]
    for e in EXITS:
        for grp in ["Winners", "Losers"]:
            r = dur[(dur.Exit == e) & (dur.Group == grp)].iloc[0]
            rows.append([e if grp == "Winners" else "", grp, f"{int(r.Trades):,}", f"{r['Avg days']:,.0f}",
                         f"{r['Median days']:,.0f}", f"{r['P25 days']:,.0f}–{r['P75 days']:,.0f}",
                         f"{r['P90 days']:,.0f}", f"{r['Avg gain %']:.1f}", f"{r['Median gain %']:.1f}"])
    crow = [["Exit", "Open after", "Still open %", "Eventual win %", "Eventual gain %",
             "Winners closed %"]]
    for e in EXITS:
        for n in [30, 90, 180, 365]:
            r = cond[(cond.Exit == e) & (cond["After days"] == n)].iloc[0]
            crow.append([e if n == 30 else "", f"{n} days", f"{r['Still open %']:.1f}",
                         f"{r['Win % if still open']:.1f}", f"{r['Avg gain % if still open']:.1f}",
                         f"{r['Winners done by then %']:.1f}"])
    lead = (f"Winners take far longer than losers. With no target, the median winner lasts "
            f"{g('No target', 'Winners', 'Median days'):,.0f} days against "
            f"{g('No target', 'Losers', 'Median days'):,.0f} for losers; with a 30% target, "
            f"{g('Target 30%', 'Winners', 'Median days'):,.0f} days against "
            f"{g('Target 30%', 'Losers', 'Median days'):,.0f}.")
    return [
        KeepTogether([Paragraph("Winners vs losers: trade duration", H2), Paragraph(lead, P),
                      table(rows, [21 * mm, 14 * mm, 13 * mm, 16 * mm, 19 * mm, 25 * mm, 19 * mm, 18 * mm,
                                   21 * mm], 2),
                      Paragraph("All signals 2000 – Nov 2026 (not limited by portfolio slots), closed trades "
                                "only. Gain % is net of Sharekhan costs. Days are calendar days.", SM)]),
        KeepTogether([Paragraph("Trades still open after N days", H2),
                      Paragraph("Trades that last longer do not win less often, so a time stop mainly cuts "
                                "future winners. See the time-exit study for the portfolio test.", P),
                      table(crow, [24 * mm, 20 * mm, 22 * mm, 26 * mm, 32 * mm, 38 * mm], 1),
                      Paragraph("Eventual win % and gain % = final results of the trades still open after "
                                "that many days. Winners closed % = share of all winners already finished by then.",
                                SM)]),
    ]
