"""Build docs/index.html: one sortable table of every 1% risk / 8 slot run in results/.

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

ROOT = Path(__file__).resolve().parent
REPO = "https://github.com/ameyades1/backtest-vbt/blob/main/"


def streak(losses):
    best = cur = 0
    for x in losses:
        cur = cur + 1 if x else 0
        best = max(best, cur)
    return best


rows = []
for cfgp in sorted(ROOT.glob("results/*/*/*/config.json")):
    run = cfgp.parent
    c = json.load(open(cfgp))
    z = c["sizing"]
    if z["risk_pct"] != 1.0 or z["max_positions"] != 8:
        continue
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
            "family": run.parts[-3], "variant": run.parts[-2], "universe": run.parts[-1].upper(), "exit": ex,
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
    ("strategy", "Strategy", None, "Strategy family / variant"),
    ("universe", "Universe", None, "Stocks traded (today's index members)"),
    ("exit", "Exit", None, "Fixed target, or no target (trend exit)"),
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
    ("skipped", "Skipped", "{:,}", "Signals not taken because all 8 slots were full or cash ran out"),
    ("cost_pct", "Costs % of gross", "{:.0f}", "Fees + slippage as a share of profit before costs"),
    ("pdf", "Report", None, "Full PDF report"),
]


def cell(r, k, fmt):
    v = r.get(k)
    if k == "strategy":
        return f'<td title="{html.escape(r["desc"])}">{r["family"]}<br><span class="v">{r["variant"]}</span></td>', f'{r["family"]}/{r["variant"]}'
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
    body.append(f'<tr data-family="{r["family"]}">' + "".join(tds) + "</tr>")
families = sorted({r["family"] for r in rows})
head = "".join(f'<th title="{html.escape(t)}" data-num="{0 if f is None else 1}">{h}</th>' for _, h, f, t in COLS)
opts = "".join(f'<option value="{f}">{f}</option>' for f in families)

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
.notes{{margin-top:16px;font-size:12.5px;color:var(--mut)}} .notes li{{margin:2px 0}}
</style></head><body><main>
<h1>Strategy scoreboard</h1>
<p>Every backtest at <b>1% risk per trade, 8 slots</b>, ₹1,00,000 starting capital, from 2000. Click a header to sort; hover a header for its meaning.</p>
<div class="bar"><label>Strategy <select id="fam"><option value="">All</option>{opts}</select></label>
<span id="count" class="v"></span></div>
<div class="wrap"><table id="t"><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>
<ul class="notes">
<li>Prices are actual traded prices (adjusted for splits and bonuses, not dividends); dividend income is not counted.</li>
<li>Universe is <b>today's</b> index members, so results carry survivorship bias and are optimistic.</li>
<li>Costs: Sharekhan delivery fees (~0.47% per side) plus 0.1% slippage per side. Risk is 1% of <i>starting</i> capital, so positions do not grow with the account.</li>
<li>Gaps fill at the open; stop is checked before target on the same day. Tax is not deducted.</li>
<li>Red: negative return, drawdown worse than 40%, or costs over half the gross profit. Green: CAGR ≥ 8% or CAGR/DD ≥ 0.2.</li>
<li>Research and education only, not investment advice. Generated {date.today():%d %b %Y} by <code>site.py</code>.</li>
</ul></main>
<script>
const t=document.getElementById('t'),tb=t.tBodies[0],fam=document.getElementById('fam'),cnt=document.getElementById('count');
function count(){{const n=[...tb.rows].filter(r=>r.style.display!=='none').length;cnt.textContent=n+' rows';}}
fam.onchange=()=>{{[...tb.rows].forEach(r=>r.style.display=!fam.value||r.dataset.family===fam.value?'':'none');count();}};
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
