"""NSE equity trading holidays (weekdays only) for days not yet in the price data. Past trading days come from the
NIFTY 50 series itself; this list is only needed to find the *next* trading day.

2026 list: NSE circular, cross-checked against pandas_market_calendars XNSE and against the weekdays NIFTY did not
trade in Jan-Nov 2026 (14 of 14 match). Add the next year's list when NSE publishes it (usually in December);
live.py warns when the next trading day falls in a year that isn't listed.
"""
import numpy as np
import pandas as pd

HOLIDAYS = {
    2026: ["2026-01-15", "2026-01-26", "2026-03-03", "2026-03-26", "2026-03-31", "2026-04-03", "2026-04-14",
           "2026-05-01", "2026-05-28", "2026-06-26", "2026-09-14", "2026-10-02", "2026-10-20", "2026-11-10",
           "2026-11-24", "2026-12-25"],
}
_ALL = pd.DatetimeIndex([d for v in HOLIDAYS.values() for d in v])


def covered(day) -> bool:
    return pd.Timestamp(day).year in HOLIDAYS


def next_trading_day(day) -> pd.Timestamp:
    """First weekday after `day` that is not an NSE holiday."""
    d = pd.Timestamp(np.busday_offset(pd.Timestamp(day).date(), 1, roll="forward"))
    while d in _ALL:
        d = pd.Timestamp(np.busday_offset(d.date(), 1, roll="forward"))
    return d
