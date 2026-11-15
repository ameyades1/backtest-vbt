# backtest-vbt

Backtesting NIFTY 500 stocks with [vectorbt](https://github.com/polakowo/vectorbt) on maximum available daily history from Yahoo Finance, with interactive candlestick charts.

The project combines both approaches: reusable code lives in `lib/` as plain Python, and `notebooks/` is for exploring and charting.

## Layout

```
lib/
  universe.py    NIFTY 500 constituents (NSE CSV, cached)
  data.py        yfinance download → clean → data/ohlcv.parquet; load() → wide frames for vectorbt
  costs.py       Indian delivery costs (STT, exchange, SEBI, GST, stamp) + slippage
  strategies.py  sma_cross, donchian_breakout
  backtest.py    vectorbt portfolio with liquidity filter, summary table
  plotting.py    Plotly candlesticks + volume + buy/sell markers → HTML
download.py      fetch / refresh data
run.py           run a backtest across the universe, print a summary, chart a symbol
notebooks/explore.ipynb   interactive exploration, inline charts, parameter heatmap
```

## Setup (WSL / Linux)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m ipykernel install --user --name backtest --display-name "backtest (.venv)"
```

## Usage

```bash
python download.py                                  # all NIFTY 500 + ^NSEI, max history (~5–10 min)
python download.py --symbols RELIANCE.NS TCS.NS     # just a few symbols
python run.py --strategy sma --fast 50 --slow 200 --plot RELIANCE.NS
python run.py --strategy donchian --start 2005-01-01
```

`run.py` writes `data/summary.csv` and `charts/<SYMBOL>_<strategy>.html`, and opens the chart in the Windows browser (via `wslview` or `explorer.exe`).

For notebooks, open the folder in VS Code (`code .`) with the WSL and Jupyter extensions, then pick the **backtest (.venv)** kernel.

## Data notes and caveats

- **Source:** Yahoo Finance daily OHLCV, adjusted for splits, bonuses and dividends. `^NSEI` starts in 2007. Most large-cap stocks start around 1996–2002.
- **Survivorship bias:** the universe is *today's* NIFTY 500. Companies that were delisted or dropped from the index are missing, so results are optimistic.
- **Cleaning:** removes non-positive prices, fixes inconsistent OHLC, and drops single-day ±40% spikes that reverse the next day.
- **Costs:** about 0.11% per side for delivery plus 0.1% slippage (`lib/costs.py`). Check these against your broker.
- **Per-stock backtests:** each symbol is backtested on its own. This is not a combined portfolio.
- Data and charts are git-ignored. Run `download.py` to rebuild them.

## Disclaimer

This is for research and education only. It is not investment advice.
