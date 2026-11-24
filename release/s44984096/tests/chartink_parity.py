"""Chartink parity: does the Chartink screener give the same stocks as rules.py?  (needs internet)

    python release/s44984096/tests/chartink_parity.py            # month ends + latest day
    python release/s44984096/tests/chartink_parity.py --fridays  # also every Friday (expect noise, see below)

Chartink scan: https://chartink.com/screener/s44984096-screener. Its scan clause is stored below (CLAUSE); if you edit
the screen on Chartink, copy the new clause here (browser dev tools -> /screener/process request -> scan_clause).

What it compares, on Chartink's basis (month so far, current unfinished week, that day's close):
  - today's live Chartink result vs our list for the latest day in the cache;
  - Chartink's backtest history (about 160 trading days) vs our list on every month end in it.
Only month ends matter for trading. Chartink's history "repaints" monthly bars (its page says so): a past mid-month
date uses a monthly bar finished later, so Fridays differ by design and are shown only with --fridays.

Each difference is explained by the filter that decides it, with the margin. A difference within EDGE (relative gap
between the two sides of the deciding filter) is a tie that data or rounding can flip; anything wider is a FAIL.
Measured 24 Nov 2026: 8 month ends Apr-Nov 2026, 6 exact, 2 ties (HAL weekly close 0.02% below EMA, KIMS prior-month
%K 17.1 vs %D 17.0); exit code 0.
"""
import argparse, datetime as dt, sys, urllib.parse
from pathlib import Path
import pandas as pd
import requests

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import data, rules  # noqa: E402
from indicators import to_monthly, to_weekly, ema, rsi, stoch_rsi  # noqa: E402

URL = "https://chartink.com/screener/s44984096-screener"
EDGE = 0.01            # 1% relative gap = a tie
SR = "^916('src'=' monthly close',{d}'smoothk'='3','lengthrsi'='14','lengthstoch'='14','output'='{o}')^"
K_, D_ = SR.format(d="", o="val"), SR.format(d="'smoothd'='3',", o="signal")
CLAUSE = (f"( {{57960}} (  monthly {K_} >  monthly {D_} and  1 month ago {K_} <=  1 month ago {D_} and  "
          "monthly close >  monthly ema(  monthly close , 61 ) and  weekly close >  weekly ema(  weekly close , 61 ) and  "
          "daily close >  daily ema(  daily close , 61 ) and  monthly rsi( 14 ) >=  50 and  "
          f"monthly {D_} <  30 and  60 months ago close >  0 ) )")


def chartink():
    """(today's list, {date: list} from the backtest history)."""
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0"
    s.get(URL, timeout=30)
    h = {"x-xsrf-token": urllib.parse.unquote(s.cookies.get("XSRF-TOKEN", "")),
         "x-requested-with": "XMLHttpRequest", "referer": URL}
    now = s.post("https://chartink.com/screener/process", data={"scan_clause": CLAUSE}, headers=h, timeout=60).json()
    bt = s.post("https://chartink.com/backtest/process", data={"max_rows": 160, "scan_clause": CLAUSE},
                headers=h, timeout=60).json()
    ist = dt.timezone(dt.timedelta(hours=5, minutes=30))
    hist = {pd.Timestamp(dt.datetime.fromtimestamp(t / 1000, ist).date()): set(row[::3])
            for t, row in zip(bt["metaData"][0]["tradeTimes"], bt["aggregatedStockList"])}
    return {x["nsecode"] for x in now["data"]}, hist


def check(d, day):
    """Each filter on Chartink's basis for one stock up to `day`: name -> (left, right) with pass = left > right
    (or >= for RSI)."""
    d = d[:day]
    m = to_monthly(d)
    K, D = stoch_rsi(m["Close"], *rules.STOCH)
    w = to_weekly(d)
    return {"monthly %K > %D": (K.iloc[-1], D.iloc[-1]),
            "prior month %K <= %D": (D.iloc[-2], K.iloc[-2] - 1e-12),
            "monthly %D < 30": (rules.OVERSOLD, D.iloc[-1]),
            "monthly close > EMA61": (m["Close"].iloc[-1], ema(m["Close"], 61).iloc[-1]),
            "weekly close > EMA61": (w["Close"].iloc[-1], ema(w["Close"], 61).iloc[-1]),
            "daily close > EMA61": (d["Close"].iloc[-1], ema(d["Close"], 61).iloc[-1]),
            "monthly RSI >= 50": (rsi(m["Close"]).iloc[-1] + 1e-12, rules.RSI_MIN),
            "60 months of history": (len(m), 60)}


def ours(px, day):
    out = set()
    for s in data.members_on(day):
        d = px.get(s)
        if d is None or len(d[:day]) < 300 or d[:day].index[-1] != day:
            continue
        if all(a > b for a, b in check(d, day).values()):
            out.add(s.replace(".NS", ""))
    return out


def explain(px, sym, day):
    """(worst filter text, is it a tie?) for a stock on one side only."""
    d = px.get(sym + ".NS")
    if d is None:
        return "not in our price cache", False
    if sym + ".NS" not in data.members_on(day):
        return "not a NIFTY 500 member that day in our list", False
    c = check(d, day)
    failing = {k: v for k, v in c.items() if not v[0] > v[1]}
    near = failing or c                                    # on Chartink only: what fails for us; else the closest
    k, (a, b) = min(near.items(), key=lambda kv: abs(kv[1][0] - kv[1][1]) / max(abs(kv[1][1]), 1e-9))
    gap = abs(a - b) / max(abs(b), 1e-9)
    return f"{k}: {a:,.2f} vs {b:,.2f} ({gap * 100:.2f}%)", gap <= EDGE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fridays", action="store_true")
    a = ap.parse_args()
    now, hist = chartink()
    px = data.load([s for s in data.ever_members() if s in data.cached_symbols()])
    latest = max(d.index[-1] for d in px.values())
    days = sorted(hist)
    month_ends = [x for i, x in enumerate(days[:-1]) if days[i + 1].month != x.month]
    todo = [(x, hist[x], "month end") for x in month_ends]
    if a.fridays:
        todo += [(x, hist[x], "Friday (repaints)") for x in days if x.weekday() == 4 and x not in month_ends]
    todo.append((latest, now, "live today"))
    fails = ties = 0
    for day, ck, kind in sorted(todo, key=lambda t: t[0]):
        o = ours(px, day)
        diff = [(s, "Chartink only") for s in sorted(ck - o)] + [(s, "ours only") for s in sorted(o - ck)]
        print(f"{day:%a %d %b %Y}  {kind:18} Chartink {len(ck):2}  ours {len(o):2}  "
              + ("MATCH" if not diff else f"{len(diff)} different"))
        for s, side in diff:
            why, tie = explain(px, s, day)
            counted = kind != "Friday (repaints)"
            fails += counted and not tie
            ties += counted and tie
            print(f"    {s:12} {side:14} {'tie ' if tie else 'FAIL' if counted else '    '}  {why}")
    print(f"\n{len(month_ends)} month ends + today: {fails} real differences, {ties} ties (within {EDGE:.0%})")
    if latest.date() != max(days).date() and latest.date() != dt.date.today():
        print(f"note: cache ends {latest:%d %b}; run live.py report --refresh first for a fair 'today' comparison")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
