"""Plotly 圖表元件：折線、雷達、水平 bar、donut。全部套用 Spurs 黑銀深色主題。"""
from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go

from models.player import Player
from ui.theme import COLORS

_FONT = "system-ui, -apple-system, 'Segoe UI', sans-serif"


def _dark_layout(**overrides: Any) -> dict[str, Any]:
    base = {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "font": {"color": COLORS["silver"], "family": _FONT, "size": 12},
        "margin": {"l": 40, "r": 20, "t": 30, "b": 40},
        "xaxis": {
            "gridcolor": "#2A2C2F",
            "zerolinecolor": "#2A2C2F",
            "linecolor": "#2A2C2F",
            "tickfont": {"color": COLORS["cool_blue_gray"]},
        },
        "yaxis": {
            "gridcolor": "#2A2C2F",
            "zerolinecolor": "#2A2C2F",
            "linecolor": "#2A2C2F",
            "tickfont": {"color": COLORS["cool_blue_gray"]},
        },
        "legend": {
            "bgcolor": "rgba(0,0,0,0)",
            "font": {"color": COLORS["silver"]},
        },
        "hoverlabel": {
            "bgcolor": "#1D1F21",
            "bordercolor": "#2A2C2F",
            "font": {"color": COLORS["white"], "family": _FONT},
        },
    }
    base.update(overrides)
    return base


def player_trend_chart(df: pd.DataFrame) -> go.Figure:
    """近年 per-game 折線：PPG / RPG / APG。"""
    fig = go.Figure()
    colors = {
        "points": COLORS["silver"],
        "rebounds": COLORS["cool_blue_gray"],
        "assists": COLORS["success"],
    }
    labels = {"points": "PPG", "rebounds": "RPG", "assists": "APG"}
    for col, color in colors.items():
        if col not in df.columns:
            continue
        fig.add_trace(
            go.Scatter(
                x=df["season"],
                y=df[col],
                name=labels[col],
                mode="lines+markers",
                line={"color": color, "width": 2.5},
                marker={"size": 7, "color": color},
                hovertemplate=f"<b>{labels[col]}</b> %{{y:.1f}}<extra>%{{x}}</extra>",
            )
        )
    fig.update_layout(**_dark_layout(height=320))
    return fig


def player_radar_chart(player: Player) -> go.Figure:
    """單一球員五維雷達：PTS / REB / AST / STL / BLK。"""
    categories = ["PTS", "REB", "AST", "STL", "BLK"]
    values = [
        player.points,
        player.rebounds,
        player.assists,
        player.steals * 5,
        player.blocks * 5,
    ]
    raw = [player.points, player.rebounds, player.assists, player.steals, player.blocks]
    fig = go.Figure()
    fig.add_trace(
        go.Scatterpolar(
            r=values + [values[0]],
            theta=categories + [categories[0]],
            fill="toself",
            line={"color": COLORS["silver"], "width": 2},
            fillcolor="rgba(196, 206, 212, 0.18)",
            name=player.name,
            customdata=raw + [raw[0]],
            hovertemplate="<b>%{theta}</b> %{customdata:.1f}<extra></extra>",
        )
    )
    max_val = max(values + [10])
    fig.update_layout(
        polar={
            "bgcolor": "rgba(0,0,0,0)",
            "radialaxis": {
                "visible": True,
                "range": [0, max_val * 1.1],
                "gridcolor": "#2A2C2F",
                "linecolor": "#2A2C2F",
                "tickfont": {"color": COLORS["cool_blue_gray"], "size": 10},
            },
            "angularaxis": {
                "gridcolor": "#2A2C2F",
                "linecolor": "#2A2C2F",
                "tickfont": {"color": COLORS["silver"], "size": 12},
            },
        },
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": COLORS["silver"], "family": _FONT},
        showlegend=False,
        height=320,
        margin={"l": 40, "r": 40, "t": 30, "b": 30},
    )
    return fig


def team_compare_bar(
    team_a_name: str,
    team_b_name: str,
    team_a_values: list[float],
    team_b_values: list[float],
    labels: list[str],
) -> go.Figure:
    """兩隊水平 bar 對比。"""
    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            y=labels,
            x=team_a_values,
            name=team_a_name,
            orientation="h",
            marker={"color": COLORS["silver"]},
            hovertemplate=f"<b>{team_a_name}</b> %{{x:.1f}}<extra>%{{y}}</extra>",
        )
    )
    fig.add_trace(
        go.Bar(
            y=labels,
            x=team_b_values,
            name=team_b_name,
            orientation="h",
            marker={"color": COLORS["cool_blue_gray"]},
            hovertemplate=f"<b>{team_b_name}</b> %{{x:.1f}}<extra>%{{y}}</extra>",
        )
    )
    fig.update_layout(**_dark_layout(
        barmode="group",
        height=320,
        legend={"orientation": "h", "y": 1.1, "x": 0, "bgcolor": "rgba(0,0,0,0)",
                "font": {"color": COLORS["silver"]}},
    ))
    return fig


def vote_donut_chart(
    labels: list[str],
    values: list[int],
    other_label: str | None = None,
) -> go.Figure:
    """投票結果 donut。other_label 指定的項目會套用固定暗色，與其他選項明顯區隔。"""
    palette = [COLORS["silver"], COLORS["cool_blue_gray"], COLORS["success"], COLORS["warning"]]
    _other_color = "#4A4D52"
    colors = [
        _other_color if (other_label and label == other_label) else palette[i % len(palette)]
        for i, label in enumerate(labels)
    ]
    fig = go.Figure(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.6,
            marker={"colors": colors, "line": {"color": "#0B0B0C", "width": 2}},
            textfont={"color": COLORS["white"], "size": 13, "family": _FONT},
            hovertemplate="<b>%{label}</b> %{value} 票 (%{percent})<extra></extra>",
        )
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        font={"color": COLORS["silver"], "family": _FONT},
        showlegend=True,
        legend={"orientation": "v", "x": 1, "y": 0.5, "bgcolor": "rgba(0,0,0,0)"},
        height=300,
        margin={"l": 10, "r": 10, "t": 30, "b": 10},
        annotations=[{
            "text": f"{sum(values)}<br><span style='font-size:12px;color:{COLORS['cool_blue_gray']}'>票</span>",
            "showarrow": False,
            "font": {"color": COLORS["white"], "size": 22, "family": _FONT},
            "x": 0.5, "y": 0.5,
        }],
    )
    return fig
