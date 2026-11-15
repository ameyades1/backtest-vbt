"""Backtest a strategy across the cached universe and chart one symbol.

    python run.py --strategy sma --fast 50 --slow 200 --plot RELIANCE.NS
    python run.py --strategy donchian --start 2005-01-01
"""
import argparse, subprocess, shutil
from lib import data, strategies, backtest, plotting

p = argparse.ArgumentParser()
p.add_argument("--strategy", choices=["sma", "donchian"], default="sma")
p.add_argument("--fast", type=int, default=50)
p.add_argument("--slow", type=int, default=200)
p.add_argument("--start")
p.add_argument("--plot", help="symbol to chart, e.g. RELIANCE.NS")
a = p.parse_args()

d = data.load(start=a.start)
c = d["Close"]
if a.strategy == "sma":
    entries, exits = strategies.sma_cross(c, a.fast, a.slow)
    entries.columns = exits.columns = c.columns
else:
    entries, exits = strategies.donchian_breakout(c, d["High"], d["Low"])

pf = backtest.run(c, entries, exits, volume=d["Volume"])
s = backtest.summary(pf)
s.to_csv("data/summary.csv")
print(s.head(20).to_string(float_format=lambda x: f"{x:.3f}"))
print(f"\nMedian CAGR {s['cagr'].median():.2%} | median Sharpe {s['sharpe'].median():.2f} "
      f"| stocks with trades {(s['trades'] > 0).sum()}/{len(s)}")

if a.plot:
    o = data.ohlcv_for(a.plot, a.start)
    fig = plotting.candles(o, f"{a.plot} – {a.strategy}", entries[a.plot], exits[a.plot])
    path = plotting.save_html(fig, f"{a.plot}_{a.strategy}")
    print(f"Chart: {path}")
    opener = shutil.which("wslview") or shutil.which("explorer.exe")
    if opener:
        win = subprocess.run(["wslpath", "-w", str(path)], capture_output=True, text=True).stdout.strip()
        subprocess.run([opener, win if "explorer" in opener else str(path)])
