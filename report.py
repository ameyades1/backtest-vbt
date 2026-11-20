"""Standard PDF for any saved run.

    python report.py results/stochrsi_pullback/weekly_candle_stop/nifty500
    python report.py results/*/*/*            # every run

Writes report.pdf inside the run folder. Everything in it is computed from config.json,
summary.csv, equity.csv and fills_*.csv; nothing is written by hand.
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib import ids
_IDS = ids.by_name()
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


SCORE_TEXT = {
    "macd_turn": "competing signals ranked by monthly MACD (histogram turning up below zero first, then turning up "
                 "above zero)",
    "weekly_pattern": "competing signals with a weekly bullish TA-Lib pattern (engulfing, hammer, morning star, "
                      "piercing) in the last 2 completed weeks first",
    "macd_pattern": "competing signals ranked by a 0-3 score: monthly MACD histogram rising +1, rising below zero +1, "
                    "weekly bullish TA-Lib pattern in the last 2 weeks +1",
    "mom": "competing signals ranked by the stock's 6/12-month return percentile",
    "rs_sector": "competing signals ranked by stock + sector relative strength (6-month return percentiles)"}


def rules(c):
    s, tf = c["setup"], TF[c["timeframe"]]
    T = tf.capitalize()
    NEW = {"rsi_pullback": lambda: f"{T} RSI({s.get('period', 2)}) below {s.get('level', 10)}",
           "williams_r": lambda: f"{T} Williams %R({s.get('period', 14)}) crosses back above {s.get('level', -80)}",
           "cci_cross": lambda: f"{T} CCI({s.get('period', 20)}) crosses back above {s.get('level', -100)}",
           "ema_touch": lambda: f"{T} low touches EMA{s.get('span', 21)} and the close is above it",
           "donchian": lambda: f"First {tf} close above the highest high of the prior {s.get('period', 20)} {tf[:-2]}s",
           "bb_squeeze": lambda: (f"{T} close crosses above the upper Bollinger band ({s.get('period', 20)},"
                                  f"{s.get('k', 2.0):g}) within {s.get('recent', 4)} candles of a "
                                  f"{s.get('lookback', 26)}-candle low in band width"),
           "momentum_rotation": lambda: (f"Monthly rotation: hold the {s.get('top', 10)} strongest stocks by "
                                         f"{s.get('lookback', 252) // 21}-1 month return, above their "
                                         f"{s.get('sma', 200)}-day average; keep while in the top "
                                         f"{s.get('top', 10) * s.get('buffer', 2)}; equal weight"
                                         + (f"; no new buys while NIFTY 50 is below its {s['market_sma']}-day average"
                                            if s.get('market_sma') else "")),
           "rs_high": lambda: f"Stock / NIFTY 50 ratio makes a new {s.get('period', 26)}-{tf[:-2]} high"}
    if s["type"] == "ema_breakout":
        setup = f"{tf.capitalize()} candle opens below and closes above EMA{s['span']}"
    elif s["type"] in NEW:
        setup = NEW[s["type"]]()
    else:
        stf = "monthly" if s["type"] == "stochrsi_wmacd" else tf
        setup = (f"{stf.capitalize()} Stochastic RSI ({s['rsi']},{s['stoch']},{s['k']},{s['d']}): %K crosses above %D "
                 f"with %D below {s['oversold']}")
        if s["type"] == "stochrsi_macd":
            a, b, c9 = s.get("macd", [12, 26, 9])
            setup += (f"; then MACD ({a},{b},{c9}) crosses above its signal line while below zero, in the same "
                      f"{tf[:-2]} or within {s.get('window', 3)} {tf[:-2]}s. Signal candle = the MACD-cross candle")
        if s["type"] == "stochrsi_wmacd":
            a, b, c9 = s.get("macd", [12, 26, 9])
            setup += (f" (completed month); then weekly MACD ({a},{b},{c9}) crosses above its signal line while "
                      f"below zero within {s.get('window_weeks', 13)} weeks of that month's end. Signal candle = "
                      f"the MACD-cross week")
    if c.get("side") == "short":
        setup = ("SHORT (stock futures), mirrored on the reciprocal price: " + setup.replace("crosses above", "crosses below")
                 .replace("below 30", "above 70").replace("below 40", "above 60").replace("below 50", "above 50")
                 + "; trend filters, stops and exits mirrored (close below EMA, stop at the previous week's high, cover "
                 "when Supertrend turns bullish)")
        if c.get("symbols_from"):
            setup += f"; only {c['symbols_from']} names"
    rows = [["Rule", "Value"], ["Setup", setup]]
    if s["type"] == "momentum_rotation":
        k = c["costs"]
        rows += [["Fills", "Rebalance on the first trading day of each month at the open, using closes up to the "
                  "previous day; new positions sized at equity / top"],
                 ["Costs", f"{k['broker'].capitalize()} {k['product']} fees + {k['slippage_pct']:g}% slippage per side"]]
        if c["sizing"].get("cash"):
            rows.append(["Idle cash", str(c["sizing"]["cash"])])
        return [[a, Paragraph(b, SM)] for a, b in rows[1:]], rows[0]
    f = c.get("filters", {})
    if "trend_ema" in f:
        rows.append(["Trend", f"Close above EMA{f['trend_ema']['span']} on "
                     + ", ".join(TF[x] for x in f["trend_ema"]["timeframes"]) + " (last completed bars)"])
    if "rsi_min" in f:
        rows.append(["Momentum", f"{TF[f['rsi_min'].get('timeframe', c['timeframe'])].capitalize()} RSI({f['rsi_min']['period']}) > {f['rsi_min']['value']}"])
    FT = {"adx": lambda v: f"ADX({v.get('period', 14)}) >= {v.get('min', 20)} with +DI > -DI",
          "supertrend": lambda v: f"Supertrend({v.get('period', 10)},{v.get('mult', 3):g}) bullish",
          "sma_rising": lambda v: f"close above a rising {v.get('period', 40)}-candle average",
          "ichimoku": lambda v: "close above the Ichimoku cloud",
          "volume": lambda v: f"signal-candle volume above {v.get('mult', 1.5):g} x its {v.get('period', 20)}-candle average",
          "obv_high": lambda v: f"on-balance volume at a {v.get('period', 26)}-candle high",
          "near_high": lambda v: f"close within {v.get('pct', 10)}% of the {v.get('period', 252)}-bar high"}
    for k, fn in FT.items():
        if k in f:
            rows.append(["Filter", f"{TF[f[k].get('timeframe', c['timeframe'])].capitalize()} " + fn(f[k])])
    e = c.get("entry", {})
    ent = f"Buy above the signal candle's high during the next {e.get('valid_bars', 1)} {tf} candle(s)"
    df = e.get("day_filters", {})
    if df:
        ent += "; only on days when " + " and ".join(
            {"weekly_ema": f"last week's close >= weekly EMA{df.get('weekly_ema')}",
             "daily_ema": f"yesterday's close >= daily EMA{df.get('daily_ema')}",
             "market_sma": f"NIFTY 50 closed above its {df.get('market_sma')}-day average yesterday "
                           f"(Sensex before mid-2008)",
             "market_below_sma": f"NIFTY 50 closed below its {df.get('market_below_sma')}-day average yesterday "
                                 f"(Sensex before mid-2008)"}[k] for k in df)
    if e.get("delay_days"):
        ent += f"; entry no earlier than {e['delay_days']} trading day(s) after the signal candle"
    rows.append(["Entry", ent])
    st = c["stop"]
    stop = {"signal_low": "Signal candle's low", "prev_week_low": "Low of the previous completed week",
            "trail_pct": f"Trailing {st.get('pct', 0) * 100:g}% (fixed rupees)", "none": "None",
            "atr": f"{st.get('mult', 2):g} x daily ATR({st.get('period', 14)}) below entry"}[st["type"]]
    if st.get("trail") == "atr":
        stop += f", trailed at the highest high since entry minus {st.get('trail_mult', 3):g} x ATR"
    if st.get("trail") == "weekly_low":
        stop += ", raised to each completed week's low"
    if st.get("market_tighten") == "weekly_low":
        stop += (f"; while NIFTY 50 is below its {st.get('market_sma', 200)}-day average (previous close), raised to "
                 f"the last completed week's low")
    elif st.get("market_tighten") == "exit":
        stop += f"; all open trades sold at the next open when NIFTY 50 closes below its {st.get('market_sma', 200)}-day average"
    rows.append(["Stop", stop])
    ex = c["exits"]
    tg = [t for t in ex["targets_pct"] if t is not None]
    xs = []
    if tg:
        xs.append("targets " + ", ".join(f"{t:g}%" if isinstance(t, (int, float)) else
                                         (f"half at {t[1:]} (rest by the trend exit)" if t.startswith("P") else t)
                                         for t in tg) + ("; R = initial risk (entry minus stop)"
                                                         if any(isinstance(t, str) for t in tg) else ""))
    if None in ex["targets_pct"]:
        xs.append(f"no target (exit on {TF[ex['ema_close_when_no_target'].get('timeframe', c['timeframe'])]} close below EMA{ex['ema_close_when_no_target']['span']})"
                  if ex.get("ema_close_when_no_target") else
                  (f"no target (exit when the {TF[ex['supertrend_exit_when_no_target'].get('timeframe', 'W')]} "
                   f"Supertrend turns bearish)" if ex.get("supertrend_exit_when_no_target") else "no target (stop only)"))
    if ex.get("max_days"):
        xs.append(f"time exit after {ex['max_days']} days")
    if ex.get("time_stop"):
        xs.append(f"time stop: sold at the next open if the close is below +{ex['time_stop'].get('min_r', 0.5):g}R "
                  f"{ex['time_stop']['days']} calendar days after entry")
    if ex.get("pyramid"):
        xs.append(f"pyramid: at +{ex['pyramid']['at_r']:g}R the stop moves to break-even and a second leg of "
                  f"{ex['pyramid'].get('weight', 0.5):g}x risk is added (its stop at the first entry)")
    rows.append(["Exits", "; ".join(xs)])
    z = c["sizing"]
    rows.append(["Sizing", f"{z['risk_pct']:g}% of {'current equity' if z.get('compound') else 'starting capital'} at risk per trade; max {z['max_positions']} "
                 f"open trades; " + (SCORE_TEXT.get(z["score"]["type"], z["score"]["type"])
                 + (", ties by 12-month return" if z["score"].get("tiebreak") == "mom12" else ", ties by tightest stop")
                 if z.get("score") else "tightest stop filled first")])
    extra = []
    if z.get("max_stop_pct"):
        extra.append(f"only signals with a stop within {z['max_stop_pct']:g}% of entry")
    if z.get("dd_rule"):
        d = z["dd_rule"]
        extra.append(f"half risk after a {d.get('halve', 10)}% fall from the equity high until a new high; no new "
                     f"trades for {d.get('pause_days', 21)} trading days on reaching {d.get('pause', 15)}%")
    rr = z.get("risk_rules", {})
    if "market_sma" in rr:
        extra.append(f"x{rr['market_sma'].get('mult', 0.5):g} risk while NIFTY 50 is below its "
                     f"{rr['market_sma'].get('days', 200)}-day average")
    if "breadth" in rr:
        extra.append(f"x{rr['breadth'].get('mult', 0.5):g} risk while under {rr['breadth'].get('min', 40)}% of the "
                     f"universe is above its 200-day average")
    if "vix" in rr:
        extra.append(f"x{rr['vix'].get('mult', 0.5):g} risk while India VIX is above {rr['vix'].get('max', 25)}")
    if z.get("cash"):
        extra.append("idle cash earns " + (f"{z['cash'].get('rate', 6.5):g}% a year (liquid fund)" if z["cash"]["type"] == "liquid"
                                           else "the NIFTY 50 price return (index ETF)"))
    if z.get("sector_top"):
        extra.append(f"only stocks in the {z['sector_top'].get('n', 4)} strongest sectors by "
                     f"{z['sector_top'].get('months', 6)}-month median return")
    if z.get("min_turnover_cr"):
        extra.append(f"only stocks with a 60-day median traded value of at least Rs {z['min_turnover_cr']:g} crore")
    if z.get("liq_top_pct"):
        extra.append(f"only stocks in the top {z['liq_top_pct']:g}% of the universe by 60-day median traded value that day")
    if c["costs"].get("slippage_extra"):
        x = c["costs"]["slippage_extra"]
        extra.append(f"{x['universe']} trades pay {x['pct']:g}% slippage per side")
    if z.get("pos_cap"):
        extra.append(f"positions above {z['pos_cap'] * 100:g}% of equity trimmed at month end")
    if z.get("max_open_risk"):
        extra.append(f"total open risk at most {z['max_open_risk'] * 100:g}% of equity")
    if z.get("hedge"):
        extra.append(f"short NIFTY futures worth {z['hedge'].get('ratio', 1) * 100:g}% of the long book while NIFTY 50 is "
                     f"below its {z['hedge'].get('sma', 200)}-day average")
    if c.get("side") == "short" or c.get("combine"):
        sh = {"margin": 0.25, "roll": 0.001, "max": 6, **z.get("short", {})}
        extra.append(f"shorts: {sh['margin'] * 100:g}% margin, {sh['roll'] * 100:g}% roll cost a month, at most "
                     f"{sh['max']} open, futures fees")
    if z.get("sector_cap"):
        extra.append(f"at most {z['sector_cap']} open positions per sector")
    if c.get("combine"):
        extra.append("shares capital with " + ", ".join(x["config"].split("strategies/")[-1].replace(".json", "")
                                                        + (f" ({x['target']} target)" if x.get("target") else "")
                                                        + (f" ({x['universe']} names)" if x.get("universe") else "")
                                                        for x in c["combine"]))
    if extra:
        rows.append(["Sizing rules", "; ".join(extra)])
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
    sid = c.get("id") or _IDS.get(c["name"], "")
    story = [Paragraph((f"{ids.short(sid)} · " if sid else "") + c["name"], H1),
             *([Paragraph(f"Strategy ID {sid}", SM)] if sid else []),
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
                        + (f" --universe {c['universe']}" if c["universe"] != "NIFTY500_PIT" else "")
                        + f"<br/>python report.py {run.as_posix()}</font>", P),
              Paragraph("For research and education only; not investment advice.", SM)]

    def footer(cv, d):
        cv.setFont("Helvetica", 7.5); cv.setFillColor(colors.HexColor(GREY))
        cv.drawString(18 * mm, 10 * mm, f"{c['name']} · {c['universe']}")
        cv.drawRightString(A4[0] - 18 * mm, 10 * mm, f"Page {d.page}")

    out = run / "report.pdf"
    SimpleDocTemplate(str(out), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                      bottomMargin=16 * mm, title=(f"{ids.short(sid)} " if sid else "") + c["name"]).build(story, onFirstPage=footer, onLaterPages=footer)
    for p in charts:
        p.unlink()
    return out


if __name__ == "__main__":
    for a in sys.argv[1:]:
        if (Path(a) / "config.json").exists():
            print(build(Path(a)))
