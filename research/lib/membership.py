"""Point-in-time NIFTY 500 membership, rebuilt from NSE Indices' change notices (niftyindices.com press releases).

    python -m lib.membership build <pdf_dir> <links.tsv>    -> data/constituents/NIFTY500_changes.csv
    members_on(date) -> set of Yahoo symbols (RELIANCE.NS ...) in the index on that date

Method: parse every notice for the NIFTY 500 section ("S&P CNX 500" to 2010, "CNX 500", "NIFTY 500"), read the
excluded / included rows, map them to today's NSE symbols (symbol-change and name-change files; company names
for the older, symbol-less notices), then walk backwards from today's list: before each effective date,
members = members - included + excluded. Names that cannot be mapped stay in the set as "?name" placeholders
so the index size stays near 500; their stocks are not tradeable (no price data) either way.
"""
import csv, difflib, re, sys
from datetime import datetime
from functools import lru_cache
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CONS = ROOT.parent / "data" / "constituents"
CHANGES = CONS / "NIFTY500_changes.csv"
REF = CONS / "nse_ref"               # EQUITY_L.csv, symbolchange.csv, namechange.csv

IDX500 = re.compile(r"(?:S\s*&\s*P\s+)?(?:CNX|NIFTY)\s*500(?:\s+Index)?\s*:?\s*$", re.I)
HEADER = re.compile(r"^\s*(?:\(?\d{1,2}\)|\d{1,2}\.|\(?[a-z]\))\s+(.{3,90}?)\s*$")
ROW = re.compile(r"^\s*(\d{1,3})\s+(.+?)\s*$")
SYM = re.compile(r"^[A-Z0-9][A-Z0-9&\-]{1,19}$")
DATE = r"([A-Z][a-z]+\.?\s+\d{1,2},?\s*\d{4}|\d{1,2}(?:st|nd|rd|th)?\s+[A-Z][a-z]+,?\s*\d{4})"


def _date(s):
    s = re.sub(r"(\d)(st|nd|rd|th)", r"\1", s.replace(".", "").replace(",", " "))
    s = re.sub(r"\s+", " ", s).strip()
    for f in ("%B %d %Y", "%b %d %Y", "%d %B %Y", "%d %b %Y", "%Sept %d %Y"):
        try:
            return datetime.strptime(s, f).date()
        except ValueError:
            pass
    s = s.replace("Sept ", "Sep ")
    try:
        return datetime.strptime(s, "%b %d %Y").date()
    except ValueError:
        return None


def norm(name):
    n = name.lower().replace("&", " and ")
    n = re.sub(r"\(.*?\)", " ", n)
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    n = re.sub(r"\b(the|ltd|limited|co|company|corporation|corp|india|of|and|inc|pvt|private)\b", " ", n)
    return re.sub(r"\s+", " ", n).strip()


@lru_cache(None)
def _ref():
    eq = pd.read_csv(REF / "EQUITY_L.csv")
    eq.columns = [c.strip() for c in eq.columns]
    names = {norm(n): s.strip() for s, n in zip(eq["SYMBOL"], eq["NAME OF COMPANY"])}
    sc = pd.read_csv(REF / "symbolchange.csv", encoding="latin-1")
    sc.columns = [c.strip() for c in sc.columns]
    sc["d"] = pd.to_datetime(sc["EFFECTIVE DATE"].str.strip(), format="%d-%b-%Y", errors="coerce")
    nxt = {}
    for o, n in sc.sort_values("d")[["OLD SYMBOL", "NEW SYMBOL"]].itertuples(index=False):
        nxt[o.strip()] = n.strip()
    nc = pd.read_csv(REF / "namechange.csv", encoding="latin-1")
    nc.columns = [c.strip() for c in nc.columns]
    for s, o in zip(nc["SYMBOL"], nc["OLD NAME OF THE COMPANY"]):
        names.setdefault(norm(str(o)), s.strip())
    return names, nxt, set(eq["SYMBOL"].str.strip())


def current_symbol(sym):
    _, nxt, _ = _ref()
    seen = set()
    while sym in nxt and sym not in seen:
        seen.add(sym)
        sym = nxt[sym]
    return sym


def by_name(name):
    names, _, _ = _ref()
    k = norm(name)
    if k in names:
        return names[k]
    m = difflib.get_close_matches(k, list(names), n=1, cutoff=0.92)
    return names[m[0]] if m else None


def parse(text, title=""):
    """-> (effective date | None, [(action 'in'|'out', company, symbol | None)]) for the NIFTY 500 section."""
    eff = None
    for src in (title, text):
        m = re.search(r"(?:w\.?\s?e\.?\s?f\.?|effective\s+(?:from|on|date)?)\s*:?\s*" + DATE, src, re.I)
        if m:
            eff = _date(m.group(1))
            if eff:
                break
    lines = [re.sub(r"^\s*-{3,}\s*", "", l) for l in text.splitlines()]
    lines = [l for l in lines if l.strip()]
    out, in500, mode, has_sym = [], False, None, False
    single = bool(re.search(r"changes?\s+in\s+(?:the\s+)?(?:S\s*&\s*P\s+)?(?:CNX|NIFTY)\s*500\b(?!\s*(?:and|&|,))",
                            " ".join(lines[:40]), re.I)) and not any(HEADER.match(l) for l in lines)
    in500 = single
    for l in lines:
        h = HEADER.match(l)
        if h and re.search(r"index|nifty|cnx|midcap|smallcap|\b\d{2,3}\b", h.group(1), re.I):
            in500, mode = bool(IDX500.search(h.group(1).strip())), None
            continue
        low = l.lower()
        if "symbol" in low and ("company" in low or "sr" in low or low.strip() == "symbol"):
            has_sym = True
        elif "industry" in low and "company" in low:
            has_sym = False
        if "exclu" in low and ("follow" in low or "being" in low):
            mode = "out"; continue
        if "inclu" in low and ("follow" in low or "being" in low):
            mode = "in"; continue
        if not in500 or mode is None:
            continue
        r = ROW.match(l)
        if not r or re.match(r"^\d{1,2}\s+(?:of|the)\b", l, re.I):
            continue
        body = r.group(2)
        toks = body.split()
        sym = toks[-1] if has_sym and len(toks) > 1 and SYM.match(toks[-1]) and not toks[-1].isdigit() else None
        name = " ".join(toks[:-1]) if sym else body
        if not sym:                                       # old notices: "Company Ltd. Industry" -> "Company Ltd."
            m = re.match(r"(.+?\b(?:Ltd|Limited|Corporation|Corpn|Co)\b\.?)", name)
            name = m.group(1) if m else name
        if re.search(r"company name|symbol|sr\.?\s*no", name, re.I):
            continue
        out.append((mode, name.strip(), sym))
    return eff, out


def build(pdf_dir, links_tsv):
    import pdfplumber
    titles = {}
    for line in open(links_tsv, encoding="utf-8"):
        u, *t = line.rstrip("\n").split("\t")
        titles[Path(u).name] = (t[0] if t else "")
    rows = []
    for f in sorted(Path(pdf_dir).glob("*.pdf")):
        try:
            with pdfplumber.open(f) as p:
                text = "\n".join((pg.extract_text() or "") for pg in p.pages)
        except Exception as e:                                  # broken / non-PDF download
            print("skip", f.name, type(e).__name__)
            continue
        title = titles.get(f.name, "").replace("&amp;", "&")
        eff, ch = parse(text, title)
        if not ch:
            continue
        if eff is None:
            m = re.search(r"ind_prs(\d{8})", f.name)
            eff = datetime.strptime(m.group(1), "%d%m%Y").date() if m else None
        for act, name, sym in ch:
            cur = current_symbol(sym) if sym else by_name(name)
            rows.append({"date": eff, "action": act, "company": name, "symbol_raw": sym or "",
                         "symbol": cur or "", "source": f.name})
    df = pd.DataFrame(rows).drop_duplicates(["date", "action", "company"]).sort_values(["date", "action"])
    df.to_csv(CHANGES, index=False)
    return df


@lru_cache(None)
def _timeline():
    """[(start date, frozenset of members valid from that date)] in ascending order, rebuilt backwards from
    today's list."""
    from .indices import constituents
    cur = {s.strip() for s in constituents("NIFTY500")["Symbol"]}
    asof = pd.Timestamp(datetime.fromtimestamp((CONS / "NIFTY500.csv").stat().st_mtime).date())
    ch = pd.read_csv(CHANGES, parse_dates=["date"]).fillna("")
    ch = ch[ch.date <= asof]                                    # changes after the list date have not happened yet
    key = lambda r: r.symbol if r.symbol else "?" + norm(r.company)
    valid = []
    for d, g in sorted(ch.groupby("date"), key=lambda x: x[0], reverse=True):
        valid.append((d, frozenset(cur)))                      # valid from d until the next change
        ins = {key(r) for r in g.itertuples() if r.action == "in"}
        outs = {key(r) for r in g.itertuples() if r.action == "out"}
        cur = (cur - ins) | outs
    valid.append((pd.Timestamp.min, frozenset(cur)))
    return valid[::-1]


def members_on(date) -> set:
    """Yahoo symbols in NIFTY 500 on `date` (placeholders for unmapped names dropped)."""
    date, s = pd.Timestamp(date), None
    for d, m in _timeline():
        if d > date:
            break
        s = m
    return {f"{x}.NS" for x in s if not x.startswith("?")}


def membership_table(days: pd.DatetimeIndex, symbols) -> pd.DataFrame:
    """day x symbol bool: was the stock in NIFTY 500 that day."""
    tl = _timeline()
    starts = pd.DatetimeIndex([max(d, pd.Timestamp("1900-01-01")) for d, _ in tl])
    pos = starts.searchsorted(days, side="right") - 1
    cols = {}
    for sym in symbols:
        base = sym[:-3] if sym.endswith(".NS") else sym
        inside = [base in m for _, m in tl]
        cols[sym] = [inside[p] for p in pos]
    return pd.DataFrame(cols, index=days)


def ever_members() -> list[str]:
    """Yahoo symbols of every mapped stock that was in NIFTY 500 at any time in the rebuilt history."""
    return sorted({f"{x}.NS" for _, m in _timeline() for x in m if not x.startswith("?")})


def size_series(freq="QE"):
    pts = [(d, len(s), sum(x.startswith("?") for x in s)) for d, s in _timeline()[1:]]
    return pd.DataFrame(pts, columns=["date", "size", "placeholders"]).set_index("date")


if __name__ == "__main__":
    if sys.argv[1] == "build":
        df = build(sys.argv[2], sys.argv[3])
        print(len(df), "changes,", (df.symbol == "").sum(), "unmapped names,", df.date.nunique(), "dates")


@lru_cache(maxsize=None)
def coverage(years=(2006, 2008, 2010, 2015, 2020, 2025)) -> list[tuple[int, int, int]]:
    """(year, members on 1 July, members with a price in the 5 trading days before): how much of the PIT universe
    the price cache covers. Members without prices (mostly delisted) can't be traded in the backtest: that is the
    survivorship bias left over."""
    from . import data
    have = data.cached_symbols()
    out = []
    for y in years:
        d = pd.Timestamp(f"{y}-07-01")
        m = sorted(members_on(d))
        c = data.load([s for s in m if s in have])["Close"]
        n = int(c.loc[d - pd.Timedelta(days=8):d].notna().any().sum())
        out.append((y, len(m), n))
    return out
