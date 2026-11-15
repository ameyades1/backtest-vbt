"""Backtest a strategy on index constituents, or on the index series themselves.

    python run.py --index NIFTY500 --strategy sma --plot RELIANCE.NS
    python run.py --index BANK IT --strategy donchian --start 2010-01-01
    python run.py --on-index sectoral --plot BANK      # strategy on each sector index
"""
import argparse, subprocess, shutil
import pandas as pd
from lib import data, indices, strategies, backtest, plotting

p = argparse.ArgumentParser()
p.add_argument("--index", nargs="*", default=["NIFTY500"], help="universe = constituents of these")
p.add_argument("--on-index", nargs="*", help="trade the index series instead of stocks")
p.add_argument("--strategy", choices=["sma", "donchian"], default="sma")
p.add_argument("--fast", type=int, default=50)
p.add_argument("--slow", type=int, default=200)
p.add_argument("--start")
p.add_argument("--plot", help="symbol (e.g. RELIANCE.NS) or index key with --on-index")
a = p.parse_args()

if a.on_index:
    series = {}
    for k in indices.resolve(a.on_index):
        try:
            series[k] = data.index_close(k)
        except ValueError as e:
            print(f"skip {k}: {e}")
    c = pd.DataFrame(series)
    if a.start:
        c = c[c.index >= a.start]
    hi = {k: data.ohlcv_for(indices.INDICES[k]["yahoo"])["High"] for k in c}
    lo = {k: data.ohlcv_for(indices.INDICES[k]["yahoo"])["Low"] for k in c}
    h, l = pd.DataFrame(hi).reindex(c.index), pd.DataFrame(lo).reindex(c.index)
    vol = None
else:
    universe = sorted({s for k in indices.resolve(a.index) for s in indices.symbols(k)})
    universe = [s for s in universe if s in data.cached_symbols()]
    if not universe:
        raise SystemExit("No cached data for that universe; run download.py --index ... first")
    d = data.load(universe, start=a.start)
    c, h, l, vol = d["Close"], d["High"], d["Low"], d["Volume"]

if a.strategy == "sma":
    entries, exits = strategies.sma_cross(c, a.fast, a.slow)
    entries.columns = exits.columns = c.columns
else:
    entries, exits = strategies.donchian_breakout(c, h, l)

pf = backtest.run(c, entries, exits, volume=vol)
s = backtest.summary(pf)
s.to_csv("data/summary.csv")
print(s.head(30).to_string(float_format=lambda x: f"{x:.3f}"))
print(f"\nUniverse {len(s)} | median CAGR {s['cagr'].median():.2%} | median Sharpe "
      f"{s['sharpe'].median():.2f} | with trades {(s['trades'] > 0).sum()}")

if a.plot:
    if a.on_index:
        o = data.ohlcv_for(indices.INDICES[a.plot]["yahoo"], a.start)
    else:
        o = data.ohlcv_for(a.plot, a.start)
    fig = plotting.candles(o, f"{a.plot} – {a.strategy}", entries[a.plot].reindex(o.index),
                           exits[a.plot].reindex(o.index))
    path = plotting.save_html(fig, f"{a.plot}_{a.strategy}")
    print(f"Chart: {path}")
    opener = shutil.which("wslview") or shutil.which("explorer.exe")
    if opener:
        win = subprocess.run(["wslpath", "-w", str(path)], capture_output=True, text=True).stdout.strip()
        subprocess.run([opener, win if "explorer" in opener else str(path)])
