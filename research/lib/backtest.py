import pandas as pd
import vectorbt as vbt
from .costs import FEES, SLIPPAGE


def run(close: pd.DataFrame, entries, exits, min_turnover: float | None = 1e7,
        volume: pd.DataFrame | None = None, **kw) -> vbt.Portfolio:
    """Per-stock backtest (each column independent). Optional liquidity filter:
    only enter when 20d avg traded value >= min_turnover (INR)."""
    if min_turnover and volume is not None:
        liquid = (close * volume).rolling(20).mean() >= min_turnover
        entries = entries & liquid
    return vbt.Portfolio.from_signals(close, entries, exits, fees=FEES,
                                      slippage=SLIPPAGE, freq="1D", **kw)


def summary(pf: vbt.Portfolio) -> pd.DataFrame:
    df = pd.DataFrame({
        "total_return": pf.total_return(),
        "cagr": pf.annualized_return(),
        "sharpe": pf.sharpe_ratio(),
        "max_dd": pf.max_drawdown(),
        "trades": pf.trades.count(),
        "win_rate": pf.trades.win_rate(),
    })
    return df.sort_values("sharpe", ascending=False)
