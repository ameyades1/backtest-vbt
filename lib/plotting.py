from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

CHART_DIR = Path(__file__).resolve().parent.parent / "charts"


def candles(ohlcv: pd.DataFrame, title: str = "", entries=None, exits=None,
            overlays: dict[str, pd.Series] | None = None) -> go.Figure:
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.78, 0.22],
                        vertical_spacing=0.03)
    fig.add_trace(go.Candlestick(x=ohlcv.index, open=ohlcv["Open"], high=ohlcv["High"],
                                 low=ohlcv["Low"], close=ohlcv["Close"], name="Price"), 1, 1)
    for name, s in (overlays or {}).items():
        fig.add_trace(go.Scatter(x=s.index, y=s, name=name, line=dict(width=1.2)), 1, 1)
    if entries is not None:
        e = entries[entries.fillna(False).astype(bool)].index
        fig.add_trace(go.Scatter(x=e, y=ohlcv.loc[e, "Low"] * 0.97, mode="markers", name="Buy",
                                 marker=dict(symbol="triangle-up", size=10, color="#16a34a")), 1, 1)
    if exits is not None:
        x = exits[exits.fillna(False).astype(bool)].index
        fig.add_trace(go.Scatter(x=x, y=ohlcv.loc[x, "High"] * 1.03, mode="markers", name="Sell",
                                 marker=dict(symbol="triangle-down", size=10, color="#dc2626")), 1, 1)
    fig.add_trace(go.Bar(x=ohlcv.index, y=ohlcv["Volume"], name="Volume",
                         marker_color="#94a3b8"), 2, 1)
    fig.update_layout(title=title, height=750, xaxis_rangeslider_visible=False,
                      template="plotly_white", hovermode="x unified")
    fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    return fig


def save_html(fig: go.Figure, name: str) -> Path:
    CHART_DIR.mkdir(exist_ok=True)
    path = CHART_DIR / f"{name}.html"
    fig.write_html(path, include_plotlyjs="cdn")
    return path
