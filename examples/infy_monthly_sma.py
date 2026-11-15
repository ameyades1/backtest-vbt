"""SMA crossover on INFY using monthly candles.

    python examples/infy_monthly_sma.py --fast 10 --slow 20
"""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import vectorbt as vbt
from lib import data, plotting
from lib.costs import FEES, SLIPPAGE

p = argparse.ArgumentParser()
p.add_argument("--symbol", default="INFY.NS")
p.add_argument("--fast", type=int, default=10, help="fast SMA in months")
p.add_argument("--slow", type=int, default=20, help="slow SMA in months")
a = p.parse_args()

# 1. Daily OHLCV from cache -> monthly candles (labelled by month start)
daily = data.ohlcv_for(a.symbol)
monthly = daily.resample("MS").agg(
    {"Open": "first", "High": "max", "Low": "min", "Close": "last", "Volume": "sum"}
).dropna()

# 2. Signals: fast SMA crosses above/below slow SMA (evaluated on month close)
close = monthly["Close"]
fast = vbt.MA.run(close, a.fast)
slow = vbt.MA.run(close, a.slow)
entries = fast.ma_crossed_above(slow)
exits = fast.ma_crossed_below(slow)

# 3. Backtest: trade at the month's close, Indian delivery costs
pf = vbt.Portfolio.from_signals(close, entries, exits, init_cash=100_000,
                                fees=FEES, slippage=SLIPPAGE, freq="30D")
bh = vbt.Portfolio.from_holding(close, init_cash=100_000, fees=FEES, freq="30D")

print(f"{a.symbol} monthly SMA {a.fast}/{a.slow}  ({close.index[0]:%b %Y} – {close.index[-1]:%b %Y})")
print(pf.stats()[["Total Return [%]", "Max Drawdown [%]", "Total Trades",
                  "Win Rate [%]", "Sharpe Ratio"]].to_string())
print(f"Buy & hold return [%]  {bh.total_return() * 100:.1f}")
print("\nTrades:")
print(pf.trades.records_readable[["Entry Timestamp", "Avg Entry Price",
                                   "Exit Timestamp", "Avg Exit Price", "Return"]].to_string(index=False))

# 4. Monthly candlestick chart: SMA lines on price, RSI and MACD panels below
rsi = vbt.RSI.run(close, 14).rsi
macd = vbt.MACD.run(close, 12, 26, 9)
fig = plotting.candles(
    monthly, f"{a.symbol} – monthly SMA {a.fast}/{a.slow}", entries, exits,
    overlays={f"SMA {a.fast}": fast.ma, f"SMA {a.slow}": slow.ma},
    panels={"RSI 14": {"RSI": rsi},
            "MACD 12/26/9": {"MACD": macd.macd, "Signal": macd.signal, "Hist": ("bar", macd.hist)}},
    guides={"RSI 14": [30, 70], "MACD 12/26/9": [0]},
)
path = plotting.save_html(fig, f"{a.symbol}_monthly_sma{a.fast}_{a.slow}")
print(f"\nChart: {path}")
