"""Build reports/ema61_time_exit.pdf from data/time_exit/summary.csv (examples/time_exit_study.py)."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "ema61_time_exit.pdf"
BLUE, GREY, DARK = "#2563eb", "#64748b", "#0f172a"
t = pd.read_csv(ROOT / "data" / "time_exit" / "summary.csv")
t["Time exit"] = t["Time exit"].fillna("None")
TIMES = ["None", "90 days", "180 days", "365 days"]
GROUPS = [(s, e) for s in ["Candle low", "Week low fixed"] for e in ["No target", "Target 15%", "Target 30%"]]


def val(stop, exit_, time, sizing, col):
    r = t[(t.Stop == stop) & (t.Exit == exit_) & (t["Time exit"] == time) & (t.Sizing == sizing)]
    return float(r[col].iloc[0])


charts = []
for col, title, fname, ylim in [
        ("CAGR %", "Time exits lower CAGR in most cases, sharply with no target", "_c1.png", (0, 11)),
        ("Max DD %", "...but they also cut the drawdown of the no-target versions", "_c2.png", (-62, 0))]:
    fig, ax = plt.subplots(figsize=(7.2, 3.4), dpi=200)
    x = np.arange(len(GROUPS)); w = 0.2
    for i, tm in enumerate(TIMES):
        vals = [val(s, e, tm, "2%/4", col) for s, e in GROUPS]
        c = DARK if tm == "None" else BLUE
        a = 1.0 if tm == "None" else [0.35, 0.6, 0.9][i - 1]
        ax.bar(x + (i - 1.5) * w, vals, w * 0.92, color=c, alpha=a,
               label="No time exit" if tm == "None" else f"Exit after {tm}", zorder=2)
        for xi, v in zip(x + (i - 1.5) * w, vals):
            ax.text(xi, v + (0.15 if v >= 0 else -1.0), f"{v:.1f}" if col == "CAGR %" else f"{v:.0f}",
                    ha="center", va="bottom" if v >= 0 else "top", fontsize=6, color=DARK)
    ax.set_xticks(x, [f"{'Candle low' if s == 'Candle low' else 'Week low'}\n{e}" for s, e in GROUPS], fontsize=7.5)
    ax.set_ylim(*ylim)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.axhline(0, color=GREY, lw=0.8)
    ax.legend(frameon=False, fontsize=7, ncol=4, loc="upper right" if col == "CAGR %" else "lower right")
    ax.set_title(title, loc="left", fontsize=10, fontweight="bold", color=DARK)
    ax.set_ylabel(col.replace(" %", "") + " (2% risk, 4 slots)", color=GREY, fontsize=8)
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=GREY, length=0); ax.grid(axis="y", color="#e2e8f0", zorder=0)
    fig.tight_layout(); p = ROOT / "reports" / fname; fig.savefig(p); plt.close(fig); charts.append(p)

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=17, leading=21, alignment=0,
                    textColor=colors.HexColor(DARK), spaceAfter=2)
SUB = ParagraphStyle("SUB", parent=ss["Normal"], fontSize=9, textColor=colors.HexColor(GREY))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12.5, textColor=colors.HexColor(DARK),
                    spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("P", parent=ss["Normal"], fontSize=9.5, leading=13.5, spaceAfter=4)
B = ParagraphStyle("B", parent=P, leftIndent=10, spaceAfter=2)
SM = ParagraphStyle("SM", parent=P, fontSize=8, leading=10.5, textColor=colors.HexColor(GREY))


def table(rows, widths, num_from=1, bold_rows=()):
    tb = Table(rows, colWidths=widths, repeatRows=1)
    st = [("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.4), ("FONT", (0, 1), (-1, -1), "Helvetica", 7.4),
          ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(DARK)),
          ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
          ("ALIGN", (num_from, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
          ("TOPPADDING", (0, 0), (-1, -1), 2.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2)]
    for r in bold_rows:
        st.append(("FONT", (0, r), (-1, r), "Helvetica-Bold", 7.4))
    tb.setStyle(TableStyle(st))
    return tb


# best time exit per (stop, exit, sizing) vs none
cmp = []
for (s, e) in GROUPS:
    for sz in ["2%/4", "1%/8"]:
        base = val(s, e, "None", sz, "CAGR %")
        best_t = max(TIMES[1:], key=lambda tm: val(s, e, tm, sz, "CAGR %"))
        cmp.append((s, e, sz, base, best_t, val(s, e, best_t, sz, "CAGR %")))
better = [c for c in cmp if c[5] > c[3] + 0.05]
nt = ("Candle low", "No target")
story = [
    Paragraph("EMA61 Breakout: Do Time Exits Improve CAGR?", H1),
    Paragraph("Rs 1,00,000 shared capital · NIFTY 500 · monthly breakouts · time exits at 90 / 180 / 365 days · "
              "Jan 2000 – Nov 2026 · Sharekhan costs · prepared 17 Nov 2026", SUB),
    Paragraph("Data: actual traded prices (adjusted for splits and bonuses, not for dividends; dividend income is not counted). Junk pre-listing quotes removed. Re-run on 17 Nov 2026.", SM),
    Spacer(1, 8),
    Paragraph("Answer", H2),
    Paragraph(f"<b>No.</b> Recycling slots with a time exit raised CAGR by more than 0.05 points in only "
              f"{len(better)} of {len(cmp)} combinations, by at most "
              f"{max((c[5] - c[3] for c in better), default=0):.1f} points. For the best strategies it costs a lot: "
              f"the candle-low no-target version falls from {val(*nt, 'None', '2%/4', 'CAGR %'):.1f}% to "
              f"{val(*nt, '90 days', '2%/4', 'CAGR %'):.1f}% CAGR with a 90-day exit, and the weekly-stop no-target "
              f"version from {val('Week low fixed', 'No target', 'None', '1%/8', 'CAGR %'):.1f}% to "
              f"{val('Week low fixed', 'No target', '90 days', '1%/8', 'CAGR %'):.1f}% (1% / 8 slots).", P),
    Paragraph(f"The one real benefit is a smaller drawdown: the candle-low no-target drawdown shrinks from "
              f"{val(*nt, 'None', '2%/4', 'Max DD %'):.0f}% to {val(*nt, '90 days', '2%/4', 'Max DD %'):.0f}% with a "
              f"90-day exit, at the price of most of the return. It does not hold for the weekly-stop target versions: "
              f"there, time exits make the drawdown worse (30% target: "
              f"{val('Week low fixed', 'Target 30%', 'None', '2%/4', 'Max DD %'):.0f}% to "
              f"{val('Week low fixed', 'Target 30%', '90 days', '2%/4', 'Max DD %'):.0f}% with a 90-day exit).", P),
    Paragraph("Rules", H2),
    Paragraph("Same strategies as the earlier studies (monthly Open < EMA61 < Close, buy above the breakout high "
              "next month; stop at the monthly candle low, or at the previous week's low with weekly/daily EMA61 "
              "filters). <b>Time exit:</b> if a trade is still open N calendar days after entry, sell at that "
              "day's open. Freed slots are filled by the next signals (tightest stop first). Sizing: 2% risk / "
              "4 slots and 1% risk / 8 slots.", P),
    KeepTogether([Paragraph("CAGR", H2), Image(str(charts[0]), width=172 * mm, height=81 * mm)]),
    KeepTogether([Paragraph("Max drawdown", H2), Image(str(charts[1]), width=172 * mm, height=81 * mm)]),
    Paragraph("Why recycling does not help", H2),
]
_c = pd.read_csv(ROOT / "data" / "trade_duration" / "conditional.csv")
_c = _c[_c["After days"].between(90, 365)]["Win % if still open"]
_w = t[t["Time exit"] == "None"]["Win %"]
_n = lambda stop, exit_, tm, col: val(stop, exit_, tm, "2%/4", col)
_tgt = [val(s, e, "90 days", z, "Trades taken") / val(s, e, "None", z, "Trades taken")
        for s in ["Candle low", "Week low fixed"] for e in ["Target 15%", "Target 30%"] for z in ["2%/4", "1%/8"]]
pts = [
    f"<b>Old trades are better than new ones.</b> Trades still open after 90–365 days eventually win "
    f"{_c.min():.0f}–{_c.max():.0f}% of the time (see the duration tables in the other reports). A time exit "
    f"swaps them for fresh signals, which win only {_w.min():.0f}–{_w.max():.0f}% of the time.",
    "<b>The big winners get cut.</b> With no target, nearly all profit comes from a few trades held for years. "
    f"A 90-day exit caps them: the average trade falls from about {_n(*nt, 'None', 'Avg trade %'):+.0f}% to "
    f"{_n(*nt, '90 days', 'Avg trade %'):+.0f}% (candle low, 2% / 4 slots).",
    f"<b>More trades, more costs.</b> For the no-target versions a 90-day exit multiplies the trade count "
    f"({_n(*nt, 'None', 'Trades taken'):.0f} to {_n(*nt, '90 days', 'Trades taken'):.0f} for candle low at 2% / 4 "
    f"slots); for the target versions by {min(_tgt):.1f} to {max(_tgt):.1f} times. Each trade pays about 1.13% round trip.",
    f"<b>Deployment falls, not rises.</b> Capital deployed drops (e.g. {_n(*nt, 'None', 'Avg deployed %'):.0f}% to "
    f"{_n(*nt, '90 days', 'Avg deployed %'):.0f}% for candle-low no target with a 90-day exit), "
    "because the long winners were what kept capital invested.",
]
story += [Paragraph(x, B, bulletText="•") for x in pts]
story += [Paragraph("Full results", H2)]
hdr = ["Stop", "Exit", "Time exit", "Sizing", "CAGR %", "Max DD %", "Trades", "Skipped", "Win %",
       "Avg trade %", "Med. hold (d)", "Deployed %"]
rows, bold = [hdr], []
for (s, e) in GROUPS:
    for sz in ["2%/4", "1%/8"]:
        best = max(TIMES, key=lambda tm: val(s, e, tm, sz, "CAGR %"))
        for tm in TIMES:
            r = t[(t.Stop == s) & (t.Exit == e) & (t["Time exit"] == tm) & (t.Sizing == sz)].iloc[0]
            rows.append([s.replace("Week low fixed", "Week low"), e, tm, sz, f"{r['CAGR %']:.1f}",
                         f"{r['Max DD %']:.1f}", f"{int(r['Trades taken']):,}", f"{int(r['Signals skipped']):,}",
                         f"{r['Win %']:.1f}", f"{r['Avg trade %']:.1f}", f"{r['Median hold days']:.0f}",
                         f"{r['Avg deployed %']:.1f}"])
            if tm == best:
                bold.append(len(rows) - 1)
story += [table(rows, [16 * mm, 16 * mm, 15 * mm, 12 * mm, 13 * mm, 14 * mm, 12 * mm, 13 * mm, 11 * mm,
                       17 * mm, 18 * mm, 16 * mm], num_from=4, bold_rows=bold),
          Paragraph("Bold = best CAGR within each stop / exit / sizing group. Trades taken by the portfolio only.",
                    SM),
          Paragraph("Survivorship bias: today's NIFTY 500 members only, so absolute returns are optimistic; "
                    "the comparison between time exits is the useful part.", SM),
          Paragraph("How to reproduce", H2),
          Paragraph("<font face='Courier' size='8'>python examples/time_exit_study.py<br/>"
                    "python reports/time_exit_report.py</font>", P),
          Paragraph("Code: max_days in lib/ema61.py and lib/ema61_mtf.py; lib/portfolio.py. For research and "
                    "education only; not investment advice.", SM)]


def footer(c, d):
    c.setFont("Helvetica", 7.5); c.setFillColor(colors.HexColor(GREY))
    c.drawString(18 * mm, 10 * mm, "EMA61 breakout – time exits")
    c.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {d.page}")


SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                  bottomMargin=16 * mm, title="EMA61 Breakout: Time Exits").build(
    story, onFirstPage=footer, onLaterPages=footer)
for c in charts:
    c.unlink()
print(OUT, "| better:", [(c[0], c[1], c[2], round(c[3], 1), c[4], round(c[5], 1)) for c in better])
