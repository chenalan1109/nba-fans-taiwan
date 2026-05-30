from __future__ import annotations

from typing import Any

import streamlit as st

from database.seed_data import get_seed_matchups, get_seed_polls
from models.player import Player
from services.cached import get_game_boxscore, get_playoff_series, get_scoreboard, get_season_phase, get_standings
from services.nba_api_service import get_data_mode
from services.player_service import calculate_fantasy_score, get_featured_players
from services.season_service import SeasonPhase
from ui.components import (
    render_feature_card,
    render_kpi_strip,
    render_page_header,
    render_player_card,
    render_section,
)


def _get_todays_top_performers() -> list[Player]:
    """Return top 3 scorers from today's active games; fall back to highest fantasy-score seed players."""
    try:
        scoreboard = get_scoreboard(data_mode=get_data_mode())
        active_games = [
            g for g in scoreboard.get("items", [])
            if str(g.get("status", "")).lower() not in ("scheduled", "")
        ]
        if not active_games:
            return _fallback_performers()

        all_perf: list[dict[str, Any]] = []
        for game in active_games:
            game_id = str(game.get("game_id") or "")
            if not game_id:
                continue
            box = get_game_boxscore(game_id, data_mode=get_data_mode())
            all_perf.extend(item for item in box.get("items", []) if isinstance(item, dict))

        if not all_perf:
            return _fallback_performers()

        top3 = sorted(
            all_perf,
            key=lambda p: (int(p.get("points") or 0), int(p.get("rebounds") or 0)),
            reverse=True,
        )[:3]

        seed_map = {p.id: p for p in get_featured_players()}
        result: list[Player] = []
        for perf in top3:
            pid = int(perf.get("player_id") or 0)
            if pid in seed_map:
                result.append(seed_map[pid])
            elif pid:
                result.append(Player(
                    id=pid,
                    name=str(perf.get("player_name") or "Unknown"),
                    team=str(perf.get("team") or "N/A"),
                    position="N/A",
                    points=float(perf.get("points") or 0),
                    rebounds=float(perf.get("rebounds") or 0),
                    assists=float(perf.get("assists") or 0),
                    steals=float(perf.get("steals") or 0),
                    blocks=float(perf.get("blocks") or 0),
                    turnovers=float(perf.get("turnovers") or 0),
                    image_url=f"https://cdn.nba.com/headshots/nba/latest/260x190/{pid}.png",
                ))
        return result if result else _fallback_performers()
    except Exception:
        return _fallback_performers()


def _fallback_performers() -> list[Player]:
    return sorted(get_featured_players(), key=calculate_fantasy_score, reverse=True)[:3]


def render() -> None:
    render_page_header(
        "NBA FANS TAIWAN",
        "給台灣 NBA 球迷的互動資料平台 · Spurs inspired dashboard",
    )

    data_mode = get_data_mode()
    phase_value = get_season_phase(data_mode)
    phase = SeasonPhase(phase_value)

    from services.season_service import get_current_season
    season = get_current_season()

    matchup_count = len(get_seed_matchups())
    render_kpi_strip([
        ("賽季", season, phase.label()),
        ("Matchup", str(matchup_count), "5v5 陣容辯論"),
        ("資料來源", "API + Seed", "雙模式 fallback"),
    ])

    _render_season_status(phase, data_mode)

    render_section("今日焦點")
    players = _get_todays_top_performers()
    if players:
        columns = st.columns(len(players))
        for column, player in zip(columns, players, strict=True):
            with column:
                render_player_card(player)

    render_section("功能地圖")
    row1 = st.columns(3)
    with row1[0]:
        render_feature_card("球員百科", "搜尋球員、近年 per-game 數據、雷達圖與互動折線。")
    with row1[1]:
        render_feature_card("即時資訊牆", "近期 NBA 賽程與比分卡片化呈現，API 失效時 fallback。")
    with row1[2]:
        render_feature_card("球迷投票", "MVP / 總冠軍 / 單場預測，donut 圖即時統計，支援雲端模式。")

    row2 = st.columns(3)
    with row2[0]:
        render_feature_card("Fantasy Team", "30+ 球員池、Salary Cap 100、位置規則檢查、進度環顯示。")
    with row2[1]:
        render_feature_card("Matchup Debate", "5v5 VS 區塊、Plotly 對比圖、模型結果 vs 球迷投票對照。")
    with row2[2]:
        render_feature_card("Spurs Dashboard", "黑、銀、白卡片化視覺，Plotly 深色圖表，無使用官方 logo。")


def _render_season_status(phase: SeasonPhase, data_mode: str) -> None:
    render_section("比賽狀況")

    if phase in (SeasonPhase.PLAYOFFS, SeasonPhase.PLAY_IN):
        series_list = get_playoff_series(data_mode)
        if not series_list:
            st.info("目前尚無季後賽資料。")
            return
        _render_bracket(series_list)
    elif phase == SeasonPhase.REGULAR_SEASON:
        standings = get_standings(data_mode)
        _render_standings(standings)
    else:
        st.info("🏖️ 目前為休賽季，靜待新球季開幕。")


def _render_bracket(series_list: list[dict[str, Any]]) -> None:
    rounds: dict[int, list[dict[str, Any]]] = {}
    for s in series_list:
        rnd = s.get("round_num", 0)
        rounds.setdefault(rnd, []).append(s)

    round_labels = {1: "第一輪", 2: "分區準決賽", 3: "分區決賽", 4: "NBA Finals"}

    def _is_round_active(series_in_round: list[dict[str, Any]]) -> bool:
        return any(s.get("status") != "finished" for s in series_in_round)

    sorted_rounds = sorted(rounds.keys())
    active_rounds = sorted([r for r in sorted_rounds if _is_round_active(rounds[r])], reverse=True)
    completed_rounds = sorted([r for r in sorted_rounds if not _is_round_active(rounds[r])], reverse=True)

    for rnd in active_rounds:
        label = round_labels.get(rnd, f"第{rnd}輪")
        st.markdown(f"#### {label}")
        _render_round_content(rounds[rnd])

    for rnd in completed_rounds:
        with st.expander(f"查看第{rnd}輪比賽結果"):
            _render_round_content(rounds[rnd])


def _render_round_content(series_in_round: list[dict[str, Any]]) -> None:
    finals = [s for s in series_in_round if s.get("conference") == "Finals"]
    conf_series = [s for s in series_in_round if s.get("conference") != "Finals"]

    if finals:
        for s in finals:
            _render_series_card(s, width="full")
    else:
        east = [s for s in conf_series if s.get("conference") == "East"]
        west = [s for s in conf_series if s.get("conference") == "West"]
        col_e, col_w = st.columns(2)
        with col_e:
            if east:
                st.caption("🏀 東區")
                for s in east:
                    _render_series_card(s)
        with col_w:
            if west:
                st.caption("🏀 西區")
                for s in west:
                    _render_series_card(s)


def _render_series_card(series: dict[str, Any], width: str = "normal") -> None:
    team_a = series["team_a"]
    team_b = series["team_b"]
    wins_a = series["wins_a"]
    wins_b = series["wins_b"]
    status = series["status"]
    winner = series.get("winner")

    if status == "finished":
        status_icon = "✅"
        status_text = f"系列賽結束・{winner} 晉級"
    else:
        status_icon = "🔴"
        status_text = "進行中"

    a_bold = "**" if winner == team_a or (not winner and wins_a >= wins_b) else ""
    b_bold = "**" if winner == team_b or (not winner and wins_b > wins_a) else ""

    st.markdown(
        f"""
        <div style="background:#1a1a2e;border:1px solid #2d2d44;border-radius:8px;padding:12px 16px;margin-bottom:8px;">
            <div style="font-size:0.75em;color:#7E8A97;margin-bottom:6px;">{status_icon} {status_text}</div>
            <div style="display:grid;grid-template-columns:1fr auto 1fr;align-items:center;gap:0.5rem;">
                <div style="font-size:0.95em;color:#{'C4CED4' if winner == team_b else 'E8E8E8'};">{team_a}</div>
                <div style="font-size:1.3em;font-weight:bold;color:#C4CED4;letter-spacing:4px;text-align:center;">{wins_a} – {wins_b}</div>
                <div style="font-size:0.95em;color:#{'C4CED4' if winner == team_a else 'E8E8E8'};text-align:right;">{team_b}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_standings(standings: dict[str, list[dict[str, Any]]]) -> None:
    col_e, col_w = st.columns(2)

    for col, conf_name, label in [
        (col_e, "East", "🏀 東區"),
        (col_w, "West", "🏀 西區"),
    ]:
        with col:
            st.caption(label)
            teams = standings.get(conf_name, [])
            if not teams:
                st.info("暫無排名資料。")
                continue
            for t in teams:
                playoff_marker = "🟢 " if t["rank"] <= 6 else ("🟡 " if t["rank"] <= 8 else "⚫ ")
                st.markdown(
                    f"<div style='display:flex;justify-content:space-between;padding:4px 0;border-bottom:1px solid #2d2d44;'>"
                    f"<span style='color:#C4CED4'>{t['rank']}. {playoff_marker}{t['team']}</span>"
                    f"<span style='color:#7E8A97;font-size:0.9em'>{t['wins']}-{t['losses']}</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )
