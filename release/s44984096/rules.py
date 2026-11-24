"""S44984096: every trading rule, in one file. backtest.py and live.py both call these functions, so the
backtest and your daily orders cannot drift apart.

The strategy in one paragraph: buy NIFTY 500 stocks in a long-term uptrend when monthly momentum turns up after a
pullback, only while the NIFTY 500 index is above its 200-day average. Stop at the previous week's low, risk 1% of
equity, at most 10 stocks, no stock above 20% of equity. Sell trades that go nowhere in 25 days; otherwise hold
until the weekly Supertrend turns bearish. Halve risk 10% below the equity high; pause 21 days at 15% below.
"""
import numpy as np
import pandas as pd
from indicators import to_weekly, to_monthly, ema, sma, rsi, stoch_rsi, supertrend_bullish

# ---- the rules as numbers -------------------------------------------------------------------------------------
START = "2006-07-01"           # NIFTY 500 index has a 200-day average from July 2006; NSE data only
STOCH = (14, 14, 3, 3)         # Stochastic RSI on monthly candles
OVERSOLD = 30                  # %D must be below this when %K crosses above %D
TREND_EMA = 61                 # close above EMA 61 on the monthly, last completed weekly and daily candle
RSI_MIN = 50                   # monthly RSI(14) at or above 50
MARKET_INDEX = "^CRSLDX"       # NIFTY 500 index
MARKET_SMA = 200               # buy only if the index closed above its 200-day average the day before
SUPERTREND = (10, 3.0)         # weekly Supertrend; sell at the next open after it turns bullish -> bearish
TIME_STOP_DAYS = 25            # calendar days after entry ...
TIME_STOP_R = 0.25             # ... sell at the next open if the close is below entry + 0.25 x risk
RISK = 0.01                    # of the previous day's equity per new trade
MAX_POSITIONS = 10
POS_CAP = 0.20                 # of equity: at entry, and trimmed at each month-end close
DD_HALVE, DD_PAUSE, PAUSE_DAYS = 10, 15, 21   # % below the equity high -> half risk; pause new trades 21 days
LIQUID_RATE = 6.5              # % a year earned by idle cash (liquid fund)
SLIPPAGE = 0.001               # per side

# Sharekhan delivery, per side (average of buy and sell): brokerage 0.30%, STT 0.1%, stamp 0.015% (buy),
# exchange 0.00297%, SEBI 0.0001%, GST 18% on brokerage + exchange + SEBI.
_GST = 0.18 * (0.0030 + 0.0000297 + 0.000001)
FEE = ((0.0030 + 0.001 + 0.00015 + 0.0000297 + 0.000001 + _GST) + (0.0030 + 0.001 + 0.0000297 + 0.000001 + _GST)) / 2


# ---- 1. setups (month end) ------------------------------------------------------------------------------------
def setups(daily: pd.DataFrame) -> pd.DataFrame:
    """Monthly candles of one stock with a column `setup` (all conditions true at that month's close).
    Weekly and daily conditions use the last completed week / day of the month."""
    m = to_monthly(daily)
    K, D = stoch_rsi(m["Close"], *STOCH)
    cross = (K > D) & (K.shift() <= D.shift()) & (D < OVERSOLD)
    last_day = daily.index[np.searchsorted(daily.index, m.index, side="right") - 1]   # month's last trading day

    w = to_weekly(daily)
    week_ok = (w["Close"] > ema(w["Close"], TREND_EMA)).to_numpy()
    wi = np.searchsorted(w.index, last_day, side="right") - 1           # last week ending on/before that day
    weekly = np.where(wi >= 0, week_ok[np.clip(wi, 0, None)], False)

    day_ok = (daily["Close"] > ema(daily["Close"], TREND_EMA)).reindex(last_day).to_numpy()

    m["setup"] = (cross & (m["Close"] > ema(m["Close"], TREND_EMA)) & (rsi(m["Close"], 14) >= RSI_MIN)).to_numpy() \
        & weekly & day_ok
    m["K"], m["D"] = K, D
    return m


# ---- 2. market filter -----------------------------------------------------------------------------------------
def market_ok(index_close: pd.Series) -> pd.Series:
    """Day -> may we buy today? True if the NIFTY 500 index closed above its 200-day average on the previous
    trading day of the index. False before the average exists."""
    avg = sma(index_close, MARKET_SMA)
    above = (index_close > avg)[avg.notna()]
    return above.shift(1)


# ---- 3. one stock's trades (entry, stop, exits) ---------------------------------------------------------------
def stock_trades(daily: pd.DataFrame, buy_allowed: pd.Series) -> list[dict]:
    """Every trade the rules give for one stock, ignoring money (the portfolio decides which ones it can take).
    buy_allowed: the market filter on this stock's days. One trade at a time per stock; while a trade (taken or
    not by the portfolio) is open, new setups of that stock are ignored."""
    days = daily.index
    o, h, l, c = (daily[x].to_numpy() for x in ("Open", "High", "Low", "Close"))
    m = setups(daily)
    month_end = np.searchsorted(days, m.index, side="right")             # first day after each month
    w = to_weekly(daily)
    week_end = np.searchsorted(days, w.index, side="right")              # first day after each week
    last_week = np.searchsorted(week_end, np.arange(len(days)), side="right") - 1   # last completed week, per day
    bear = ~supertrend_bullish(w, *SUPERTREND).to_numpy()
    flip = bear & np.r_[False, ~bear[:-1]]                               # turned bullish -> bearish this week
    st_exit_days = {week_end[i] for i in np.flatnonzero(flip)}          # sell at the open of the next day
    ok = buy_allowed.reindex(days, method="ffill").fillna(False).to_numpy(dtype=bool)

    trades, free_from = [], 0
    for b in np.flatnonzero(m["setup"].to_numpy()):
        first = month_end[b]                                             # buy-stop live for the whole next month
        if first < free_from or first >= len(days):
            continue
        last = month_end[b + 1] if b + 1 < len(m) else len(days)
        level = m["High"].iat[b]
        k = next((j for j in range(first, last) if h[j] > level and last_week[j] >= 0 and ok[j]), None)
        if k is None:
            continue
        entry = max(level, o[k])                                         # gap up: buy at the open
        stop = w["Low"].iat[last_week[k]]                                # low of the last completed week, fixed
        if stop >= entry:
            continue
        risk = entry - stop
        exit_day, exit_px, why = None, None, "open"
        if c[k] <= stop:                                                 # stop armed from the next session
            exit_day, exit_px, why = k, c[k], "stop-entry-day"
        else:
            for j in range(k + 1, len(days)):
                held, held_before = (days[j] - days[k]).days, (days[j - 1] - days[k]).days
                if held >= TIME_STOP_DAYS > held_before and c[j - 1] < entry + TIME_STOP_R * risk:
                    exit_day, exit_px, why = j, o[j], "time-stop"; break
                if o[j] <= stop:
                    exit_day, exit_px, why = j, o[j], "stop-gap"; break
                if j in st_exit_days:
                    exit_day, exit_px, why = j, o[j], "supertrend"; break
                if l[j] <= stop:
                    exit_day, exit_px, why = j, stop, "stop"; break
        trades.append({"signal_month": m.index[b], "entry_date": days[k], "entry": entry, "stop": stop,
                       "exit_date": days[exit_day] if exit_day is not None else None, "exit": exit_px, "reason": why})
        free_from = exit_day + 1 if exit_day is not None else len(days)
    return trades


# ---- 4. money -------------------------------------------------------------------------------------------------
class DrawdownRule:
    """Feed it yesterday's equity each day; .mult is 1 (normal), 0.5 (10% below the high) or 0 (paused).
    Half risk lasts until a new high; the 21-day pause happens once per drawdown."""

    def __init__(self, capital):
        self.peak, self.halved, self.pause_used, self.pause_left, self.mult = capital, False, False, 0, 1.0

    def update(self, prev_equity):
        self.peak = max(self.peak, prev_equity)
        dd = (1 - prev_equity / self.peak) * 100
        if prev_equity >= self.peak:
            self.halved, self.pause_used = False, False
        if dd >= DD_HALVE:
            self.halved = True
        if dd >= DD_PAUSE and not self.pause_used:
            self.pause_used, self.pause_left = True, PAUSE_DAYS
        if self.pause_left > 0:
            self.mult, self.pause_left = 0.0, self.pause_left - 1
        else:
            self.mult = 0.5 if self.halved else 1.0
        return self.mult


def buy_price(entry):
    """Cash paid per share: price + slippage + costs."""
    return entry * (1 + SLIPPAGE) * (1 + FEE)


def sell_value(qty, price):
    return qty * price * (1 - SLIPPAGE) * (1 - FEE)


def shares(prev_equity, mult, entry, stop, cash):
    """Shares to buy: 1% (x mult) of yesterday's equity at risk, at most 20% of yesterday's equity, at most the
    cash. Returns (shares, capped_by_cash)."""
    q = int(prev_equity * RISK * mult // (entry - stop))
    px = buy_price(entry)
    q = min(q, int(POS_CAP * prev_equity // px))
    if q * px > cash:
        return int(cash // px), True
    return q, False


def trim(qty, price, equity):
    """Shares to sell at a month-end close so the position is at most 20% of equity (0 if none)."""
    n = qty - int(POS_CAP * equity // price)
    return n if 0 < n < qty else 0
