"""Permanent strategy IDs: 'S' + UUIDv7 (RFC 9562), shown as 'S' + the last 8 hex digits.

    python -m lib.ids assign     give every strategies/**/*.json without an "id" a new one, update the registry
    python -m lib.ids check      verify: every config has a unique id, short forms are unique, registry matches

The full id is stored in each config ("id") and in strategies/registry.csv. IDs are never reused or changed:
renaming or editing a strategy keeps its id; a deleted strategy stays in the registry with status 'deleted'.
The short form uses the random tail of the UUID (the head is a timestamp, shared by IDs made in the same
moment). If two short forms ever collide, `short()` callers should use `short(id, 12)`; `check` reports it.
"""
import csv, json, os, sys, time, uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REG = ROOT / "strategies" / "registry.csv"
FIELDS = ["id", "short", "name", "path", "created", "status"]


def uuid7(ms: int | None = None) -> uuid.UUID:
    ms = int(time.time() * 1000) if ms is None else ms
    r = int.from_bytes(os.urandom(10), "big")
    v = (ms & (2 ** 48 - 1)) << 80 | 0x7 << 76 | (r >> 68 & 0xFFF) << 64 | 0b10 << 62 | (r & (2 ** 62 - 1))
    return uuid.UUID(int=v)


def new_id(ms: int | None = None) -> str:
    return "S" + str(uuid7(ms))


def short(sid: str, n: int = 8) -> str:
    return "S" + sid.replace("-", "")[-n:]


def created(sid: str) -> str:
    ms = int(sid[1:].replace("-", "")[:12], 16)
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%d")


def configs():
    return sorted(p for p in (ROOT / "strategies").rglob("*.json"))


def load_registry() -> dict:
    if not REG.exists():
        return {}
    return {r["id"]: r for r in csv.DictReader(open(REG))}


def save_registry(reg: dict):
    with open(REG, "w", newline="") as f:
        w = csv.DictWriter(f, FIELDS)
        w.writeheader()
        for r in sorted(reg.values(), key=lambda r: r["id"]):
            w.writerow(r)


def by_name() -> dict:
    """strategy name -> full id, from the configs."""
    return {c["name"]: c["id"] for c in (json.load(open(p)) for p in configs()) if "id" in c}


def assign():
    reg, base = load_registry(), int(time.time() * 1000)
    k = 0
    for p in configs():
        c = json.load(open(p))
        if "id" not in c:
            c = {"id": new_id(base + k), **c}      # +1 ms each keeps creation order within a batch
            k += 1
            json.dump(c, open(p, "w"), indent=2); open(p, "a").write("\n")
            print(f"{short(c['id'])}  {c['name']}")
        reg[c["id"]] = {"id": c["id"], "short": short(c["id"]), "name": c["name"],
                        "path": p.relative_to(ROOT).as_posix(), "created": created(c["id"]),
                        "status": reg.get(c["id"], {}).get("status", "active")}
    live = {json.load(open(p))["id"] for p in configs()}
    for i, r in reg.items():
        if i not in live and r["status"] == "active":
            r["status"] = "deleted"
    save_registry(reg)
    return check()


def check() -> bool:
    ok, seen, shorts = True, {}, {}
    reg = load_registry()
    for p in configs():
        c = json.load(open(p))
        i = c.get("id")
        if not i or not i.startswith("S") or uuid.UUID(i[1:]).version != 7:
            print(f"missing/invalid id: {p}"); ok = False; continue
        if i in seen:
            print(f"duplicate id {i}: {p} and {seen[i]}"); ok = False
        seen[i] = p
        if short(i) in shorts and shorts[short(i)] != i:
            print(f"short-form collision {short(i)}: {p}"); ok = False
        shorts[short(i)] = i
        if i not in reg:
            print(f"not in registry: {p}"); ok = False
    print(f"{len(seen)} strategies, ids {'OK' if ok else 'FAILED'}")
    return ok


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "check"
    sys.exit(0 if (assign() if cmd == "assign" else check()) else 1)


def pdf_section(names, h2_style, fs=7.2):
    """ReportLab flowables for a study PDF: heading + table of short ID, full ID and name for each strategy."""
    from . import pdffont  # noqa: F401  (DejaVu glyphs for ₹ and −)
    from reportlab.lib import colors
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Table, TableStyle, KeepTogether
    m = by_name()
    seen, rows = set(), [["ID", "Full ID", "Strategy"]]
    for n in names:
        if n in seen:
            continue
        seen.add(n)
        rows.append([short(m[n]) if n in m else "–", m.get(n, "(no config)"), n])
    tb = Table(rows, colWidths=[20 * mm, 70 * mm, 86 * mm], repeatRows=1)
    tb.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", fs), ("FONT", (0, 1), (-1, -1), "Helvetica", fs),
        ("FONT", (0, 1), (1, -1), "Courier", fs - .6),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("TOPPADDING", (0, 0), (-1, -1), 2.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.2)]))
    return [KeepTogether([Paragraph("Strategy IDs", h2_style), tb])]
