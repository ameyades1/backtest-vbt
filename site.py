"""Build docs/index.html: one sortable table of every run in results/.

    python site.py

Reads results/<family>/<variant>/<universe>/{config.json,summary.csv,fills_*.csv}. Self-contained HTML,
no outside libraries; serve with GitHub Pages from /docs on main.
"""
import json, html
from datetime import date
from pathlib import Path
import numpy as np
import pandas as pd
from lib.costs import fee_per_side
from lib import ids

ROOT = Path(__file__).resolve().parent
REPO = "https://github.com/ameyades1/backtest-vbt/blob/main/"


def streak(losses):
    best = cur = 0
    for x in losses:
        cur = cur + 1 if x else 0
        best = max(best, cur)
    return best


IDS = ids.by_name()
rows = []
for cfgp in sorted(ROOT.glob("results/*/*/*/config.json")):
    run = cfgp.parent
    c = json.load(open(cfgp))
    z = c["sizing"]
    fee = fee_per_side(c["costs"]["broker"], c["costs"]["product"]); slip = c["costs"]["slippage_pct"] / 100
    S = pd.read_csv(run / "summary.csv", index_col=0)
    for ex, s in S.iterrows():
        tag = "none" if ex == "No target" else ex.split()[1].rstrip("%")
        f = pd.read_csv(run / f"fills_{tag}.csv", parse_dates=["entry_date", "exit_date"])
        f = f.dropna(subset=["exit_date"]).sort_values("exit_date")
        if f.empty:
            continue
        pnl = f.proceeds - f.cost
        ret = (f.proceeds / f.cost - 1) * 100
        risk = f.qty * (f.entry - f.stop)
        gross = f.qty * (f.exit - f.entry)
        costs = (gross - pnl).sum()
        gross_sum = gross.sum()
        win, loss = ret[ret > 0], ret[ret <= 0]
        yrs = (pd.Timestamp(f.exit_date.max()) - pd.Timestamp(c["period"]["start"])).days / 365.25
        rows.append({
            "id": IDS.get(c["name"], ""), "sid": ids.short(IDS[c["name"]]) if c["name"] in IDS else "",
            "risk": z["risk_pct"], "slots": z["max_positions"],
            "sizing": ", ".join(k for k in ("dd_rule", "risk_rules", "max_stop_pct") if z.get(k)) or "fixed",
            "family": run.parts[-3], "variant": run.parts[-2], "universe": run.parts[-1].upper(), "exit": ex,
            "mkt": f"NIFTY > {c['entry']['day_filters']['market_sma']}-DMA"
                   if "market_sma" in c.get("entry", {}).get("day_filters", {}) else "none",
            "win": (ret > 0).mean() * 100,
            "avg_ret": ret.mean(), "avg_rs": pnl.mean(),
            "avg_win": win.mean() if len(win) else np.nan, "avg_loss": loss.mean() if len(loss) else np.nan,
            "payoff": win.mean() / -loss.mean() if len(win) and len(loss) else np.nan,
            "exp_r": (pnl / risk).mean(),
            "cagr": s["CAGR %"], "mdd": s["Max DD %"], "mar": s["CAGR %"] / -s["Max DD %"],
            "trades": len(f), "tpy": len(f) / yrs,
            "streak": streak(list(pnl <= 0)),
            "hold": float(s["Median hold days"]), "deployed": s["Avg deployed %"],
            "skipped": int(s["Signals skipped"]),
            "cost_pct": costs / gross_sum * 100 if gross_sum > 0 else np.inf,
            "pdf": REPO + (run / "report.pdf").relative_to(ROOT).as_posix(),
            "desc": c.get("description", ""),
        })

COLS = [  # key, header, format, tooltip
    ("sid", "ID", None, "Permanent strategy ID (short form). Hover for the full ID"),
    ("strategy", "Strategy", None, "Strategy family / variant"),
    ("universe", "Universe", None, "Stocks traded (today's index members)"),
    ("exit", "Exit", None, "Fixed target, or no target (trend exit)"),
    ("risk", "Risk %", "{:g}", "Risk per trade, % of starting capital"),
    ("slots", "Slots", "{:d}", "Maximum open trades"),
    ("mkt", "Market filter", None, "New entries only when NIFTY 50 is above its 200-day average"),
    ("win", "Win %", "{:.0f}", "Share of closed trades that made money after costs"),
    ("avg_ret", "Avg trade %", "{:+.1f}", "Average net return per trade"),
    ("avg_rs", "Avg trade ₹", "{:+,.0f}", "Average net rupee profit per trade"),
    ("avg_win", "Avg win %", "{:+.1f}", "Average net return of winning trades"),
    ("avg_loss", "Avg loss %", "{:+.1f}", "Average net return of losing trades"),
    ("payoff", "Payoff", "{:.2f}", "Average win ÷ average loss"),
    ("exp_r", "Expectancy R", "{:+.2f}", "Average net profit per rupee risked (1R = planned loss to the stop)"),
    ("cagr", "CAGR %", "{:.1f}", "Compound annual growth of the account"),
    ("mdd", "Max DD %", "{:.0f}", "Largest fall from an equity peak"),
    ("mar", "CAGR / DD", "{:.2f}", "CAGR divided by max drawdown: return per unit of pain"),
    ("trades", "Trades", "{:,}", "Closed trades"),
    ("tpy", "Trades / yr", "{:.0f}", "Closed trades per year"),
    ("streak", "Max losing streak", "{:d}", "Most consecutive losing trades (by exit date)"),
    ("hold", "Median days", "{:.0f}", "Median holding period in calendar days"),
    ("deployed", "Deployed %", "{:.0f}", "Average share of equity in open positions"),
    ("skipped", "Skipped", "{:,}", "Signals not taken because all slots were full, cash ran out or a sizing rule paused entries"),
    ("cost_pct", "Costs % of gross", "{:.0f}", "Fees + slippage as a share of profit before costs"),
    ("pdf", "Report", None, "Full PDF report"),
]


GLOSSARY = {
    "ID": "Permanent strategy ID: 'S' + a UUIDv7, shown by its last 8 characters (hover for the full ID). It never "
          "changes when a strategy is renamed or edited, and is never reused. Full list: strategies/registry.csv.",
    "Strategy": "The setup tested (family) and the variant of its rules. Hover over a name for the full rules.",
    "Universe": "The stocks the strategy could trade: today's NIFTY 500 or NIFTY 50 members.",
    "Exit": "How winners are closed. 'Target X%' sells when price rises X% above entry. 'No target' holds until the "
            "trend exit (a close below EMA61 on the signal timeframe) or the stop. Every trade also has a stop loss.",
    "Risk %": "Rupees risked per trade (entry minus stop, times quantity) as a % of starting capital. Most runs use 1%.",
    "Slots": "Maximum number of open trades at once. Most runs use 8.",
    "Market filter": "'NIFTY > 200-DMA' means no new trades are opened while NIFTY 50 closed below its 200-day "
                     "simple moving average the day before (BSE Sensex is used before mid-2008, when NIFTY data "
                     "starts). Open trades are not sold by the filter. 'none' means no market filter.",
    "Win %": "Share of closed trades that made money after fees and slippage. A high win rate alone means little: "
             "read it together with Avg win %, Avg loss % and Payoff.",
    "Avg trade %": "Average net return per closed trade, on the money put into that trade.",
    "Avg trade ₹": "Average net profit or loss per closed trade in rupees. Unlike the %, it reflects position size.",
    "Avg win %": "Average net return of the winning trades only.",
    "Avg loss %": "Average net return of the losing trades only. Usually close to the stop distance plus costs.",
    "Payoff": "Average win divided by average loss. A payoff of 3 means the typical winner is three times the "
              "typical loser. Low win rates need high payoffs to make money.",
    "Expectancy R": "Average net profit per rupee risked. 1R is the planned loss if the stop is hit (about ₹1,000 here). "
                    "+0.5R means each trade earns half of what it risks on average; below 0 the strategy loses money.",
    "CAGR %": "Compound annual growth rate: the steady yearly return that would turn ₹1 lakh into the final equity.",
    "Max DD %": "Maximum drawdown: the largest fall from an equity peak to a later low. The pain you must sit through.",
    "CAGR / DD": "CAGR divided by the size of the max drawdown. Return per unit of pain; higher is better. "
                 "Useful for ranking strategies with different risk.",
    "Trades": "Number of closed trades. Fewer than about 100 means the result rests on a small sample.",
    "Trades / yr": "Closed trades per year: how busy the strategy keeps you, and how often you pay costs.",
    "Max losing streak": "Most losing trades in a row (ordered by exit date). Expect a streak at least this long again.",
    "Median days": "Median holding period in calendar days. Under 365 days, gains are taxed as short-term (20%); "
                   "over 365 days as long-term (12.5%). Tax is not deducted in these results.",
    "Deployed %": "Average share of the account held in open positions. The rest sits idle as cash.",
    "Skipped": "Signals not taken because all 8 slots were full or cash ran out. Many skips mean the result depends "
               "on which signals got the slots (here: tightest stop first).",
    "Costs % of gross": "Fees and slippage as a share of profit before costs. Above 100% (or '>100') means the "
                        "strategy would make money before costs but loses after them.",
    "Report": "Link to the full PDF report: rules, equity and drawdown charts, and all results for that strategy.",
}


def cell(r, k, fmt):
    v = r.get(k)
    if k == "strategy":
        return f'<td title="{html.escape(r["desc"])}">{r["family"]}<br><span class="v">{r["variant"]}</span></td>', f'{r["family"]}/{r["variant"]}'
    if k == "sid":
        return f'<td class="id" title="{r["id"]}"><code>{v}</code></td>', str(v)
    if k == "pdf":
        return f'<td><a href="{v}">PDF</a></td>', ""
    if fmt is None:
        return f"<td>{html.escape(str(v))}</td>", str(v)
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return '<td class="n">–</td>', "-1e18"
    if v == np.inf:
        return '<td class="n bad">&gt;100</td>', "1e18"
    cls = "n"
    if k in ("mdd",) and v <= -40 or k in ("cagr", "avg_ret", "exp_r", "avg_rs") and v < 0 \
            or k == "cost_pct" and v >= 50:
        cls += " bad"
    if k == "cagr" and v >= 8 or k == "mar" and v >= 0.2:
        cls += " good"
    return f'<td class="{cls}" data-v="{v}">{fmt.format(v)}</td>', str(v)


body = []
for r in sorted(rows, key=lambda r: -r["cagr"]):
    tds = []
    for k, _, fmt, _ in COLS:
        td, _ = cell(r, k, fmt)
        tds.append(td)
    body.append(f'<tr data-family="{r["family"]}" data-mkt="{html.escape(r["mkt"])}">' + "".join(tds) + "</tr>")
families = sorted({r["family"] for r in rows})
head = "".join(f'<th title="{html.escape(t)}" data-num="{0 if f is None else 1}">{h}</th>' for _, h, f, t in COLS)
opts = "".join(f'<option value="{f}">{f}</option>' for f in families)

STUDY_TITLES = {"slot_ranking": "Slot ranking: which signals should fill the 8 slots",
                "cagr18": "CAGR 18%: capital use, exits, selection, regime, rotation",
                "pit": "NIFTY 500 point in time: survivorship bias measured",
                "longshort": "Long/short: hardened Sa15d9d9c, short books, NIFTY hedge",
                "market_filter": "NIFTY 200-day market filter on every strategy",
                "market_tighten": "Tightening stops / exiting when NIFTY is below its 200-day average",
                "overnight": "Overnight study: robustness, sizing, high win-rate fixes, new indicators",
                "signal_rank": "Ranking signals with MACD and candlestick patterns",
                "stochrsi_macd": "MACD with the StochRSI pullback: monthly gate, weekly gate, ranking"}
studies = "".join(f'<li><a href="{REPO}{p.relative_to(ROOT).as_posix()}">'
                  f'{STUDY_TITLES.get(p.parent.name, p.parent.name)}</a></li>'
                  for p in sorted(ROOT.glob("results/studies/*/report.pdf")))
gloss = "".join(f"<dt>{h}</dt><dd>{html.escape(GLOSSARY[h])}</dd>" for _, h, _, _ in COLS)

page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Strategy Scoreboard</title>
<style>
:root{{--bg:#fff;--fg:#0f172a;--mut:#64748b;--line:#e2e8f0;--alt:#f8fafc;--head:#0f172a;--headfg:#fff;--bad:#dc2626;--good:#15803d;--link:#2563eb}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#0b1120;--fg:#e2e8f0;--mut:#94a3b8;--line:#1e293b;--alt:#111827;--head:#1e293b;--headfg:#e2e8f0;--bad:#f87171;--good:#4ade80;--link:#60a5fa}}}}
:root[data-theme="dark"]{{--bg:#0b1120;--fg:#e2e8f0;--mut:#94a3b8;--line:#1e293b;--alt:#111827;--head:#1e293b;--headfg:#e2e8f0;--bad:#f87171;--good:#4ade80;--link:#60a5fa}}
body{{margin:0;background:var(--bg);color:var(--fg);font:14px/1.5 system-ui,-apple-system,Segoe UI,sans-serif}}
main{{max-width:1600px;margin:0 auto;padding:24px 16px}}
h1{{font-size:22px;margin:0 0 4px}} p{{margin:4px 0;color:var(--mut)}} a{{color:var(--link)}}
.bar{{display:flex;gap:12px;align-items:center;margin:16px 0 8px;flex-wrap:wrap}}
select{{font:inherit;padding:4px 8px;background:var(--bg);color:var(--fg);border:1px solid var(--line);border-radius:6px}}
.wrap{{overflow-x:auto;border:1px solid var(--line);border-radius:8px}}
table{{border-collapse:collapse;width:100%;font-size:12.5px;white-space:nowrap}}
th{{position:sticky;top:0;background:var(--head);color:var(--headfg);padding:8px;text-align:right;cursor:pointer;user-select:none;font-weight:600}}
th:nth-child(-n+3){{text-align:left}} th.s::after{{content:" ▾"}} th.s.asc::after{{content:" ▴"}}
td{{padding:6px 8px;border-top:1px solid var(--line)}} td.n{{text-align:right;font-variant-numeric:tabular-nums}}
tr:nth-child(even) td{{background:var(--alt)}} .v{{color:var(--mut);font-size:11.5px}}
.bad{{color:var(--bad)}} .good{{color:var(--good);font-weight:600}}
h2{{font-size:17px;margin:24px 0 8px}}
.gloss{{display:grid;grid-template-columns:max-content 1fr;gap:6px 16px;font-size:13px;margin:0}}
.gloss dt{{font-weight:600}} .gloss dd{{margin:0;color:var(--mut)}}
@media (max-width:600px){{.gloss{{grid-template-columns:1fr}} .gloss dd{{margin-bottom:6px}}}}
.notes{{margin-top:16px;font-size:12.5px;color:var(--mut)}} .notes li{{margin:2px 0}}
</style></head><body><main>
<h1>Strategy scoreboard</h1>
<p>Every backtest (most at <b>1% risk per trade, 8 slots</b>; see the Risk and Slots columns), ₹1,00,000 starting capital, from 2000. Click a header to sort; hover a header for its meaning.</p>
<div class="bar"><label>Strategy <select id="fam"><option value="">All</option>{opts}</select></label>
<label>Market filter <select id="mkt"><option value="">All</option><option>none</option><option>NIFTY &gt; 200-DMA</option></select></label>
<span id="count" class="v"></span></div>
<div class="wrap"><table id="t"><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>
<ul class="notes">
<li>Prices are actual traded prices (adjusted for splits and bonuses, not dividends); dividend income is not counted.</li>
<li>Universe is <b>today's</b> index members, so results carry survivorship bias and are optimistic.</li>
<li>Costs: Sharekhan delivery fees (~0.47% per side) plus 0.1% slippage per side. Risk is 1% of <i>starting</i> capital, so positions do not grow with the account.</li>
<li>Gaps fill at the open; stop is checked before target on the same day. Tax is not deducted.</li>
<li>Red: negative return, drawdown worse than 40%, or costs over half the gross profit. Green: CAGR ≥ 8% or CAGR/DD ≥ 0.2.</li>
<li>Research and education only, not investment advice. Generated {date.today():%d %b %Y} by <code>site.py</code>.</li>
</ul>
<h2>Studies</h2>
<ul class="notes">{studies}</ul>
<h2>Glossary</h2>
<dl class="gloss">{gloss}</dl>
</main>
<script>
const t=document.getElementById('t'),tb=t.tBodies[0],fam=document.getElementById('fam'),cnt=document.getElementById('count');
function count(){{const n=[...tb.rows].filter(r=>r.style.display!=='none').length;cnt.textContent=n+' rows';}}
const mkt=document.getElementById('mkt');
function filt(){{[...tb.rows].forEach(r=>r.style.display=(!fam.value||r.dataset.family===fam.value)&&(!mkt.value||r.dataset.mkt===mkt.value)?'':'none');count();}}
fam.onchange=filt;mkt.onchange=filt;
[...t.tHead.rows[0].cells].forEach((th,i)=>th.onclick=()=>{{
  const num=th.dataset.num==='1',asc=th.classList.contains('s')&&!th.classList.contains('asc');
  [...t.tHead.rows[0].cells].forEach(h=>h.classList.remove('s','asc'));th.classList.add('s');if(asc)th.classList.add('asc');
  const key=r=>{{const c=r.cells[i];return num?parseFloat(c.dataset.v??'-1e18'):c.textContent;}};
  [...tb.rows].sort((a,b)=>{{const x=key(a),y=key(b);const d=num?x-y:String(x).localeCompare(y);return asc?d:-d;}}).forEach(r=>tb.appendChild(r));
}});
count();
</script></body></html>
"""
(ROOT / "docs").mkdir(exist_ok=True)
(ROOT / "docs" / "index.html").write_text(page, encoding="utf-8")
print(f"docs/index.html: {len(rows)} rows")
