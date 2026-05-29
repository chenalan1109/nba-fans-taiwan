from __future__ import annotations

import pandas as pd
import streamlit as st

from models.player import Player
from services.game_service import (
    calculate_player_salary,
    calculate_team_averages,
    calculate_team_score,
    calculate_total_salary,
    save_fantasy_team,
    validate_fantasy_roster,
)
from services.player_service import calculate_fantasy_score, get_player_pool, get_searchable_players
from ui.components import (
    render_kpi_strip,
    render_page_header,
    render_player_card,
    render_progress_ring,
    render_section,
    render_stat_card,
)

_CAP_MODES: dict[str, float | None] = {
    "無上限": None,
    "上限 50": 50.0,
    "上限 30": 30.0,
}


def render() -> None:
    render_page_header(
        "Fantasy Team",
        "從 30+ 名球員池中組出 5 人陣容，同位置最多 3 名。",
    )

    all_players = get_player_pool()
    teams = sorted({p.team for p in all_players})
    positions = ["PG", "SG", "SF", "PF", "C"]

    cap_mode = st.radio(
        "薪資上限模式",
        list(_CAP_MODES.keys()),
        index=1,
        horizontal=True,
    )
    salary_cap: float | None = _CAP_MODES[cap_mode]

    cap_kpi = "∞" if salary_cap is None else f"{salary_cap:.0f}"
    cap_sub = "無限制" if salary_cap is None else "總薪資上限"
    render_kpi_strip([
        ("球員池", str(len(all_players)), "可選球員"),
        ("Salary Cap", cap_kpi, cap_sub),
        ("陣容大小", "5", "必選人數"),
        ("位置規則", "≤ 3", "同位置上限"),
    ])

    # ── 篩選 ────────────────────────
    render_section("篩選球員池")
    col_kw, col_team, col_pos = st.columns(3)
    keyword = col_kw.text_input("搜尋姓名", placeholder="例如 Curry")
    selected_team = col_team.selectbox("球隊", ["全部"] + teams)
    selected_pos = col_pos.selectbox("位置", ["全部"] + positions)

    filtered_players = get_player_pool(
        keyword=keyword,
        team="" if selected_team == "全部" else selected_team,
        position="" if selected_pos == "全部" else selected_pos,
    )

    render_section(f"球員池（{len(filtered_players)} 名）")
    if not filtered_players:
        st.info("找不到符合條件的球員，請調整篩選條件。")
    else:
        tab_cards, tab_table = st.tabs(["卡片檢視", "完整表格"])
        with tab_cards:
            _render_pool_cards(filtered_players)
        with tab_table:
            _render_pool_table(filtered_players)

    st.divider()

    # ── 選人 ────────────────────────
    render_section("組建陣容")
    col_owner, col_team_name = st.columns(2)
    owner_name = col_owner.text_input(
        "隊伍擁有者",
        value=st.session_state.get("fantasy_owner", ""),
        placeholder="例如 Maurice",
    ).strip()
    team_name = col_team_name.text_input(
        "隊伍名稱",
        value=st.session_state.get("fantasy_team_name", ""),
        placeholder="例如 Taipei Shooters",
    ).strip()
    st.session_state["fantasy_owner"] = owner_name
    st.session_state["fantasy_team_name"] = team_name

    select_search = st.text_input(
        "搜尋球員",
        placeholder="輸入姓名可搜尋所有 NBA 球員，例如 Curry",
        key="fantasy_select_search",
        help="不限定球員池，可搜尋任何球員。非球員池球員 stats 顯示為 0。",
    )
    select_pool = get_searchable_players(select_search) if select_search else all_players
    # Always keep currently-selected players in options to prevent them being dropped
    current_keys: list[str] = st.session_state.get("fantasy_selected_names", [])
    select_map = {p.name: p for p in select_pool}
    for p in all_players:
        if p.name in current_keys:
            select_map[p.name] = p
    selected_names = st.multiselect(
        "選擇球員加入陣容（最多 5 人）",
        list(select_map.keys()),
        max_selections=5,
        key="fantasy_selected_names",
        help="搜尋後選擇，或直接從下拉選單挑選。",
    )
    selected_players = [select_map[name] for name in selected_names if name in select_map]

    if selected_players:
        render_section(f"已選球員（{len(selected_players)} / 5）")
        _render_selected_cards(selected_players)
        total_salary = calculate_total_salary(selected_players)
        if salary_cap is not None:
            render_progress_ring(
                total_salary / salary_cap,
                "SALARY 使用率",
                f"{total_salary:.1f} / {salary_cap:.0f}",
                "超過 85% 進入吃緊，超過 100% 違規",
            )
        else:
            render_progress_ring(
                0.0,
                "SALARY 使用率",
                f"{total_salary:.1f} / ∞",
                "目前為無上限模式",
            )

    roster_errors = validate_fantasy_roster(selected_players, salary_cap) if selected_players else []
    for err in roster_errors:
        st.warning(err)

    if len(selected_players) != 5:
        st.info("請選滿 5 名球員後計算與儲存隊伍。")
        return

    if roster_errors:
        st.error("陣容不符合規則，請調整後再儲存。")
        return

    # ── 隊伍數據 ─────────────────────
    total_score = calculate_team_score(selected_players)
    total_salary = calculate_total_salary(selected_players)
    averages = calculate_team_averages(selected_players)

    render_section("隊伍數據")
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        render_stat_card("Fantasy 總分", f"{total_score:.1f}", "5 人加總", accent="silver")
    with c2:
        cap_label = "無上限" if salary_cap is None else f"上限 {salary_cap:.0f}"
        render_stat_card("總 Salary", f"{total_salary:.1f}", cap_label, accent="blue")
    with c3:
        render_stat_card("平均得分", f"{averages['points']:.1f}", "PPG", accent="silver")
    with c4:
        render_stat_card("平均籃板", f"{averages['rebounds']:.1f}", "RPG", accent="silver")
    with c5:
        render_stat_card("平均助攻", f"{averages['assists']:.1f}", "APG", accent="green")

    if st.button("儲存 Fantasy Team", disabled=not owner_name or not team_name, use_container_width=True):
        try:
            team_id = save_fantasy_team(owner_name, team_name, selected_players)
            st.success(f"已儲存 Fantasy Team #{team_id}！")
        except ValueError as exc:
            st.error(str(exc))


def _render_pool_cards(players: list[Player]) -> None:
    """以 3 欄 grid 渲染球員卡。"""
    cols_per_row = 3
    for i in range(0, len(players), cols_per_row):
        row = players[i:i + cols_per_row]
        columns = st.columns(cols_per_row)
        for col, player in zip(columns, row, strict=False):
            with col:
                render_player_card(
                    player,
                    fantasy_score=calculate_fantasy_score(player),
                    salary=calculate_player_salary(player),
                )


def _render_selected_cards(players: list[Player]) -> None:
    cols_per_row = 5
    columns = st.columns(cols_per_row)
    for col, player in zip(columns, players, strict=False):
        with col:
            render_player_card(
                player,
                fantasy_score=calculate_fantasy_score(player),
                salary=calculate_player_salary(player),
            )


def _render_pool_table(players: list[Player]) -> None:
    rows = [
        {
            "球員": p.name,
            "隊伍": p.team,
            "位置": p.position,
            "PTS": p.points,
            "REB": p.rebounds,
            "AST": p.assists,
            "STL": p.steals,
            "BLK": p.blocks,
            "TOV": p.turnovers,
            "Fantasy 分": round(calculate_fantasy_score(p), 1),
            "Salary": calculate_player_salary(p),
        }
        for p in players
    ]
    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Salary": st.column_config.NumberColumn("Salary", format="%.1f"),
            "Fantasy 分": st.column_config.NumberColumn("Fantasy 分", format="%.1f"),
        },
    )
