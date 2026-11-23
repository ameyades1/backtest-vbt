"""Download, clean and cache OHLCV for the universe as one long-format parquet."""
from pathlib import Path
import numpy as np
import pandas as pd
import yfinance as yf

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OHLCV_PATH = DATA_DIR / "ohlcv.parquet"
FIELDS = ["Open", "High", "Low", "Close", "Volume"]


def download(symbols: list[str], start: str = "1990-01-01", chunk: int = 50) -> pd.DataFrame:
    """Return long df: index=Date, columns=[Symbol, Open, High, Low, Close, Volume].
    Prices are split/bonus adjusted but NOT dividend adjusted (auto_adjust=False, Yahoo 'Close'),
    i.e. the prices actually traded, as shown on NSE charts."""
    frames = []
    for i in range(0, len(symbols), chunk):
        batch = symbols[i : i + chunk]
        print(f"Downloading {i + 1}-{i + len(batch)} of {len(symbols)} ...")
        raw = yf.download(batch, start=start, auto_adjust=False, group_by="ticker",
                          progress=False, threads=True)
        for sym in batch:
            if sym not in raw.columns.get_level_values(0):
                continue
            df = raw[sym][FIELDS].dropna(how="all")
            if df.empty:
                continue
            df = df.assign(Symbol=sym)
            frames.append(df)
    out = pd.concat(frames)
    out.index.name = "Date"
    return _fill_last_close(out)


def _fill_last_close(out: pd.DataFrame, days: int = 7) -> pd.DataFrame:
    """Yahoo often publishes the latest daily candle with Open/High/Low/Volume but Close = NaN for a day or more
    (seen 23 Nov 2026), and such rows were dropped later, so the cache silently lagged a day. For rows in the last
    `days` days with a missing Close, take the close of that day's last hourly bar (same price NSE shows as the
    close to within the closing-auction difference) and widen High/Low to include it."""
    miss = out["Close"].isna() & out[["Open", "High", "Low"]].notna().all(axis=1) \
        & (out.index >= out.index.max() - pd.Timedelta(days=days))
    syms = sorted(out.loc[miss, "Symbol"].unique())
    if not syms:
        return out
    print(f"Filling the latest close for {len(syms)} symbols from hourly bars ...")
    h = yf.download(syms, period="1mo", interval="1h", auto_adjust=False, group_by="ticker", progress=False,
                    threads=True)
    for sym in syms:
        try:
            c = h[sym]["Close"].dropna()
        except KeyError:
            continue
        idx = c.index.tz_localize(None) if c.index.tz is None else c.index.tz_convert("Asia/Kolkata").tz_localize(None)
        last = pd.Series(c.to_numpy(), index=idx.normalize()).groupby(level=0).last()
        rows = miss & (out["Symbol"] == sym)
        for d in out.index[rows]:
            if d in last.index:
                m = rows & (out.index == d)
                out.loc[m, "Close"] = last[d]
                out.loc[m, "Adj Close" if "Adj Close" in out else "Close"] = last[d]
                out.loc[m, "High"] = out.loc[m, "High"].clip(lower=last[d])
                out.loc[m, "Low"] = out.loc[m, "Low"].clip(upper=last[d])
    return out


def clean(df: pd.DataFrame, max_jump: float = 0.4) -> pd.DataFrame:
    """Drop obviously bad rows: non-positive prices, inconsistent OHLC, and
    single-day spikes > max_jump that reverse next day."""
    df = df[(df[["Open", "High", "Low", "Close"]] > 0).all(axis=1)].copy()
    df["High"] = df[["Open", "High", "Low", "Close"]].max(axis=1)
    df["Low"] = df[["Open", "High", "Low", "Close"]].min(axis=1)

    df = df.sort_values(["Symbol", "Date"])
    r = df.groupby("Symbol")["Close"].pct_change()
    nxt = r.groupby(df["Symbol"]).shift(-1)
    bad = (r.abs() > max_jump) & (nxt.abs() > max_jump) & (r * nxt < 0)
    return df[~bad.fillna(False)]


def drop_prelisting(df: pd.DataFrame, min_run: int = 20) -> tuple[pd.DataFrame, dict]:
    """Yahoo pads some symbols with junk before real trading starts (e.g. TCS from 2002, listed
    Aug 2004): long runs of an identical close. Per symbol, drop all rows up to the end of the last
    run of >= min_run identical closes, then leading rows whose volume is < 10% of the median volume
    of the following year (thin pre-listing quotes), until 10 normal days in a row. Returns (df, {symbol: (rows dropped, new first date)})."""
    keep, dropped = [], {}
    for sym, g in df.groupby("Symbol", sort=False):
        g = g.sort_index()
        run_id = (g["Close"].diff() != 0).cumsum()
        size = run_id.map(run_id.value_counts())
        long_ = np.flatnonzero((size >= min_run).to_numpy())
        if len(long_):
            cut = long_[-1] + 1
            dropped[sym] = (cut, g.index[cut].date() if cut < len(g) else None)
            g = g.iloc[cut:]
        if not sym.startswith("^") and len(g) > 250:               # thin pre-listing rows
            v = g["Volume"].to_numpy()
            ahead = pd.Series(v[::-1]).rolling(250, min_periods=50).median().to_numpy()[::-1]
            good = pd.Series(v[:510] >= 0.1 * ahead[:510]).astype(int)
            ok = np.flatnonzero(good[::-1].rolling(10).sum()[::-1].to_numpy()[:500] == 10)
            cut2 = ok[0] if len(ok) else 0                               # first of 10 normal days
            if cut2:
                n0 = dropped.get(sym, (0, None))[0]
                dropped[sym] = (n0 + cut2, g.index[cut2].date())
                g = g.iloc[cut2:]
        keep.append(g)
    return pd.concat(keep), dropped


def save(df: pd.DataFrame) -> None:
    """Merge into the cache: symbols in df replace their old rows, others are kept."""
    DATA_DIR.mkdir(exist_ok=True)
    if OHLCV_PATH.exists():
        old = pd.read_parquet(OHLCV_PATH)
        df = pd.concat([old[~old["Symbol"].isin(df["Symbol"].unique())], df])
    df.to_parquet(OHLCV_PATH)


def cached_symbols() -> set[str]:
    if not OHLCV_PATH.exists():
        return set()
    return set(pd.read_parquet(OHLCV_PATH, columns=["Symbol"])["Symbol"].unique())


def load(symbols: list[str] | None = None, start: str | None = None) -> dict[str, pd.DataFrame]:
    """Load cache -> dict of wide DataFrames {field: Date x Symbol} ready for vectorbt."""
    df = pd.read_parquet(OHLCV_PATH)
    if symbols:
        df = df[df["Symbol"].isin(symbols)]
    if start:
        df = df[df.index >= start]
    return {f: df.pivot(columns="Symbol", values=f).sort_index() for f in FIELDS}


def ohlcv_for(symbol: str, start: str | None = None) -> pd.DataFrame:
    df = pd.read_parquet(OHLCV_PATH)
    df = df[df["Symbol"] == symbol].drop(columns="Symbol").sort_index()
    return df[df.index >= start] if start else df


def index_close(key: str) -> pd.Series:
    """Yahoo close series for an index key (only indices Yahoo provides)."""
    from .indices import INDICES
    y = INDICES[key]["yahoo"]
    if not y:
        raise ValueError(f"{key}: no index series available on Yahoo")
    if y not in cached_symbols():
        raise ValueError(f"{key}: {y} not cached; run: python download.py --index {key}")
    return ohlcv_for(y)["Close"].rename(key)
