# backtest-vbt

Backtesting NIFTY index constituents (NIFTY 500, broad, sectoral and thematic indices) and the index series themselves with [vectorbt](https://github.com/polakowo/vectorbt) on maximum available daily history from Yahoo Finance, with interactive candlestick charts.

The project combines both approaches: reusable code lives in `lib/` as plain Python, and `notebooks/` is for exploring and charting.

## Layout

```
lib/
  indices.py     registry of 31 NIFTY indices: NSE constituent list + Yahoo index ticker
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
python download.py --list                           # available indices and their Yahoo tickers
python download.py                                  # all NIFTY 500 stocks + index, max history (~10 min)
python download.py --index BANK IT AUTO             # specific indices
python download.py --index sectoral --skip-cached   # groups: broad | sectoral | thematic | all
python download.py --symbols RELIANCE.NS TCS.NS     # arbitrary Yahoo symbols

# backtest the constituents of one or more indices
python run.py --index NIFTY500 --strategy sma --fast 50 --slow 200 --plot RELIANCE.NS
python run.py --index BANK IT --strategy donchian --start 2010-01-01
# backtest the index series themselves
python run.py --on-index sectoral --plot BANK
```

Downloads merge into one cache (`data/ohlcv.parquet`), so you can add indices over time. Constituent lists are cached in `data/constituents/`; use `--refresh-list` to update them.

### Index series availability

Yahoo has no usable history for some index series: Next 50, Smallcap 100, Private Bank, Fin Services 25/50, Healthcare, Media, Consumer Durables, Oil & Gas, CPSE and Commodities. You can still backtest their *constituents*, but `--on-index` skips these indices. Most of the index series that are available start between 2005 and 2011. Run `python download.py --list` for the details.

```bash
```

`run.py` writes `data/summary.csv` and `charts/<SYMBOL>_<strategy>.html`, and opens the chart in the Windows browser (via `wslview` or `explorer.exe`).

For notebooks, open the folder in VS Code (`code .`) with the WSL and Jupyter extensions, then pick the **backtest (.venv)** kernel.

## Data notes and caveats

- **Source:** Yahoo Finance daily OHLCV, adjusted for splits, bonuses and dividends. `^NSEI` starts in 2007. Most large-cap stocks start around 1996–2002.
- **Survivorship bias:** the default universe is **NIFTY500_PIT**: historical NIFTY 500 membership rebuilt from NSE Indices' change notices (`lib/membership.py`, `data/constituents/NIFTY500_changes.csv`); a stock is tradeable only while it was in the index. Other universes (`--universe NIFTY50`, `MIDCAP150`, ...) use *today's* members and are optimistic. Members with no Yahoo price history (mostly delisted or merged companies) are still missing. Share of index members with prices on 1 July: 2000 13%, 2002 55%, 2003 61%, **2006 69%**, 2008 73%, 2010 75%, 2015 83%, 2020 96%, 2025 99%. The missing names are more often failures than winners, so results are somewhat optimistic, most of all in the early years.
- **Official period for S44984096: July 2006 onwards.** That is when the NIFTY 500 index (`^CRSLDX`) has a 200-day average, so the market filter uses NSE's own index with no Sensex/NIFTY 50 fallback, and price coverage is about 70% or more. Before 2006, coverage is too thin (the 2000 run was mostly cash) and the filter would need BSE data.
- **Cleaning:** removes non-positive prices, fixes inconsistent OHLC, and drops single-day ±40% spikes that reverse the next day.
- **Costs:** Sharekhan standard plan by default: delivery is about 0.47% per side (0.93% round trip) including STT, stamp duty, exchange, SEBI and GST, plus 0.1% slippage. A `discount` broker profile is also included. Run `python -m lib.costs` to see the table.
- **Per-stock backtests:** each symbol is backtested on its own. This is not a combined portfolio.
- Data and charts are git-ignored. Run `download.py` to rebuild them.

## Disclaimer

This is for research and education only. It is not investment advice.

## Strategy framework

Every strategy variant is a JSON file; one engine runs them all.

```
strategies/<family>/<variant>.json    rules: timeframe, setup, filters, entry, stop, exits, sizing, costs
lib/engine.py                         the trade engine (one open trade per stock, daily-bar fills)
lib/indicators.py                     resample, EMA, RSI, Stochastic RSI
lib/portfolio.py                      shared capital, fixed-risk sizing, max positions
run_strategy.py                       python run_strategy.py strategies/stochrsi_pullback/monthly_candle_stop.json [--universe NIFTY50]
report.py                             python report.py results/<family>/<variant>/<universe>
compare.py                            python compare.py  -> results/comparison.csv (all runs, one table)
site.py                               python site.py  -> docs/index.html (scoreboard of all 1%/8 runs, GitHub Pages)
studies/                              one-off studies (e.g. slot_ranking.py) -> results/studies/<name>/report.pdf
results/<family>/<variant>/<universe>/ config.json, summary.csv, report.pdf (committed); equity/fills (ignored)
tests/test_engine_parity.py           checks engine.py against the original engines (lib/legacy/)
reports/notes/                        one-off write-ups (trader profile)
```

### Strategy IDs

Every strategy has a permanent ID: `S` + a UUIDv7, stored as `"id"` in its JSON and listed in
`strategies/registry.csv` (id, short form, name, path, created, status). Reports and the scoreboard show the
short form, `S` + the last 8 hex digits (for example `S7c315ace`). The ID never changes when a strategy is
renamed or edited and is never reused; a removed strategy stays in the registry as `deleted`.

```
python -m lib.ids assign     give new configs an ID and update the registry
python -m lib.ids check      unique IDs, unique short forms, registry complete (run_strategy.py runs it too)
```

A new variant is a copy of a JSON file with the changed rule. Options are documented at the top of
`lib/engine.py`.
