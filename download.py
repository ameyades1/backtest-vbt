"""Fetch constituents + max-history daily OHLCV from Yahoo -> data/ohlcv.parquet (merged cache).

    python download.py --list                       # show available indices
    python download.py                              # NIFTY500 (default)
    python download.py --index BANK IT AUTO         # specific indices
    python download.py --index sectoral             # a whole group: broad | sectoral | thematic | all
    python download.py --index all --skip-cached    # only symbols not already cached
    python download.py --symbols RELIANCE.NS ^NSEI  # arbitrary Yahoo symbols
"""
import argparse
from lib import indices, data

p = argparse.ArgumentParser()
p.add_argument("--index", nargs="*", default=["NIFTY500"])
p.add_argument("--symbols", nargs="*")
p.add_argument("--start", default="1990-01-01")
p.add_argument("--refresh-list", action="store_true", help="re-fetch NSE constituent lists")
p.add_argument("--skip-cached", action="store_true")
p.add_argument("--list", action="store_true")
a = p.parse_args()

if a.list:
    print(indices.table().to_string()); raise SystemExit

if a.symbols:
    symbols = a.symbols
else:
    keys = indices.resolve(a.index)
    symbols = []
    for k in keys:
        mem = indices.symbols(k, a.refresh_list)
        y = indices.INDICES[k]["yahoo"]
        print(f"{k:14} {len(mem):4} constituents  index series: {y or 'not on Yahoo'}")
        symbols += mem + ([y] if y else [])
    symbols = list(dict.fromkeys(symbols))

if a.skip_cached:
    symbols = [s for s in symbols if s not in data.cached_symbols()]
if not symbols:
    print("Nothing to download."); raise SystemExit

df = data.clean(data.download(symbols, start=a.start))
data.save(df)
firsts = df.reset_index().groupby("Symbol")["Date"].min()
print(f"\nSaved {len(df):,} rows for {df['Symbol'].nunique()} symbols -> {data.OHLCV_PATH}")
print(f"Missing: {sorted(set(symbols) - set(df['Symbol']))}")
print(f"Earliest start: {firsts.min().date()}  median start: {firsts.median().date()}")
