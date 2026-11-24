"""Release tests for S44984096. Run from anywhere:  python release/s44984096/tests/run_tests.py

1. Golden trades: the backtest must reproduce tests/golden_trades.csv (every trade closed by 31 Oct 2026, frozen
   24 Nov 2026 when the release matched the research engine fill for fill). A rule change that alters any trade
   fails here: update the golden file only together with a deliberate, documented rule change.
2. Indicators against a known chart value; drawdown rule, sizing, holidays, market filter timing.
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import data, rules, backtest, indicators  # noqa: E402

failed = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  ({detail})" if detail else ""))
    if not ok:
        failed.append(name)


def test_indicators():
    d = data.load(["PERSISTENT.NS"])["PERSISTENT.NS"][:"2020-06-30"]
    m = indicators.to_monthly(d)
    K, D = indicators.stoch_rsi(m["Close"])
    r = indicators.rsi(m["Close"])
    k, dd, rr = K.iloc[-1], D.iloc[-1], r.iloc[-1]
    check("Persistent Jun 2020 monthly StochRSI / RSI", abs(k - 34.7) < 0.5 and abs(dd - 30.0) < 0.5 and abs(rr - 50.5) < 0.5,
          f"%K {k:.1f} %D {dd:.1f} RSI {rr:.1f}")


def test_drawdown_rule():
    r = rules.DrawdownRule(100.0)
    seq = [r.update(x) for x in [100, 95, 89.9, 89] + [84] * 22 + [84, 99, 101]]
    check("drawdown: half at -10%", seq[2] == 0.5 and seq[1] == 1.0)
    check("drawdown: pause 21 days at -15%, once", seq[4:25] == [0.0] * 21 and seq[25] == 0.5 and seq[26] == 0.5)
    check("drawdown: half risk until a new high", seq[27] == 0.5 and seq[28] == 1.0)


def test_sizing():
    q, capped = rules.shares(10_00_000, 1.0, 500, 460, 10_00_000)
    check("sizing: 1% risk, Rs 40 stop -> 250 shares", q == 250 and not capped, str(q))
    q, _ = rules.shares(10_00_000, 1.0, 500, 480, 10_00_000)
    check("sizing: 20% cap at entry", q == int(0.2 * 10_00_000 // rules.buy_price(500)), str(q))
    q, capped = rules.shares(10_00_000, 1.0, 500, 460, 50_000)
    check("sizing: limited by cash", capped and q == int(50_000 // rules.buy_price(500)), str(q))
    check("costs: Sharekhan delivery about 0.47% per side", abs(rules.FEE - 0.00468) < 0.0001, f"{rules.FEE:.5f}")


def test_calendar_and_market():
    check("holiday: next trading day after 23 Nov 2026 is 25 Nov", data.next_trading_day("2026-11-23") == pd.Timestamp("2026-11-25"))
    check("holiday: after 24 Dec 2026 is 28 Dec", data.next_trading_day("2026-12-24") == pd.Timestamp("2026-12-28"))
    idx = pd.Series([1.0] * 199 + [2.0, 0.5, 3.0], index=pd.bdate_range("2020-01-01", periods=202))
    ok = rules.market_ok(idx)
    check("market filter uses the previous close", bool(ok.iloc[1]) and not bool(ok.iloc[2]) and np.isnan(ok.iloc[0]))


def test_golden():
    g = pd.read_csv(HERE / "golden_trades.csv", parse_dates=["entry_date", "exit_date"])
    trades, closes = backtest.all_trades()
    _, fills, _ = backtest.run(trades, closes)
    f = fills[pd.to_datetime(fills.exit_date) <= "2026-10-31"][g.columns].reset_index(drop=True)
    f["entry_date"], f["exit_date"] = pd.to_datetime(f.entry_date), pd.to_datetime(f.exit_date)
    k = ["symbol", "entry_date", "exit_date", "qty"]
    a, b = g.sort_values(k).reset_index(drop=True), f.sort_values(k).reset_index(drop=True)
    same = len(a) == len(b) and (a[k] == b[k]).all().all() and \
        np.allclose(a[["entry", "stop", "exit"]], b[["entry", "stop", "exit"]], rtol=1e-9)
    check("golden trades (closed by 31 Oct 2026)", same, f"{len(b)} of {len(a)} trades")


if __name__ == "__main__":
    test_indicators(); test_drawdown_rule(); test_sizing(); test_calendar_and_market(); test_golden()
    print("\nALL PASS" if not failed else f"\n{len(failed)} FAILED: {failed}")
    sys.exit(1 if failed else 0)
