"""Fetch NIFTY 500 list + max-history daily OHLCV from Yahoo -> data/ohlcv.parquet

    python download.py                 # full download (~5-10 min)
    python download.py --refresh-list  # also re-fetch constituent list
    python download.py --symbols RELIANCE.NS TCS.NS ^NSEI
"""
import argparse
from lib import universe, data

p = argparse.ArgumentParser()
p.add_argument("--refresh-list", action="store_true")
p.add_argument("--symbols", nargs="*")
p.add_argument("--start", default="1990-01-01")
a = p.parse_args()

symbols = a.symbols or universe.yahoo_symbols(a.refresh_list) + ["^NSEI"]
raw = data.download(symbols, start=a.start)
df = data.clean(raw)
data.save(df)

firsts = df.reset_index().groupby("Symbol")["Date"].min()
print(f"\nSaved {len(df):,} rows, {df['Symbol'].nunique()} symbols -> {data.OHLCV_PATH}")
print(f"Missing: {sorted(set(symbols) - set(df['Symbol']))}")
print(f"Earliest start: {firsts.min().date()}  median start: {firsts.median().date()}")
