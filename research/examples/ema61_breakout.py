"""EMA61 breakout on NIFTY 50 stocks with Sharekhan-style trailing stop-loss.

    python examples/ema61_breakout.py                     # monthly, trails 5..30% + baseline
    python examples/ema61_breakout.py --tf W --trails 5 10 15
    python examples/ema61_breakout.py --plot INFY.NS --trail 15
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import numpy as np
import pandas as pd
from lib import data, indices, plotting, ema61
from lib.costs import FEES, SLIPPAGE

p = argparse.ArgumentParser()
p.add_argument("--index", default="NIFTY50")
p.add_argument("--tf", default="M", choices=["D", "W", "M"])
p.add_argument("--trails", nargs="*", type=float, default=[5, 8, 10, 12, 15, 20, 25, 30])
p.add_argument("--targets", nargs="*", type=float,
               help="fixed targets in %% with stop at breakout candle low (replaces TSL runs)")
p.add_argument("--valid", type=int, default=1, help="bars the buy-stop stays valid")
p.add_argument("--start", default="2000-01-01")
p.add_argument("--plot")
p.add_argument("--trail", type=float, default=15, help="trail %% for --plot")
a = p.parse_args()

syms = [s for s in indices.symbols(a.index) if s in data.cached_symbols()]
dailies = {s: data.ohlcv_for(s) for s in syms}
dailies = {s: d for s, d in dailies.items() if len(d)}


def run(trail, target=None, stop_low=False):
    eqs, rets, trades = [], [], []
    for s, d in dailies.items():
        t = ema61.simulate(d, s, a.tf, trail_pct=None if trail is None else trail / 100,
                           valid_bars=a.valid, stop_at_low=stop_low,
                           target_pct=None if target is None else target / 100)
        eq, r = ema61.equity(t, d, FEES, SLIPPAGE)
        eqs.append(eq.rename(s)); rets += r; trades += t
    port = pd.concat(eqs, axis=1, sort=True).ffill()
    port = port[port.index >= a.start]
    port = port.bfill().sum(axis=1)          # ₹1L per stock, idle cash before listing
    span = sum((d.index[-1] - max(d.index[0], pd.Timestamp(a.start))).days for d in dailies.values())
    trades = [t for t in trades if t.entry_date >= pd.Timestamp(a.start)]
    st = ema61.stats(port, rets, trades, span)
    if stop_low:
        reasons = pd.Series([t.reason.split("-")[0] for t in trades])
        st["Target hit %"] = (reasons == "target").mean() * 100
        st["Stopped %"] = (reasons == "stop").mean() * 100
        st["Avg stop dist %"] = np.mean([(t.entry - (t.stop or t.entry)) / t.entry * 100 for t in trades])
    return st, trades, port


rows, all_trades = {}, {}
if a.targets:
    rows["No target (stop + close<EMA61)"], _, _ = run(None, None, True)
    for tg in a.targets:
        rows[f"Target {tg:g}%"], all_trades[tg], _ = run(None, tg, True)
else:
    for tr in [None] + a.trails:
        label = "No TSL (close<EMA61)" if tr is None else f"TSL {tr:g}%"
        rows[label], all_trades[label], _ = run(tr)
tab = pd.DataFrame(rows).T
tab.to_csv(f"data/ema61_{a.index}_{a.tf}_{'targets' if a.targets else 'tsl'}.csv")
print(f"{a.index}: {len(dailies)} stocks | EMA61 breakout on {dict(D='daily', W='weekly', M='monthly')[a.tf]} "
      f"| from {a.start} | Sharekhan fees {FEES:.3%}/side + slippage {SLIPPAGE:.2%}/side\n")
print(tab.to_string(float_format=lambda x: f"{x:,.1f}"))

if a.plot:
    d = dailies[a.plot]
    t = ema61.simulate(d, a.plot, a.tf, trail_pct=a.trail / 100, valid_bars=a.valid)
    bars, ema, brk = ema61.signals(d, a.tf)
    ent = pd.Series(False, index=bars.index); ex = ent.copy()
    for x in t:
        ent[bars.index[bars.index.searchsorted(x.entry_date)]] = True
        if x.exit_date is not None:
            ex[bars.index[bars.index.searchsorted(x.exit_date)]] = True
    fig = plotting.candles(bars, f"{a.plot} – EMA61 breakout, TSL {a.trail:g}% ({a.tf})",
                           ent, ex, overlays={"EMA 61": ema})
    fig.update_xaxes(rangebreaks=[]) if a.tf != "D" else None
    print("\nTrades:")
    print(pd.DataFrame([vars(x) for x in t]).drop(columns="symbol").to_string(index=False))
    print(f"Chart: {plotting.save_html(fig, f'{a.plot}_ema61_{a.tf}_tsl{a.trail:g}')}")
