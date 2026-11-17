"""Build reports/ema61_stochrsi_weekly.pdf from data/stochrsi_r1_p8_weekly
(examples/stochrsi_pullback_study.py --tf W --skip-none --targets 4,6,8,10,12,15),
compared with the monthly version (data/stochrsi_r1_p8)."""
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "ema61_stochrsi_weekly.pdf"
D = ROOT / "data" / "stochrsi_r1_p8_weekly"
BLUE, GREY, DARK, RED = "#2563eb", "#64748b", "#0f172a", "#dc2626"
S = pd.read_csv(D / "summary.csv", index_col=0)
EQ = pd.read_csv(D / "equity.csv", index_col=0, parse_dates=True)
SM_ = pd.read_csv(ROOT / "data" / "stochrsi_r1_p8" / "summary.csv", index_col=0)
EM = pd.read_csv(ROOT / "data" / "stochrsi_r1_p8" / "equity.csv", index_col=0, parse_dates=True)
NT = "No target (close<EMA61)"
TG = [int(i.split()[1].rstrip("%")) for i in S.index]

# per-trade net win/loss from closed fills
wl = {}
for t in TG:
    f = pd.read_csv(D / f"fills_{t}.csv").dropna(subset=["exit_date"])
    r = (f.proceeds / f.cost - 1) * 100
    wl[t] = dict(win=r[r > 0].mean(), loss=r[r <= 0].mean(), n=len(f),
                 costs=(f.cost * 0.00565 + f.proceeds * 0.00565).sum(), net=(f.proceeds - f.cost).sum())


def style(ax):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=GREY, length=0, labelsize=8)
    ax.grid(axis="y", color="#e2e8f0", zorder=0)


charts = []
fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=200)
cm = plt.get_cmap("Blues")
for i, c in enumerate(S.index):
    e = EQ[c].dropna(); ax.plot(e.index, e / 1e5, lw=1.3, color=cm(0.35 + 0.6 * i / (len(S) - 1)), label=c.replace("Target ", ""))
m = EM[NT].dropna(); ax.plot(m.index, m / 1e5, lw=1.8, color="#94a3b8", label="Monthly, no target")
ax.set_yscale("log"); ax.yaxis.set_major_formatter(lambda v, _: f"Rs {v:g}L")
ax.legend(frameon=False, fontsize=7.5, loc="upper left", ncol=4)
ax.set_title("Weekly targets vs the monthly no-target version", loc="left", fontsize=10.5, fontweight="bold", color=DARK)
ax.set_ylabel("Equity (log scale)", color=GREY, fontsize=8)
style(ax); fig.tight_layout(); p = ROOT / "reports" / "_w1.png"; fig.savefig(p); plt.close(fig); charts.append(p)

fig, ax = plt.subplots(figsize=(7.2, 2.8), dpi=200)
v = S["CAGR %"].values
ax.bar(range(len(v)), v, 0.55, color=[RED if x < 0 else BLUE for x in v], zorder=2)
for x, y in enumerate(v):
    ax.text(x, y + (0.3 if y >= 0 else -1.0), f"{y:.1f}%", ha="center", fontsize=7.5, color=DARK)
ax.axhline(0, color=GREY, lw=0.8)
ax.set_xticks(range(len(v)), [f"{t}%" for t in TG]); ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax.set_title("CAGR by target: none of them pays", loc="left", fontsize=10.5, fontweight="bold", color=DARK)
style(ax); fig.tight_layout(); p = ROOT / "reports" / "_w2.png"; fig.savefig(p); plt.close(fig); charts.append(p)

fig, ax = plt.subplots(figsize=(7.2, 2.8), dpi=200)
ax.plot(TG, S["Win %"].values, marker="o", color=BLUE, lw=1.8, label="Win %")
ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
ax2 = ax.twinx(); ax2.plot(TG, S["Max DD %"].values, marker="s", color=RED, lw=1.5, label="Max drawdown")
ax2.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%"); ax2.tick_params(colors=GREY, length=0, labelsize=8)
for s in ("top", "right", "left"):
    ax2.spines[s].set_visible(False)
ax.set_xticks(TG, [f"{t}%" for t in TG])
ax.set_title("High win rates at small targets come with the deepest drawdowns", loc="left", fontsize=10.5, fontweight="bold", color=DARK)
ax.legend(frameon=False, fontsize=8, loc="upper right"); ax2.legend(frameon=False, fontsize=8, loc="lower right")
style(ax); fig.tight_layout(); p = ROOT / "reports" / "_w3.png"; fig.savefig(p); plt.close(fig); charts.append(p)

ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=17, leading=21, alignment=0, textColor=colors.HexColor(DARK), spaceAfter=2)
SUB = ParagraphStyle("SUB", parent=ss["Normal"], fontSize=9, textColor=colors.HexColor(GREY))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12.5, textColor=colors.HexColor(DARK), spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("P", parent=ss["Normal"], fontSize=9.5, leading=13.5, spaceAfter=4)
BL = ParagraphStyle("BL", parent=P, leftIndent=10, spaceAfter=2)
SM = ParagraphStyle("SM", parent=P, fontSize=8, leading=10.5, textColor=colors.HexColor(GREY))


def table(rows, widths, num_from=1):
    tb = Table(rows, colWidths=widths, repeatRows=1)
    tb.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.8), ("FONT", (0, 1), (-1, -1), "Helvetica", 7.8),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(DARK)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("ALIGN", (num_from, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return tb


best = S["CAGR %"].idxmax(); bst = S.loc[best]; mo = SM_.loc[NT]
stop = S["Median stop %"].median()
story = [
    Paragraph("Stochastic RSI Pullback on Weekly Candles", H1),
    Paragraph("Rs 1,00,000 capital · 1% risk per trade · max 8 open trades · NIFTY 500 constituents (499 stocks) · "
              "Jan 2000 – Nov 2026 · prepared 17 Nov 2026", SUB),
    Paragraph("Data: actual traded prices (adjusted for splits and bonuses, not for dividends; dividend income is not counted). Junk pre-listing quotes removed.", SM),
    Spacer(1, 8),
    Paragraph("Answer", H2),
    Paragraph(f"Moving the pullback setup from monthly to weekly candles, with fixed targets of 4–15%, does not work. "
              f"CAGR ranges from <b>{S['CAGR %'].min():.1f}% to {S['CAGR %'].max():.1f}%</b>; the best is the "
              f"{best.split()[1]} target at {bst['CAGR %']:.1f}% with a {bst['Max DD %']:.0f}% drawdown. The monthly "
              f"version with no target made {mo['CAGR %']:.1f}% with a {mo['Max DD %']:.0f}% drawdown.", P),
    Paragraph(f"The core problem: the median stop (signal week's low) is <b>{stop:.1f}% below entry</b>, wider than most of "
              f"the targets. Small targets win often but each loss is bigger than each win, and costs of about 1.1% per "
              f"round trip take a large share of every gain.", P),
    Paragraph("Rules", H2),
    table([["Rule", "Value"],
           ["Trend", "Close above EMA61 on monthly (last completed month), weekly and daily (week's last close)"],
           ["Momentum", "Weekly RSI(14) > 50"],
           ["Trigger", "Weekly Stochastic RSI (14,14,3,3): %K crosses above %D this week, with %D below 30"],
           ["Entry", "Next week, buy when price goes above the signal week's high (gap fills at open)"],
           ["Stop", "Signal week's low (fixed)"],
           ["Exits", "Fixed targets 4%, 6%, 8%, 10%, 12%, 15% or the stop; no other exit"],
           ["Sizing", "1% of starting capital (Rs 1,000) at risk per trade; max 8 open trades"],
           ["Costs", "Sharekhan delivery 0.465% per side + 0.1% slippage per side"]],
          [24 * mm, 150 * mm], num_from=9),
    KeepTogether([Paragraph("Equity", H2), Image(str(charts[0]), width=172 * mm, height=76 * mm)]),
    KeepTogether([Paragraph("Return by target", H2), Image(str(charts[1]), width=172 * mm, height=67 * mm)]),
    KeepTogether([Paragraph("Win rate and drawdown", H2), Image(str(charts[2]), width=172 * mm, height=67 * mm)]),
]
cols = [("CAGR %", "{:.1f}"), ("Max DD %", "{:.1f}"), ("Final equity (Rs)", "{:,.0f}"),
        ("Trades taken", "{:,.0f}"), ("Signals skipped", "{:,.0f}"), ("Win %", "{:.1f}"),
        ("Median trade %", "{:.1f}"), ("Median hold days", "{:.0f}"), ("Median stop %", "{:.1f}"),
        ("Avg deployed %", "{:.1f}"), ("Days with 0 positions %", "{:.0f}")]
hdr = ["Target", "CAGR %", "Max DD %", "Final equity", "Trades", "Skipped", "Win %", "Median %",
       "Med hold d", "Stop %", "Deployed %", "Idle days %"]
rows = [hdr] + [[i.replace("Target ", "")] + [f.format(r[c]) for c, f in cols] for i, r in S.iterrows()]
story += [Paragraph("Full results", H2),
          table(rows, [14 * mm, 13 * mm, 15 * mm, 18 * mm, 12 * mm, 13 * mm, 11 * mm, 14 * mm, 15 * mm,
                       12 * mm, 16 * mm, 16 * mm]),
          Paragraph("Median % = median net trade return. Stop % = median stop distance below entry. Deployed % = open "
                    "positions / equity, averaged over all days. Idle days % = days with no open position.", SM)]
wrows = [["Target", "Closed trades", "Avg net win %", "Avg net loss %", "Costs paid (Rs)", "Net trade P&L (Rs)"]]
for t in TG:
    w = wl[t]
    wrows.append([f"{t}%", f"{w['n']:,}", f"{w['win']:.1f}", f"{w['loss']:.1f}", f"{w['costs']:,.0f}", f"{w['net']:,.0f}"])
story += [KeepTogether([Paragraph("Why it loses: wins smaller than losses", H2),
                        table(wrows, [20 * mm, 26 * mm, 28 * mm, 28 * mm, 34 * mm, 36 * mm]),
                        Paragraph("Net = after fees and slippage. Costs paid are estimated at 0.565% of buy value plus "
                                  "0.565% of sell value.", SM)])]
cmp_rows = [["1% / 8", "CAGR %", "Max DD %", "Win %", "Trades", "Median stop %"]]
for name, r in [("Monthly, no target", mo), (f"Weekly, {best.split()[1]} target", bst)]:
    cmp_rows.append([name, f"{r['CAGR %']:.1f}", f"{r['Max DD %']:.1f}", f"{r['Win %']:.0f}",
                     f"{int(r['Trades taken']):,}", f"{r['Median stop %']:.1f}"])
story += [KeepTogether([Paragraph("Against the monthly version", H2),
                        table(cmp_rows, [46 * mm, 22 * mm, 22 * mm, 18 * mm, 22 * mm, 26 * mm])])]
lo = S.iloc[0]
pts = [
    f"<b>Win rate is misleading here.</b> The {TG[0]}% target wins {lo['Win %']:.0f}% of trades yet loses "
    f"{-lo['CAGR %']:.1f}% a year with a {lo['Max DD %']:.0f}% drawdown.",
    f"<b>The weekly candle stop is too wide for these targets.</b> At a {stop:.1f}% median stop, a target needs to be "
    f"well above 8% just to break even after costs at a 50% win rate.",
    f"<b>Many more trades, more cost.</b> {int(S['Trades taken'].min()):,}–{int(S['Trades taken'].max()):,} trades "
    f"versus {int(mo['Trades taken'])} for the monthly version; each one pays about 1.1% in fees and slippage.",
    f"<b>Results depend on the slot rule.</b> About {int(S['Signals skipped'].median()):,} signals were skipped "
    f"because all 8 slots were full, so which trades get taken (tightest stop first) matters a lot.",
    "<b>Survivorship bias:</b> today's NIFTY 500 members only, so even these weak returns are optimistic.",
]
story += [Paragraph("What the study shows", H2)] + [Paragraph(x, BL, bulletText="•") for x in pts]
nxt = ["<b>Let winners run:</b> exit on a weekly close below EMA21 or EMA61 instead of a fixed target.",
       "<b>Tighter setups only:</b> take signal weeks with a range under about 5%, so targets exceed the risk.",
       "<b>Stick with monthly:</b> the monthly version with no target remains the better result so far."]
story += [Paragraph("Next tests", H2)] + [Paragraph(x, BL, bulletText="•") for x in nxt]
story += [Paragraph("How to reproduce", H2),
          Paragraph("<font face='Courier' size='8'>python examples/stochrsi_pullback_study.py --tf W --skip-none "
                    "--targets 4,6,8,10,12,15<br/>python reports/stochrsi_weekly_report.py</font>", P),
          Paragraph("Code: lib/stochrsi_mtf.py (simulate_weekly), lib/portfolio.py (shared-capital simulator). "
                    "For research and education only; not investment advice.", SM)]


def footer(c, d):
    c.setFont("Helvetica", 7.5); c.setFillColor(colors.HexColor(GREY))
    c.drawString(18 * mm, 10 * mm, "Stochastic RSI pullback – weekly candles")
    c.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {d.page}")


SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                  bottomMargin=16 * mm, title="Stochastic RSI Pullback Weekly").build(story, onFirstPage=footer, onLaterPages=footer)
for c in charts:
    c.unlink()
print(OUT)
for t in TG: print(t, {k: round(v, 1) for k, v in wl[t].items()})
