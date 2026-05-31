"""共用 UI 元件：頁面標題、區段標題、資料來源徽章、KPI、卡片、進度環、VS 區塊。

注意：所有 st.markdown 注入的 HTML 必須去掉前導空白縮排，否則 Streamlit 會把 4 個以上
空白開頭的行當成 markdown code block 渲染（直接顯示原始 HTML）。
"""
from __future__ import annotations

from typing import Iterable, Literal

import streamlit as st

from models.player import Player
from ui.theme import COLORS, SOURCE_BADGE_STYLES


# ── 基本 ───────────────────────────────────────────

def render_page_header(title: str, subtitle: str = "") -> None:
    subtitle_html = f"<p>{_escape(subtitle)}</p>" if subtitle else ""
    html = (
        '<div class="spurs-hero">'
        '<span class="court-line"></span>'
        f'<h1>{_escape(title)}</h1>'
        f'{subtitle_html}'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_section(title: str) -> None:
    html = (
        '<div class="spurs-section-title">'
        '<span class="bar"></span>'
        f'<h3>{_escape(title)}</h3>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_source_badge(source: str | None) -> None:
    if not source or source not in SOURCE_BADGE_STYLES:
        return
    style = SOURCE_BADGE_STYLES[source]
    html = (
        f'<span class="spurs-badge" style="background:{style["bg"]};color:{style["fg"]};">'
        f'資料來源 · {style["label"]}'
        '</span>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_metric_row(metrics: Iterable[tuple[str, str]]) -> None:
    metric_list = list(metrics)
    if not metric_list:
        return
    columns = st.columns(len(metric_list))
    for column, (label, value) in zip(columns, metric_list, strict=True):
        column.metric(label, value)


# ── M11 Dashboard 元件 ─────────────────────────────

AccentColor = Literal["silver", "green", "red", "blue"]


def render_stat_card(label: str, value: str, sub: str = "", accent: AccentColor = "silver") -> None:
    accent_class = {
        "silver": "",
        "green": "accent-green",
        "red": "accent-red",
        "blue": "accent-blue",
    }[accent]
    sub_html = f'<p class="sub">{_escape(sub)}</p>' if sub else ""
    html = (
        f'<div class="spurs-stat-card {accent_class}">'
        f'<p class="label">{_escape(label)}</p>'
        f'<p class="value">{_escape(value)}</p>'
        f'{sub_html}'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_kpi_strip(items: list[tuple[str, str, str]]) -> None:
    if not items:
        return
    cells = "".join(
        (
            '<div class="kpi">'
            f'<div class="k-label">{_escape(label)}</div>'
            f'<div class="k-value">{_escape(value)}</div>'
            f'<div class="k-sub">{_escape(sub)}</div>'
            '</div>'
        )
        for label, value, sub in items
    )
    st.markdown(f'<div class="spurs-kpi-strip">{cells}</div>', unsafe_allow_html=True)


def render_player_card(
    player: Player,
    fantasy_score: float | None = None,
    salary: float | None = None,
    team_side: Literal["blue", "red"] | None = None,
) -> None:
    initial = player.name.strip()[0].upper() if player.name else "?"
    if player.image_url:
        avatar_html = f'<img class="avatar-img" src="{player.image_url}" alt="{_escape(initial)}">'
    else:
        avatar_html = f'<div class="avatar">{_escape(initial)}</div>'

    footer_html = ""
    if fantasy_score is not None or salary is not None:
        fs = f"FS {fantasy_score:.1f}" if fantasy_score is not None else ""
        sal = f"$ {salary:.1f}" if salary is not None else ""
        footer_html = (
            '<div class="footer">'
            f'<span class="fs">{_escape(fs)}</span>'
            f'<span class="salary">{_escape(sal)}</span>'
            '</div>'
        )
    side_class = f" team-{team_side}" if team_side else ""
    html = (
        f'<div class="spurs-player-card{side_class}">'
        '<div class="head">'
        f'{avatar_html}'
        '<div>'
        f'<p class="name">{_escape(player.name)}</p>'
        f'<span class="team-chip">{_escape(player.team)}</span>'
        f'<span class="pos-chip">{_escape(player.position)}</span>'
        '</div>'
        '</div>'
        '<div class="stats">'
        f'<div class="stat-item"><div class="s-label">PTS</div><div class="s-value">{player.points:.1f}</div></div>'
        f'<div class="stat-item"><div class="s-label">REB</div><div class="s-value">{player.rebounds:.1f}</div></div>'
        f'<div class="stat-item"><div class="s-label">AST</div><div class="s-value">{player.assists:.1f}</div></div>'
        f'<div class="stat-item"><div class="s-label">STL</div><div class="s-value">{player.steals:.1f}</div></div>'
        f'<div class="stat-item"><div class="s-label">BLK</div><div class="s-value">{player.blocks:.1f}</div></div>'
        '</div>'
        f'{footer_html}'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_progress_ring(pct: float, label: str, sub: str = "", note: str = "") -> None:
    pct_clamped = max(0.0, min(pct, 1.0))
    deg = int(pct_clamped * 360)
    ring_color = COLORS["success"] if pct_clamped <= 0.85 else (
        COLORS["silver"] if pct_clamped <= 1.0 else COLORS["warning"]
    )
    bg = f"conic-gradient({ring_color} {deg}deg, #2A2C2F {deg}deg)"
    html = (
        '<div class="spurs-ring-wrap">'
        f'<div class="spurs-ring" style="background: {bg};">'
        f'<div class="ring-value">{int(pct_clamped * 100)}%</div>'
        '</div>'
        '<div class="ring-info">'
        f'<div class="ring-label">{_escape(label)}</div>'
        f'<div class="ring-sub">{_escape(sub)}</div>'
        f'<div class="ring-note">{_escape(note)}</div>'
        '</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_vs_block(
    team_a_name: str,
    team_b_name: str,
    win_a: float,
    win_b: float,
    winner_side: str = "A",
) -> None:
    a_class = "side winner" if winner_side == "A" else "side"
    b_class = "side winner" if winner_side == "B" else "side"
    html = (
        '<div class="spurs-vs">'
        f'<div class="{a_class}">'
        f'<div class="team-name">{_escape(team_a_name)}</div>'
        f'<div class="win-rate">{win_a:.1f}<span class="win-rate-suffix">%</span></div>'
        '</div>'
        '<div class="vs-text">VS</div>'
        f'<div class="{b_class} right">'
        f'<div class="team-name">{_escape(team_b_name)}</div>'
        f'<div class="win-rate">{win_b:.1f}<span class="win-rate-suffix">%</span></div>'
        '</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_game_card(
    home_team: str,
    away_team: str,
    home_score: int,
    away_score: int,
    status: str,
    game_date: str = "",
) -> None:
    date_html = (
        f'<div class="gc-date">{_escape(game_date)}</div>' if game_date else ""
    )
    html = (
        '<div class="spurs-game-card">'
        f'<div class="gc-name gc-home">{_escape(home_team)}</div>'
        '<div class="gc-mid-top"></div>'
        f'<div class="gc-name gc-away">{_escape(away_team)}</div>'
        f'<div class="gc-score gc-home">{home_score}</div>'
        f'<div class="gc-status">{_escape(status)}</div>'
        f'<div class="gc-score gc-away">{away_score}</div>'
        f'{date_html}'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def render_feature_card(title: str, desc: str) -> None:
    html = (
        '<div class="spurs-feature-card">'
        f'<div class="f-title">{_escape(title)}</div>'
        f'<div class="f-desc">{_escape(desc)}</div>'
        '</div>'
    )
    st.markdown(html, unsafe_allow_html=True)


def _escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
