from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from models.player import Player
from services import auth_service, market_service
from services.game_service import (
    calculate_player_salary,
    calculate_team_averages,
    calculate_team_score,
    calculate_total_salary,
    save_fantasy_team,
    validate_fantasy_roster,
)
from services.player_service import calculate_fantasy_score, get_player_pool
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


def _current_user() -> dict[str, Any] | None:
    return st.session_state.get("logged_in_user")


def render() -> None:
    render_page_header(
        "Fantasy Team",
        "先在市場購買球員，加入你的球員池，再從池中組出 5 人夢幻陣容。",
    )

    user = _current_user()
    if not user:
        st.warning("請先登入帳號才能使用 Fantasy Team 功能。")
        st.info("在「球迷投票」頁面可以登入或註冊帳號。")
        return

    username: str = user["username"]
    nickname: str = user["nickname"]

    tab_market, tab_pool, tab_team = st.tabs(["🛒 球員市場", "🎒 我的球員池", "🏀 組建 Fantasy Team"])

    with tab_market:
        _render_market(username, nickname)
    with tab_pool:
        _render_pool(username, nickname)
    with tab_team:
        _render_team_builder(username, nickname)


# ── Market tab ────────────────────────────────────────────────────────────────

def _render_market(username: str, nickname: str) -> None:
    render_section("球員市場")
    coins = market_service.get_user_coins(nickname)
    owned_ids = market_service.get_user_player_pool_ids(username)
    all_players = get_player_pool()

    st.markdown(f"💰 先知幣餘額：**{coins}** 枚")
    st.caption("購買球員後，球員進入你的球員池，可用於組建 Fantasy Team。定價依球員數據計算。")

    col_kw, col_team, col_pos = st.columns(3)
    keyword = col_kw.text_input("搜尋姓名", placeholder="例如 Curry", key="mkt_kw")
    teams = sorted({p.team for p in all_players})
    positions = ["PG", "SG", "SF", "PF", "C"]
    selected_team = col_team.selectbox("球隊", ["全部"] + teams, key="mkt_team")
    selected_pos = col_pos.selectbox("位置", ["全部"] + positions, key="mkt_pos")

    filtered = get_player_pool(
        keyword=keyword,
        team="" if selected_team == "全部" else selected_team,
        position="" if selected_pos == "全部" else selected_pos,
    )

    render_section(f"可購買球員（{len(filtered)} 名）")
    cols_per_row = 3
    for i in range(0, len(filtered), cols_per_row):
        row_players = filtered[i:i + cols_per_row]
        columns = st.columns(cols_per_row)
        for col, player in zip(columns, row_players, strict=False):
            with col:
                price = market_service.get_player_price(player)
                already_owned = player.id in owned_ids
                render_player_card(
                    player,
                    fantasy_score=calculate_fantasy_score(player),
                    salary=calculate_player_salary(player),
                )
                if already_owned:
                    st.success("✓ 已擁有")
                elif st.button(
                    f"購買 {price} 先知幣",
                    key=f"buy_{player.id}",
                    use_container_width=True,
                    disabled=coins < price,
                ):
                    ok, msg = market_service.buy_player(username, nickname, player)
                    if ok:
                        st.success(msg)
                        coins = market_service.get_user_coins(nickname)
                        owned_ids = market_service.get_user_player_pool_ids(username)
                        st.rerun()
                    else:
                        st.error(msg)


# ── Pool tab ──────────────────────────────────────────────────────────────────

def _render_pool(username: str, nickname: str) -> None:
    render_section("我的球員池")
    coins = market_service.get_user_coins(nickname)
    st.markdown(f"💰 先知幣餘額：**{coins}** 枚")

    owned_ids = market_service.get_user_player_pool_ids(username)
    if not owned_ids:
        st.info("你尚未購買任何球員。前往「球員市場」購買球員加入球員池。")
        return

    all_players = get_player_pool()
    pool_players = [p for p in all_players if p.id in owned_ids]

    render_kpi_strip([
        ("球員池人數", str(len(pool_players)), "可用於組隊"),
        ("先知幣餘額", str(coins), "枚"),
    ])

    tab_cards, tab_table = st.tabs(["卡片檢視", "完整表格"])
    with tab_cards:
        _render_pool_cards(pool_players)
    with tab_table:
        _render_pool_table(pool_players)


# ── Team builder tab ──────────────────────────────────────────────────────────

def _render_team_builder(username: str, nickname: str) -> None:
    render_section("組建 Fantasy Team")

    owned_ids = market_service.get_user_player_pool_ids(username)
    if not owned_ids:
        st.warning("你的球員池是空的。請先在「球員市場」購買球員。")
        return

    all_players = get_player_pool()
    pool_players = [p for p in all_players if p.id in owned_ids]

    st.caption(f"可選球員：{len(pool_players)} 名（僅限球員池內的球員）")

    cap_mode = st.radio(
        "薪資上限模式",
        list(_CAP_MODES.keys()),
        index=1,
        horizontal=True,
    )
    salary_cap: float | None = _CAP_MODES[cap_mode]

    col_owner, col_team_name = st.columns(2)
    owner_name = col_owner.text_input(
        "隊伍擁有者",
        value=st.session_state.get("fantasy_owner", nickname),
        placeholder="例如 Maurice",
    ).strip()
    team_name = col_team_name.text_input(
        "隊伍名稱",
        value=st.session_state.get("fantasy_team_name", ""),
        placeholder="例如 Taipei Shooters",
    ).strip()
    st.session_state["fantasy_owner"] = owner_name
    st.session_state["fantasy_team_name"] = team_name

    select_map = {p.name: p for p in pool_players}
    current_keys: list[str] = st.session_state.get("fantasy_selected_names", [])
    # keep selected players in options even if filtered
    for p in pool_players:
        if p.name in current_keys:
            select_map[p.name] = p

    selected_names = st.multiselect(
        "選擇球員加入陣容（最多 5 人，僅限球員池內球員）",
        list(select_map.keys()),
        max_selections=5,
        key="fantasy_selected_names",
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
            render_progress_ring(0.0, "SALARY 使用率", f"{total_salary:.1f} / ∞", "無上限模式")

    roster_errors = validate_fantasy_roster(selected_players, salary_cap) if selected_players else []
    for err in roster_errors:
        st.warning(err)

    if len(selected_players) != 5:
        st.info("請選滿 5 名球員後計算與儲存隊伍。")
        return

    if roster_errors:
        st.error("陣容不符合規則，請調整後再儲存。")
        return

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


# ── Render helpers ─────────────────────────────────────────────────────────────

def _render_pool_cards(players: list[Player]) -> None:
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
    columns = st.columns(5)
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
            "市場價格": market_service.get_player_price(p),
        }
        for p in players
    ]
    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Fantasy 分": st.column_config.NumberColumn("Fantasy 分", format="%.1f"),
            "市場價格": st.column_config.NumberColumn("市場價格（先知幣）", format="%d"),
        },
    )
