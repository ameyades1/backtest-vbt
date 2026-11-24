"""Candlestick charts with indicator lines.

candles(ohlcv,
        overlays={"SMA10": s1, "SMA20": s2},            # lines drawn on the price panel
        panels={"RSI 14": {"RSI": rsi},                  # one extra panel per key, below price
                "MACD": {"MACD": m, "Signal": sig, "Hist": ("bar", hist)}},
        entries=..., exits=...)                          # buy/sell markers
"""
from pathlib import Path
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

CHART_DIR = Path(__file__).resolve().parents[2] / "charts"
LINE_COLORS = ["#2563eb", "#f59e0b", "#9333ea", "#0891b2", "#db2777", "#65a30d"]
UP, DOWN = "#16a34a", "#dc2626"


def _infer_daily(index: pd.DatetimeIndex) -> bool:
    return len(index) > 2 and pd.Series(index).diff().median() <= pd.Timedelta(days=1)


def candles(ohlcv: pd.DataFrame, title: str = "", entries=None, exits=None,
            overlays: dict[str, pd.Series] | None = None,
            panels: dict[str, dict] | None = None,
            volume: bool = True, guides: dict[str, list[float]] | None = None) -> go.Figure:
    """guides: horizontal reference lines per panel, e.g. {"RSI 14": [30, 70]}."""
    panels = panels or {}
    guides = guides or {}
    names = ["Price"] + (["Volume"] if volume else []) + list(panels)
    heights = [0.6] + [0.4 / (len(names) - 1)] * (len(names) - 1) if len(names) > 1 else [1]
    fig = make_subplots(rows=len(names), cols=1, shared_xaxes=True, row_heights=heights,
                        vertical_spacing=0.025, subplot_titles=[""] + names[1:])

    fig.add_trace(go.Candlestick(
        x=ohlcv.index, open=ohlcv["Open"], high=ohlcv["High"], low=ohlcv["Low"],
        close=ohlcv["Close"], name="Price",
        increasing=dict(line=dict(color=UP), fillcolor=UP),
        decreasing=dict(line=dict(color=DOWN), fillcolor=DOWN)), 1, 1)

    for i, (name, s) in enumerate((overlays or {}).items()):
        fig.add_trace(go.Scatter(x=s.index, y=s, name=name, mode="lines",
                                 line=dict(width=1.6, color=LINE_COLORS[i % len(LINE_COLORS)])), 1, 1)

    def _mask(sig):
        return sig.reindex(ohlcv.index).fillna(False).astype(bool)

    if entries is not None:
        e = ohlcv.index[_mask(entries)]
        fig.add_trace(go.Scatter(x=e, y=ohlcv.loc[e, "Low"] * 0.94, mode="markers", name="Buy",
                                 marker=dict(symbol="triangle-up", size=13, color=UP,
                                             line=dict(width=1, color="white"))), 1, 1)
    if exits is not None:
        x = ohlcv.index[_mask(exits)]
        fig.add_trace(go.Scatter(x=x, y=ohlcv.loc[x, "High"] * 1.06, mode="markers", name="Sell",
                                 marker=dict(symbol="triangle-down", size=13, color=DOWN,
                                             line=dict(width=1, color="white"))), 1, 1)

    row = 2
    if volume:
        colors = [UP if c >= o else DOWN for o, c in zip(ohlcv["Open"], ohlcv["Close"])]
        fig.add_trace(go.Bar(x=ohlcv.index, y=ohlcv["Volume"], name="Volume",
                             marker_color=colors, opacity=0.5, showlegend=False), row, 1)
        row += 1

    for pname, series in panels.items():
        for i, (sname, s) in enumerate(series.items()):
            color = LINE_COLORS[i % len(LINE_COLORS)]
            if isinstance(s, tuple) and s[0] == "bar":
                s = s[1]
                fig.add_trace(go.Bar(x=s.index, y=s, name=sname, opacity=0.6,
                                     marker_color=[UP if v >= 0 else DOWN for v in s.fillna(0)]),
                              row, 1)
            else:
                fig.add_trace(go.Scatter(x=s.index, y=s, name=sname, mode="lines",
                                         line=dict(width=1.4, color=color)), row, 1)
        for level in guides.get(pname, []):
            fig.add_hline(y=level, line=dict(dash="dot", width=1, color="#94a3b8"), row=row, col=1)
        row += 1

    fig.update_layout(title=title, height=520 + 170 * (len(names) - 1),
                      xaxis_rangeslider_visible=False, template="plotly_white",
                      hovermode="x unified", legend=dict(orientation="h", y=1.02, x=0),
                      margin=dict(l=60, r=30, t=80, b=40))
    if _infer_daily(ohlcv.index):
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat", "mon"])])
    return fig


def save_html(fig: go.Figure, name: str) -> Path:
    CHART_DIR.mkdir(exist_ok=True)
    path = CHART_DIR / f"{name}.html"
    fig.write_html(path, include_plotlyjs="cdn")
    return path
