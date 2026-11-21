"""Skipped-signals study for Sde394f26 (D), Sa016f4eb (C) and S63387f09 (Y, your choice), point-in-time NIFTY 500.
    python studies/skipped.py [workers=3] [tags=DCYA]   (resumable) ; then python studies/skipped_report.py
1. base run with every signal logged (taken / skipped + reason)  -> results/studies/skipped/<tag>/base/signals_none.csv
2. slot variants 15, 20, unlimited (strategies/skipped/*.json; scoreboard runs)
3. 200 runs with random ranking of same-day signals              -> results/studies/skipped/random.csv
"""
import copy, json, os, sys, time
from multiprocessing import Pool
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "studies"))
from longshort_configs import write, load
OUT = ROOT / "results" / "studies" / "skipped"
OUT.mkdir(parents=True, exist_ok=True)
BASES = {"D": "longshort/L_cap20_dd", "C": "ddcut/C_hedge_i50_breadth", "Y": "hold/T25_r025", "A": "stexit/A_flip", "E": "stexit/A_flip_capentry",
         "G": "variants/r1_s7", "H": "variants/r1p5_s7", "T": "variants/st14_3", "I": "variants/r1_s6",
         "J": "variants/r1_s8", "K": "variants/r1p5_s6", "L": "variants/r1p5_s8", "M": "variants/st12_3",
         "N": "variants/st14_2p5"}
NOSLOTS = set("EGHTIJKLMN")                                  # tags without slot variants
TAGN = {"D": "Sde394f26", "C": "Sa016f4eb", "Y": "S63387f09", "A": "Sf5b94362", "E": "S44984096", "G": "Se8a1c516", "H": "Se4840bfe", "T": "Sa1f19d11", "I": "Sf660e97d", "J": "Scefe85a9", "K": "S35200f2f", "L": "S4ed7ae52", "M": "Sf34bb11d", "N": "Se6e624fa"}
SEEDS = range(200)
U = "NIFTY500_PIT"
_C = {}


def configs():
    jobs = []
    for tag, n in BASES.items():
        if tag in NOSLOTS:
            continue
        for k, lab in [(15, "15"), (20, "20"), (1000, "all")]:
            c = load(n); c.pop("id", None)
            c["name"] = f"skipped/{TAGN[tag]}_slots{lab}"
            c["description"] += f" [{'No slot limit (every signal, cash permitting)' if k == 1000 else f'{k} slots instead of 10'}.]"
            c["sizing"]["max_positions"] = k
            write(c, "slots", (U,), jobs)
    return jobs


def work(task):
    import pandas as pd
    import run_strategy as R
    kind, tag, x = task
    if "d" not in _C:
        _C["d"] = R.load_dailies(U)
    t0 = time.time()
    if kind == "base":
        cfg = load(BASES[tag]); cfg["log_skips"] = True
        out = OUT / tag / "base"
    elif kind == "slots":
        cfg = json.load(open(ROOT / x)); out = ROOT / "results" / cfg["name"] / U.lower()
    else:
        cfg = load(BASES[tag]); cfg["sizing"]["rank"] = "random"; cfg["sizing"]["seed"] = x
        out = Path(os.environ.get("TMPDIR", "/tmp")) / f"skipped_rand_{os.getpid()}"
    out.mkdir(parents=True, exist_ok=True)
    r = R.run(cfg, *_C["d"], out).iloc[0]
    return {"kind": kind, "tag": tag, "x": x, "CAGR": r["CAGR %"], "DD": r["Max DD %"], "trades": int(r["Trades taken"]),
            "secs": round(time.time() - t0)}


if __name__ == "__main__":
    w = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    only = sys.argv[2] if len(sys.argv) > 2 else "".join(BASES)
    jobs = configs()
    json.dump(jobs, open(OUT / "jobs.json", "w"), indent=1)
    import subprocess
    subprocess.run([sys.executable, "-m", "lib.ids", "assign"], cwd=ROOT, check=True)
    rp = OUT / "random.csv"
    done = set()
    if rp.exists():
        import pandas as pd
        done = {(a, int(b)) for a, b in pd.read_csv(rp)[["tag", "x"]].itertuples(index=False)}
    tasks = [("base", t, None) for t in only] + \
            [("slots", None, j["config"]) for j in jobs if any(TAGN[t] in j["name"] for t in only)] + \
            [("random", t, s) for s in SEEDS for t in only if (t, s) not in done]
    # group so each worker reuses its trade cache: random runs of one tag go together
    with Pool(w) as pool, open(OUT / "run.log", "a") as log:
        for i, res in enumerate(pool.imap_unordered(work, tasks, chunksize=1), 1):
            msg = f"{time.strftime('%H:%M:%S')} {res['kind']:6} {res['tag']} {res['x']}  CAGR {res['CAGR']:.1f} DD {res['DD']:.1f}  " \
                  f"trades {res['trades']}  {res['secs']}s  ({i}/{len(tasks)})"
            print(msg, flush=True); log.write(msg + "\n"); log.flush()
            if res["kind"] == "random":
                new = not rp.exists()
                with open(rp, "a") as f:
                    if new:
                        f.write("tag,x,CAGR,DD,trades\n")
                    f.write(f"{res['tag']},{res['x']},{res['CAGR']},{res['DD']},{res['trades']}\n")
