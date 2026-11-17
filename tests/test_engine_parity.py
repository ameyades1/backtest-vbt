"""Check lib/engine.py reproduces the original engines trade-for-trade.

    python tests/test_engine_parity.py [n_stocks]
"""
import sys, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pandas as pd
from lib import data, indices, ema61, engine
from lib.legacy import ema61_mtf, stochrsi_mtf

TREND3 = {"trend_ema": {"span": 61, "timeframes": ["M", "W", "D"]}, "rsi_min": {"period": 14, "value": 50}}
SRSI = {"type": "stochrsi_cross", "rsi": 14, "stoch": 14, "k": 3, "d": 3, "oversold": 30}
BRK = {"type": "ema_breakout", "span": 61}
EMAX = {"span": 61}


def ex(t=None, ema=False, days=None):
    return {"target_pct": t, "ema_close": EMAX if ema else None, "max_days": days}


CASES = []
for t in [None, .08, .15, .30]:
    CASES.append((f"breakout candle-low t={t}",
                  lambda df, s, t=t: ema61.simulate(df, s, "M", stop_at_low=True, target_pct=t),
                  {"timeframe": "M", "setup": BRK, "stop": {"type": "signal_low"}, "exits": ex(t, t is None)}))
    CASES.append((f"stochrsi M candle t={t}",
                  lambda df, s, t=t: stochrsi_mtf.simulate(df, s, t),
                  {"timeframe": "M", "setup": SRSI, "filters": TREND3, "stop": {"type": "signal_low"},
                   "exits": ex(t, t is None)}))
    CASES.append((f"stochrsi M prev-week t={t}",
                  lambda df, s, t=t: stochrsi_mtf.simulate(df, s, t, stop="prev_week"),
                  {"timeframe": "M", "setup": SRSI, "filters": TREND3, "stop": {"type": "prev_week_low"},
                   "exits": ex(t, t is None)}))
    CASES.append((f"stochrsi W candle t={t}",
                  lambda df, s, t=t: stochrsi_mtf.simulate_weekly(df, s, t),
                  {"timeframe": "W", "setup": SRSI, "filters": TREND3, "stop": {"type": "signal_low"},
                   "exits": ex(t, t is None)}))
    for mode in ["fixed", "trail"]:
        CASES.append((f"mtf weekly-stop {mode} t={t}",
                      lambda df, s, t=t, m=mode: ema61_mtf.simulate(df, s, t, m),
                      {"timeframe": "M", "setup": BRK,
                       "entry": {"day_filters": {"weekly_ema": 61, "daily_ema": 61}},
                       "stop": {"type": "prev_week_low", **({"trail": "weekly_low"} if mode == "trail" else {})},
                       "exits": ex(t, t is None)}))
for days in [90, 365]:
    for t in [None, .15]:
        CASES.append((f"breakout time={days} t={t}",
                      lambda df, s, t=t, n=days: ema61.simulate(df, s, "M", stop_at_low=True, target_pct=t, max_days=n),
                      {"timeframe": "M", "setup": BRK, "stop": {"type": "signal_low"}, "exits": ex(t, t is None, days)}))
        CASES.append((f"mtf time={days} t={t}",
                      lambda df, s, t=t, n=days: ema61_mtf.simulate(df, s, t, "fixed", max_days=n),
                      {"timeframe": "M", "setup": BRK, "entry": {"day_filters": {"weekly_ema": 61, "daily_ema": 61}},
                       "stop": {"type": "prev_week_low"}, "exits": ex(t, t is None, days)}))
for tr in [None, .10, .20]:
    CASES.append((f"breakout trail={tr}",
                  lambda df, s, tr=tr: ema61.simulate(df, s, "M", trail_pct=tr),
                  {"timeframe": "M", "setup": BRK,
                   "stop": {"type": "trail_pct", "pct": tr} if tr else {"type": "none"},
                   "exits": ex(None, tr is None)}))


def key(t):
    return (t.symbol, t.signal_date, t.entry_date, round(t.entry, 6), t.exit_date,
            None if t.exit is None else round(t.exit, 6), t.reason,
            None if t.stop is None else round(t.stop, 6))


if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    syms = [s for s in indices.symbols("NIFTY500") if s in data.cached_symbols()]
    if n:
        syms = random.Random(0).sample(syms, n)
    d = data.load(syms)
    dailies = {s: pd.DataFrame({f: d[f][s] for f in ["Open", "High", "Low", "Close", "Volume"]}).dropna()
               for s in syms}
    bad = 0
    for name, old, cfg in CASES:
        a = [key(t) for s, df in dailies.items() for t in old(df, s)]
        b = [key(t) for s, df in dailies.items() for t in engine.simulate(df, s, cfg)]
        ok = a == b
        bad += not ok
        print(f"{'OK  ' if ok else 'DIFF'} {name:34s} {len(a):6d} trades" + ("" if ok else f" vs {len(b)}"))
        if not ok:
            for x, y in zip(a, b):
                if x != y:
                    print("   old", x, "\n   new", y); break
    print(f"\n{len(CASES) - bad}/{len(CASES)} cases identical on {len(syms)} stocks")
    sys.exit(1 if bad else 0)
