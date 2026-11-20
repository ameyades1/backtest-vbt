"""Registry of NIFTY indices: NSE constituent CSV + Yahoo ticker for the index series.

Constituents are *current* members (survivorship bias). TOTALMARKET_IT / TOTALMARKET_FIN: NIFTY Total Market (750) members whose NSE Industry is Information Technology /
Financial Services (see DERIVED). `yahoo=None` means Yahoo has no
usable history for the index series; it is skipped when trading indices directly.
"""
from io import StringIO
from pathlib import Path
import pandas as pd
import requests

NSE_URL = "https://archives.nseindia.com/content/indices/ind_{}list.csv"
CACHE = Path(__file__).resolve().parent.parent / "data" / "constituents"
HEADERS = {"User-Agent": "Mozilla/5.0"}

# key: (group, display name, NSE csv slug, Yahoo ticker or None)
_R = [
    ("NIFTY50",       "broad",    "Nifty 50",                  "nifty50",               "^NSEI"),
    ("NIFTYNEXT50",   "broad",    "Nifty Next 50",             "niftynext50",           None),
    ("NIFTY100",      "broad",    "Nifty 100",                 "nifty100",              "^CNX100"),
    ("NIFTY200",      "broad",    "Nifty 200",                 "nifty200",              "^CNX200"),
    ("NIFTY500",      "broad",    "Nifty 500",                 "nifty500",              "^CRSLDX"),
    ("MIDCAP50",      "broad",    "Nifty Midcap 50",           None,                    "^NSEMDCP50"),
    ("MIDCAP100",     "broad",    "Nifty Midcap 100",          "niftymidcap100",        "^NSMIDCP"),
    ("MIDCAP150",     "broad",    "Nifty Midcap 150",          "niftymidcap150",        "NIFTYMIDCAP150.NS"),
    ("SMALLCAP100",   "broad",    "Nifty Smallcap 100",        "niftysmallcap100",      None),
    ("SMALLCAP250",   "broad",    "Nifty Smallcap 250",        "niftysmallcap250",      "NIFTYSMLCAP250.NS"),
    ("MICROCAP250",   "broad",    "Nifty Microcap 250",        "niftymicrocap250_",     None),
    ("NIFTY750",      "broad",    "Nifty Total Market (NIFTY 500 + Microcap 250)", "niftytotalmarket_", None),
    ("TOTALMARKET",   "broad",    "Nifty Total Market",        "niftytotalmarket_",     None),
    ("TOTALMARKET_IT",  "sectoral", "Total Market: Information Technology", None,       None),
    ("TOTALMARKET_FIN", "sectoral", "Total Market: Financial Services",     None,       None),
    ("TOTALMARKET_ITFIN", "sectoral", "Total Market: IT + Financial Services", None,     None),
    ("BANK",          "sectoral", "Nifty Bank",                "niftybank",             "^NSEBANK"),
    ("PSUBANK",       "sectoral", "Nifty PSU Bank",            "niftypsubank",          "^CNXPSUBANK"),
    ("PVTBANK",       "sectoral", "Nifty Private Bank",        "nifty_privatebank",     None),
    ("FINANCE",       "sectoral", "Nifty Financial Services",  "niftyfinance",          "NIFTY_FIN_SERVICE.NS"),
    ("FINSRV25_50",   "sectoral", "Nifty Fin Services 25/50",  "niftyfinancialservices25_50", None),
    ("IT",            "sectoral", "Nifty IT",                  "niftyit",               "^CNXIT"),
    ("AUTO",          "sectoral", "Nifty Auto",                "niftyauto",             "^CNXAUTO"),
    ("FMCG",          "sectoral", "Nifty FMCG",                "niftyfmcg",             "^CNXFMCG"),
    ("METAL",         "sectoral", "Nifty Metal",               "niftymetal",            "^CNXMETAL"),
    ("PHARMA",        "sectoral", "Nifty Pharma",              "niftypharma",           "^CNXPHARMA"),
    ("HEALTHCARE",    "sectoral", "Nifty Healthcare",          "niftyhealthcare",       None),
    ("REALTY",        "sectoral", "Nifty Realty",              "niftyrealty",           "^CNXREALTY"),
    ("MEDIA",         "sectoral", "Nifty Media",               "niftymedia",            None),
    ("CONSDURABLES",  "sectoral", "Nifty Consumer Durables",   "niftyconsumerdurables", None),
    ("OILGAS",        "sectoral", "Nifty Oil & Gas",           "niftyoilgas",           None),
    ("ENERGY",        "thematic", "Nifty Energy",              "niftyenergy",           "^CNXENERGY"),
    ("INFRA",         "thematic", "Nifty Infrastructure",      "niftyinfra",            "^CNXINFRA"),
    ("PSE",           "thematic", "Nifty PSE",                 "niftypse",              "^CNXPSE"),
    ("CPSE",          "thematic", "Nifty CPSE",                "niftycpse",             None),
    ("COMMODITIES",   "thematic", "Nifty Commodities",         "niftycommodities",      None),
    ("CONSUMPTION",   "thematic", "Nifty India Consumption",   "niftyconsumption",      "^CNXCONSUM"),
]
INDICES = {k: dict(group=g, name=n, slug=s, yahoo=y) for k, g, n, s, y in _R}
GROUPS = sorted({v["group"] for v in INDICES.values()})


def resolve(keys: list[str]) -> list[str]:
    """Expand group names (broad/sectoral/thematic/all) and validate keys."""
    out = []
    for k in keys:
        k = k.upper()
        if k == "ALL":
            out += list(INDICES)
        elif k.lower() in GROUPS:
            out += [i for i, v in INDICES.items() if v["group"] == k.lower()]
        elif k in INDICES:
            out.append(k)
        else:
            raise SystemExit(f"Unknown index '{k}'. Use one of: {', '.join(INDICES)} or {GROUPS + ['all']}")
    return list(dict.fromkeys(out))


# universes cut from a broad index by NSE's own Industry label: key -> (base index, Industry)
DERIVED = {"TOTALMARKET_IT": ("TOTALMARKET", "Information Technology"),
           "TOTALMARKET_FIN": ("TOTALMARKET", "Financial Services"),
           "TOTALMARKET_ITFIN": ("TOTALMARKET", ("Information Technology", "Financial Services"))}


def constituents(key: str, refresh: bool = False) -> pd.DataFrame:
    if key in DERIVED:
        base, industry = DERIVED[key]
        df = constituents(base, refresh)
        inds = (industry,) if isinstance(industry, str) else industry
        df = df[df["Industry"].str.strip().isin(inds)].reset_index(drop=True)
        CACHE.mkdir(parents=True, exist_ok=True)
        df.to_csv(CACHE / f"{key}.csv", index=False)
        return df
    slug = INDICES[key]["slug"]
    if slug is None:
        return pd.DataFrame(columns=["Company Name", "Industry", "Symbol"])
    path = CACHE / f"{key}.csv"
    if path.exists() and not refresh:
        return pd.read_csv(path)
    r = requests.get(NSE_URL.format(slug), headers=HEADERS, timeout=30)
    r.raise_for_status()
    df = pd.read_csv(StringIO(r.text))
    CACHE.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df


def symbols(key: str, refresh: bool = False) -> list[str]:
    """Yahoo symbols (RELIANCE.NS ...) of an index's current constituents."""
    return [f"{s.strip()}.NS" for s in constituents(key, refresh)["Symbol"]]


def table() -> pd.DataFrame:
    return pd.DataFrame(INDICES).T[["group", "name", "yahoo"]].fillna({"yahoo": "— (not on Yahoo)"})
