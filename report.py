"""Standard PDF for any saved run.

    python report.py results/stochrsi_pullback/weekly_candle_stop/nifty500
    python report.py results/*/*/*            # every run

Writes report.pdf inside the run folder. Everything in it is computed from config.json,
summary.csv, equity.csv and fills_*.csv; nothing is written by hand.
"""
import json, sys
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

BLUE, GREY, DARK, RED = "#2563eb", "#64748b", "#0f172a", "#dc2626"
TF = {"M": "monthly", "W": "weekly", "D": "daily"}
ss = getSampleStyleSheet()
H1 = ParagraphStyle("H1", parent=ss["Title"], fontSize=17, leading=21, alignment=0, textColor=colors.HexColor(DARK), spaceAfter=2)
SUB = ParagraphStyle("SUB", parent=ss["Normal"], fontSize=9, textColor=colors.HexColor(GREY))
H2 = ParagraphStyle("H2", parent=ss["Heading2"], fontSize=12.5, textColor=colors.HexColor(DARK), spaceBefore=10, spaceAfter=4)
P = ParagraphStyle("P", parent=ss["Normal"], fontSize=9.5, leading=13.5, spaceAfter=4)
SM = ParagraphStyle("SM", parent=P, fontSize=8, leading=10.5, textColor=colors.HexColor(GREY))


def style(ax):
    for s in ("top", "right", "left"):
        ax.spines[s].set_visible(False)
    ax.tick_params(colors=GREY, length=0, labelsize=8)
    ax.grid(axis="y", color="#e2e8f0", zorder=0)


def table(rows, widths, num_from=1):
    tb = Table(rows, colWidths=widths, repeatRows=1)
    tb.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 7.8), ("FONT", (0, 1), (-1, -1), "Helvetica", 7.8),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(DARK)),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("ALIGN", (num_from, 0), (-1, -1), "RIGHT"), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return tb


def rules(c):
    s, tf = c["setup"], TF[c["timeframe"]]
    if s["type"] == "ema_breakout":
        setup = f"{tf.capitalize()} candle opens below and closes above EMA{s['span']}"
    else:
        setup = (f"{tf.capitalize()} Stochastic RSI ({s['rsi']},{s['stoch']},{s['k']},{s['d']}): %K crosses above %D "
                 f"with %D below {s['oversold']}")
        if s["type"] == "stochrsi_macd":
            a, b, c9 = s.get("macd", [12, 26, 9])
            setup += (f"; then MACD ({a},{b},{c9}) crosses above its signal line while below zero, in the same "
                      f"{tf[:-2]} or within {s.get('window', 3)} {tf[:-2]}s. Signal candle = the MACD-cross candle")
    rows = [["Rule", "Value"], ["Setup", setup]]
    f = c.get("filters", {})
    if "trend_ema" in f:
        rows.append(["Trend", f"Close above EMA{f['trend_ema']['span']} on "
                     + ", ".join(TF[x] for x in f["trend_ema"]["timeframes"]) + " (last completed bars)"])
    if "rsi_min" in f:
        rows.append(["Momentum", f"{tf.capitalize()} RSI({f['rsi_min']['period']}) > {f['rsi_min']['value']}"])
    e = c.get("entry", {})
    ent = f"Buy above the signal candle's high during the next {e.get('valid_bars', 1)} {tf} candle(s)"
    df = e.get("day_filters", {})
    if df:
        ent += "; only on days when " + " and ".join(
            {"weekly_ema": f"last week's close >= weekly EMA{df.get('weekly_ema')}",
             "daily_ema": f"yesterday's close >= daily EMA{df.get('daily_ema')}",
             "market_sma": f"NIFTY 50 closed above its {df.get('market_sma')}-day average yesterday "
                           f"(Sensex before mid-2008)"}[k] for k in df)
    rows.append(["Entry", ent])
    st = c["stop"]
    stop = {"signal_low": "Signal candle's low", "prev_week_low": "Low of the previous completed week",
            "trail_pct": f"Trailing {st.get('pct', 0) * 100:g}% (fixed rupees)", "none": "None"}[st["type"]]
    if st.get("trail") == "weekly_low":
        stop += ", raised to each completed week's low"
    rows.append(["Stop", stop])
    ex = c["exits"]
    tg = [t for t in ex["targets_pct"] if t is not None]
    xs = []
    if tg:
        xs.append("targets " + ", ".join(f"{t:g}%" for t in tg))
    if None in ex["targets_pct"]:
        xs.append(f"no target (exit on {tf} close below EMA{ex['ema_close_when_no_target']['span']})"
                  if ex.get("ema_close_when_no_target") else "no target (stop only)")
    if ex.get("max_days"):
        xs.append(f"time exit after {ex['max_days']} days")
    rows.append(["Exits", "; ".join(xs)])
    z = c["sizing"]
    rows.append(["Sizing", f"{z['risk_pct']:g}% of starting capital at risk per trade; max {z['max_positions']} "
                 f"open trades; tightest stop filled first"])
    k = c["costs"]
    rows.append(["Costs", f"{k['broker'].capitalize()} {k['product']} fees + {k['slippage_pct']:g}% slippage per side"])
    return [[a, Paragraph(b, SM)] for a, b in rows[1:]], rows[0]


def build(run: Path):
    c = json.load(open(run / "config.json"))
    S = pd.read_csv(run / "summary.csv", index_col=0)
    EQ = pd.read_csv(run / "equity.csv", index_col=0, parse_dates=True)
    charts = []
    fig, ax = plt.subplots(figsize=(7.2, 3.2), dpi=200)
    cm = plt.get_cmap("Blues")
    for i, col in enumerate(S.index):
        e = EQ[col].dropna()
        ax.plot(e.index, e / 1e5, lw=1.4, color=DARK if col == "No target" else cm(0.35 + 0.6 * i / max(1, len(S) - 1)),
                label=col.replace("Target ", ""))
    ax.set_yscale("log"); ax.yaxis.set_major_formatter(lambda v, _: f"Rs {v:g}L")
    ax.legend(frameon=False, fontsize=7.5, loc="upper left", ncol=4)
    ax.set_title("Equity", loc="left", fontsize=10.5, fontweight="bold", color=DARK)
    style(ax); fig.tight_layout(); p = run / "_c1.png"; fig.savefig(p); plt.close(fig); charts.append(p)

    fig, ax = plt.subplots(figsize=(7.2, 2.6), dpi=200)
    for i, col in enumerate(S.index):
        e = EQ[col].dropna()
        ax.plot(e.index, (e / e.cummax() - 1) * 100, lw=1.1,
                color=DARK if col == "No target" else cm(0.35 + 0.6 * i / max(1, len(S) - 1)))
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0f}%")
    ax.set_title("Drawdown from peak", loc="left", fontsize=10.5, fontweight="bold", color=DARK)
    style(ax); fig.tight_layout(); p = run / "_c2.png"; fig.savefig(p); plt.close(fig); charts.append(p)

    wl = [["Exit", "Closed trades", "Win %", "Avg net win %", "Avg net loss %", "Med days win", "Med days loss", "Net P&L (Rs)"]]
    for col in S.index:
        tag = "none" if col == "No target" else col.split()[1].rstrip("%")
        f = pd.read_csv(run / f"fills_{tag}.csv")
        f = f.dropna(subset=["exit_date"])
        r = (f.proceeds / f.cost - 1) * 100
        held = (pd.to_datetime(f.exit_date) - pd.to_datetime(f.entry_date)).dt.days
        wl.append([col, f"{len(f):,}", f"{(r > 0).mean() * 100:.0f}",
                   f"{r[r > 0].mean():.1f}", f"{r[r <= 0].mean():.1f}",
                   f"{held[r > 0].median():.0f}", f"{held[r <= 0].median():.0f}", f"{(f.proceeds - f.cost).sum():,.0f}"])

    best = S["CAGR %"].idxmax(); b = S.loc[best]
    eq = EQ[best].dropna(); dd = eq / eq.cummax() - 1; tr = dd.idxmin(); pk = eq[:tr].idxmax()
    rl, hdr = rules(c)
    story = [Paragraph(c["name"], H1),
             Paragraph(f"Rs {c['sizing']['capital']:,} capital · {c['sizing']['risk_pct']:g}% risk · max "
                       f"{c['sizing']['max_positions']} open trades · {c['universe']} · from {c['period']['start']} · "
                       f"{eq.index[-1]:%d %b %Y}", SUB),
             Paragraph("Data: actual traded prices (split/bonus adjusted, not dividend adjusted; dividends not counted). "
                       "Today's index members only (survivorship bias).", SM),
             Spacer(1, 6), Paragraph(c.get("description", ""), P),
             Paragraph("Result", H2),
             Paragraph(f"Best exit: <b>{best}</b> at <b>{b['CAGR %']:.1f}% CAGR</b> with a {b['Max DD %']:.0f}% maximum "
                       f"drawdown ({pk:%b %Y} to {tr:%b %Y}), {b['Win %']:.0f}% winners over "
                       f"{int(b['Trades taken'])} trades. Across exits CAGR ranges "
                       f"{S['CAGR %'].min():.1f}% to {S['CAGR %'].max():.1f}%.", P),
             Paragraph("Rules", H2), table([hdr] + rl, [22 * mm, 152 * mm], num_from=9),
             KeepTogether([Spacer(1, 6), Image(str(charts[0]), width=172 * mm, height=76 * mm)]),
             KeepTogether([Image(str(charts[1]), width=172 * mm, height=62 * mm)])]
    cols = [("CAGR %", "{:.1f}"), ("Max DD %", "{:.1f}"), ("Final equity (Rs)", "{:,.0f}"), ("Trades taken", "{:,.0f}"),
            ("Signals skipped", "{:,.0f}"), ("Win %", "{:.1f}"), ("Median trade %", "{:.1f}"),
            ("Median hold days", "{:.0f}"), ("Median stop %", "{:.1f}"), ("Avg deployed %", "{:.0f}"),
            ("Worst trade % of capital", "{:.1f}")]
    hdr2 = ["Exit", "CAGR %", "Max DD %", "Final equity", "Trades", "Skipped", "Win %", "Median %", "Med hold d",
            "Stop %", "Deployed %", "Worst %"]
    rows = [hdr2] + [[i.replace("Target ", "")] + [f.format(r[k]) for k, f in cols] for i, r in S.iterrows()]
    story += [KeepTogether([Paragraph("Full results", H2),
                            table(rows, [17 * mm, 13 * mm, 15 * mm, 18 * mm, 12 * mm, 13 * mm, 11 * mm, 14 * mm,
                                         15 * mm, 12 * mm, 16 * mm, 13 * mm]),
                            Paragraph("Median % = median net trade return. Stop % = median stop distance below entry. "
                                      "Deployed % = open positions / equity, averaged over all days. Worst % = worst "
                                      "trade as a share of starting capital.", SM)]),
              KeepTogether([Paragraph("Wins and losses (closed trades, after costs)", H2),
                            table(wl, [24 * mm, 22 * mm, 14 * mm, 22 * mm, 22 * mm, 22 * mm, 22 * mm, 26 * mm])]),
              Paragraph("Reproduce", H2),
              Paragraph(f"<font face='Courier' size='8'>python run_strategy.py strategies/{c['name']}.json"
                        + (f" --universe {c['universe']}" if c["universe"] != "NIFTY500" else "")
                        + f"<br/>python report.py {run.as_posix()}</font>", P),
              Paragraph("For research and education only; not investment advice.", SM)]

    def footer(cv, d):
        cv.setFont("Helvetica", 7.5); cv.setFillColor(colors.HexColor(GREY))
        cv.drawString(18 * mm, 10 * mm, f"{c['name']} · {c['universe']}")
        cv.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {d.page}")

    out = run / "report.pdf"
    SimpleDocTemplate(str(out), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                      bottomMargin=16 * mm, title=c["name"]).build(story, onFirstPage=footer, onLaterPages=footer)
    for p in charts:
        p.unlink()
    return out


if __name__ == "__main__":
    for a in sys.argv[1:]:
        if (Path(a) / "config.json").exists():
            print(build(Path(a)))
