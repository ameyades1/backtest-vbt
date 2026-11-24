"""Signal funnel for the StochRSI + MACD monthly setup: how many monthly candles pass each condition.

    python studies/stochrsi_macd_funnel.py   -> results/studies/stochrsi_macd/{funnel.csv,delay.csv}
"""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
import pandas as pd
from lib import engine
from lib.indicators import resample, ema, stoch_rsi, macd
from run_strategy import load_dailies

OUT = ROOT / "results" / "studies" / "stochrsi_macd"
OUT.mkdir(parents=True, exist_ok=True)
cfg = json.load(open(ROOT / "strategies/stochrsi_macd/monthly_prev_week_stop.json"))
base = json.load(open(ROOT / "strategies/stochrsi_pullback/monthly_prev_week_stop.json"))
_, dailies = load_dailies("NIFTY500")
keys = ["Monthly candles (2000+)", "StochRSI cross from oversold", "MACD crosses up (any level)",
        "MACD crosses up below zero", "MACD below-zero cross within 3 months of a StochRSI cross",
        "+ monthly close above EMA61", "+ weekly and daily close above EMA61", "+ monthly RSI > 50",
        "Plain StochRSI pullback signals (current strategy)"]
cnt = dict.fromkeys(keys, 0)
delays, rows = [], []
for s, d in dailies.items():
    m = resample(d, "M")
    if len(m) < 40:
        continue
    keep = (m.index >= "2000-01-01")
    _, K, D = stoch_rsi(m["Close"])
    st = ((K > D) & (K.shift() <= D.shift()) & (D < 30))
    ml, ms, _ = macd(m["Close"])
    up = (ml > ms) & (ml.shift() <= ms.shift())
    mx = up & (ml < 0)
    recent = st.astype(int).rolling(4, min_periods=1).max() > 0
    setup = mx & recent
    m_ema = m["Close"] > ema(m["Close"], 61)
    full_no_rsi = engine._signal_mask(d, m, "M", {**cfg, "filters": {"trend_ema": cfg["filters"]["trend_ema"]}})
    full = engine._signal_mask(d, m, "M", cfg)
    plain = engine._signal_mask(d, m, "M", base)
    for k, v in zip(keys, [np.ones(len(m), bool), st, up, mx, setup, setup & m_ema, full_no_rsi, full, plain]):
        cnt[k] += int((np.asarray(v, bool) & keep).sum())
    # delay: months from the latest StochRSI cross to the MACD cross, for the final signals
    pos = np.where(full & keep)[0]
    stpos = np.where(st.to_numpy())[0]
    for p in pos:
        prev = stpos[stpos <= p]
        delays.append({"symbol": s, "month": m.index[p], "delay_months": int(p - prev[-1]),
                       "close_vs_ema61_pct": float(m["Close"].iloc[p] / ema(m["Close"], 61).iloc[p] * 100 - 100),
                       "macd": float(ml.iloc[p])})
f = pd.Series(cnt, name="Monthly candles")
f.to_csv(OUT / "funnel.csv")
pd.DataFrame(delays).to_csv(OUT / "delay.csv", index=False)
print(f.to_string()); print(pd.DataFrame(delays).delay_months.value_counts().sort_index())
