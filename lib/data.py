"""Download, clean and cache OHLCV for the universe as one long-format parquet."""
from pathlib import Path
import pandas as pd
import yfinance as yf

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
OHLCV_PATH = DATA_DIR / "ohlcv.parquet"
FIELDS = ["Open", "High", "Low", "Close", "Volume"]


def download(symbols: list[str], start: str = "1990-01-01", chunk: int = 50) -> pd.DataFrame:
    """Return long df: index=Date, columns=[Symbol, Open, High, Low, Close, Volume].
    Prices are split/bonus/dividend adjusted (auto_adjust=True)."""
    frames = []
    for i in range(0, len(symbols), chunk):
        batch = symbols[i : i + chunk]
        print(f"Downloading {i + 1}-{i + len(batch)} of {len(symbols)} ...")
        raw = yf.download(batch, start=start, auto_adjust=True, group_by="ticker",
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


def save(df: pd.DataFrame) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    df.to_parquet(OHLCV_PATH)


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
