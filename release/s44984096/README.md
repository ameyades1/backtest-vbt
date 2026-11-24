# S44984096: release version

The strategy you trade, and nothing else. It is a standalone copy, written only for these rules, with no options and no research code. It reads the shared price cache `data/ohlcv.parquet` and the NIFTY 500 lists in `data/constituents/`.

| File | What it is |
|---|---|
| `rules.py` | **Every rule on one page**: setup, filters, market filter, entry, stop, exits, sizing, drawdown rule, costs |
| `indicators.py` | RSI, Stochastic RSI, EMA, SMA, ATR and Supertrend; nothing else |
| `data.py` | Price cache, point-in-time NIFTY 500 membership, NSE holidays, the Yahoo download and fixes |
| `backtest.py` | Day-by-day portfolio loop from July 2006 → `out/trades.csv`, `out/equity.csv` |
| `live.py` | Daily to-do list after the close, using the same `rules.py` functions |
| `tests/run_tests.py` | Golden trades plus rule tests |

```
python release/s44984096/backtest.py
python release/s44984096/tests/run_tests.py
python release/s44984096/live.py report --refresh
```

## Checked against research
On 24 Nov 2026 the release backtest reproduced the research engine (`research/run_strategy.py` with `research/strategies/stexit/A_flip_capentry.json`) fill for fill:
- 467 of 467 fills identical;
- equity difference ₹0.00;
- CAGR 15.3%, max drawdown −23.5%, 403 trades, 21.2% of closed trades won.

The trades closed by 31 Oct 2026 are frozen in `tests/golden_trades.csv`.

## How a change gets in
1. Test the idea in `research/`.
2. If adopted, change `rules.py` here.
3. Rerun the tests. The golden test will fail.
4. Check that every changed trade is explained by the rule change.
5. Regenerate `tests/golden_trades.csv` in the same commit, with the reason in the commit message.

## Live behaviour beyond the backtest
- **Stop armed from the next session.** On the fill day only the close counts, the same as the backtest.
- **Splits and bonuses.** Detected because Yahoo's history no longer matches the entry-day close recorded at the buy. Entry, stop and quantity are adjusted by the ratio, and the output says to re-place the stop.
- **Demergers.** An overnight gap of more than 30% since the last report (and after entry) is flagged for your decision.
- **BE series.** A buy-stop on a BE-series stock carries a warning.
- **Chartink.** On a month end that isn't a Friday, the output reminds you to use the "1 week ago" weekly filters in Chartink, or this list.
- **Thursday month end before a Friday holiday.** The weekly filter uses the last full Friday week, as in the backtest (11 such month ends since 2006; using the just-finished week instead changed 1 of 403 trades). Follow this list, not Chartink, on those days.
- **Holidays.** If next year's NSE holiday list is missing from `data.py`, you get a warning.
