"""NIFTY 500 constituent list (current members only -> survivorship bias!)."""
from io import StringIO
from pathlib import Path
import pandas as pd
import requests

URLS = [
    "https://archives.nseindia.com/content/indices/ind_nifty500list.csv",
    "https://niftyindices.com/IndexConstituent/ind_nifty500list.csv",
]
LIST_PATH = Path(__file__).resolve().parent.parent / "data" / "nifty500_list.csv"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def fetch_list(refresh: bool = False) -> pd.DataFrame:
    if LIST_PATH.exists() and not refresh:
        return pd.read_csv(LIST_PATH)
    last_err = None
    for url in URLS:
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            r.raise_for_status()
            df = pd.read_csv(StringIO(r.text))
            LIST_PATH.parent.mkdir(exist_ok=True)
            df.to_csv(LIST_PATH, index=False)
            return df
        except Exception as e:  # try next mirror
            last_err = e
    raise RuntimeError(f"Could not download NIFTY 500 list: {last_err}")


def yahoo_symbols(refresh: bool = False) -> list[str]:
    return [f"{s.strip()}.NS" for s in fetch_list(refresh)["Symbol"]]
