from __future__ import annotations

import streamlit as st

from config.settings import get_admin_password
from database.seed_data import get_seed_matchups
from models.player import Player
from services.game_service import (
    calculate_team_averages,
    delete_custom_matchup,
    get_all_matchup_vote_counts,
    get_custom_matchups,
    get_matchup_creator,
    get_matchup_explanation,
    get_matchup_selected_side,
    get_matchup_vote_summary,
    has_voted_matchup,
    save_custom_matchup,
    simulate_matchup,
    submit_matchup_vote,
    validate_matchup_lineup,
)
from services.player_service import get_featured_players, get_searchable_players
from ui.charts import team_compare_bar, vote_donut_chart
from ui.components import (
    render_page_header,
    render_player_card,
    render_section,
    render_vs_block,
)


def render() -> None:
    render_page_header(
        "Matchup Debate",
        "5v5 陣容辯論：比較兩組陣容的數據特性，查看簡化模型結果，並投票支持你認為會贏的一方。",
    )

    all_players = get_featured_players()

    with st.expander("＋ 建立自訂對決"):
        _render_create_form(all_players)

    custom_matchup_list = get_custom_matchups()
    matchups = get_seed_matchups() + custom_matchup_list
    custom_ids = {str(m["id"]) for m in custom_matchup_list}
    vote_counts = get_all_matchup_vote_counts()

    _render_popular_section(matchups, vote_counts)

    if len(matchups) > 1:
        titles = [str(m["title"]) for m in matchups]
        selected_title = st.selectbox("請選擇有興趣的對決組合", titles)
        matchup = next(m for m in matchups if str(m["title"]) == selected_title)
    else:
        matchup = matchups[0]
    is_custom = str(matchup["id"]) in custom_ids
    render_section(str(matchup["title"]))
    player_map = {player.name: player for player in all_players}
    team_a = _resolve_players(matchup["team_a_players"], player_map)
    team_b = _resolve_players(matchup["team_b_players"], player_map)
    lineup_errors = validate_matchup_lineup(team_a, team_b)

    team_a_name = str(matchup["team_a_name"])
    team_b_name = str(matchup["team_b_name"])

    if lineup_errors:
        for error in lineup_errors:
            st.error(error)
        st.warning("請先修正 seed matchup 陣容後再進行模型模擬與投票。")
        _render_team_cards(team_a, team_b, team_a_name, team_b_name)
        return

    simulation = simulate_matchup(team_a, team_b)
    render_vs_block(
        team_a_name,
        team_b_name,
        float(simulation["team_a_win_rate"]),
        float(simulation["team_b_win_rate"]),
        winner_side="A" if simulation["winner"] == "Team A" else "B",
    )
    st.caption(simulation["reason"])

    # ── Tabs：陣容卡 / 數據對比 / 球迷投票 ────────────
    tab_lineup, tab_compare, tab_vote = st.tabs(["陣容卡片", "數據對比", "球迷投票"])

    with tab_lineup:
        _render_team_cards(team_a, team_b, team_a_name, team_b_name)

    with tab_compare:
        _render_compare(team_a, team_b, team_a_name, team_b_name)
        with st.expander("模型公式", expanded=False):
            st.code(get_matchup_explanation(), language="text")

    with tab_vote:
        _render_vote_panel(str(matchup["id"]), team_a_name, team_b_name, is_custom)

    st.divider()
    with st.expander("🔑 管理員模式"):
        _render_admin_panel(custom_matchup_list)


def _render_team_cards(team_a: list[Player], team_b: list[Player], team_a_name: str, team_b_name: str) -> None:
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown(f"#### {team_a_name}")
        for player in team_a:
            render_player_card(player, team_side="blue")
    with col_b:
        st.markdown(f"#### {team_b_name}")
        for player in team_b:
            render_player_card(player, team_side="red")


def _render_compare(team_a: list[Player], team_b: list[Player], team_a_name: str, team_b_name: str) -> None:
    avg_a = calculate_team_averages(team_a)
    avg_b = calculate_team_averages(team_b)
    labels = ["PTS", "REB", "AST", "STL", "BLK"]
    keys = ["points", "rebounds", "assists", "steals", "blocks"]
    fig = team_compare_bar(
        team_a_name,
        team_b_name,
        [avg_a[k] for k in keys],
        [avg_b[k] for k in keys],
        labels,
    )
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})


def _render_vote_panel(matchup_id: str, team_a_name: str, team_b_name: str, is_custom: bool = False) -> None:
    # Show vote summary publicly
    summary = get_matchup_vote_summary(matchup_id)
    total = summary["A"] + summary["B"]
    if total == 0:
        st.info("目前尚無 matchup 投票。")
    else:
        fig = vote_donut_chart([team_a_name, team_b_name], [summary["A"], summary["B"]])
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    user = st.session_state.get("logged_in_user")
    voter_id = user["nickname"] if user else ""

    if not voter_id:
        st.info("登入後即可投票。")
        if st.button("前往登入/註冊", key=f"matchup_go_login_{matchup_id}", type="primary"):
            st.session_state["main_nav"] = "登入/註冊"
            st.rerun()
        return

    already_voted = has_voted_matchup(matchup_id, voter_id)
    selected_side = get_matchup_selected_side(matchup_id, voter_id)

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button(f"支持 {team_a_name}", disabled=already_voted, use_container_width=True):
            _submit_vote(matchup_id, voter_id, "A")
    with col_b:
        if st.button(f"支持 {team_b_name}", disabled=already_voted, use_container_width=True):
            _submit_vote(matchup_id, voter_id, "B")

    if already_voted:
        voted_name = team_a_name if selected_side == "A" else team_b_name
        st.success(f"你已投票：{voted_name}")

    if is_custom:
        creator_id = get_matchup_creator(matchup_id)
        if creator_id and voter_id.strip().lower() == creator_id.strip().lower():
            st.divider()
            with st.expander("⚠️ 刪除此對決（建立者專屬）"):
                st.warning("刪除後無法恢復，所有投票紀錄也會一併清除。")
                if st.button("確認刪除", key=f"creator_del_{matchup_id}"):
                    delete_custom_matchup(matchup_id)
                    st.rerun()


def _submit_vote(matchup_id: str, voter_id: str, selected_side: str) -> None:
    if submit_matchup_vote(matchup_id, voter_id, selected_side):
        st.success("投票成功")
        st.rerun()
    else:
        st.error("投票失敗，請確認暱稱，或你是否已投過票。")


def _render_create_form(seed_players: list[Player]) -> None:
    user = st.session_state.get("logged_in_user")
    if not user:
        st.info("登入後即可建立自訂對決。")
        if st.button("前往登入/註冊", key="debate_create_go_login", type="primary"):
            st.session_state["main_nav"] = "登入/註冊"
            st.rerun()
        return

    creator_id = user["nickname"]

    if "cm_created_msg" in st.session_state:
        st.success(st.session_state.pop("cm_created_msg"))

    st.caption(f"建立者：**{creator_id}**（使用登入帳號的暱稱）")
    title = st.text_input("對決標題", placeholder="例如：Knicks vs Cavaliers Finals", key="cm_title")
    col_a, col_b = st.columns(2)

    with col_a:
        team_a_name = st.text_input("藍隊名稱", placeholder="例如：Knicks", key="cm_a_name")
        search_a = st.text_input("搜尋球員", placeholder="輸入姓名搜尋所有球員", key="cm_search_a")
        opts_a = _matchup_player_options(seed_players, search_a, st.session_state.get("cm_a_players", []))
        team_a_players: list[str] = st.multiselect("藍隊球員（1–5 人）", opts_a, max_selections=5, key="cm_a_players")

    with col_b:
        team_b_name = st.text_input("紅隊名稱", placeholder="例如：Cavaliers", key="cm_b_name")
        search_b = st.text_input("搜尋球員", placeholder="輸入姓名搜尋所有球員", key="cm_search_b")
        opts_b = _matchup_player_options(seed_players, search_b, st.session_state.get("cm_b_players", []))
        team_b_players: list[str] = st.multiselect("紅隊球員（1–5 人）", opts_b, max_selections=5, key="cm_b_players")

    if st.button("建立對決", use_container_width=True, key="cm_submit"):
        errors: list[str] = []
        if not title.strip():
            errors.append("請輸入對決標題。")
        if not team_a_name.strip():
            errors.append("請輸入藍隊名稱。")
        if not team_b_name.strip():
            errors.append("請輸入紅隊名稱。")
        if not (1 <= len(team_a_players) <= 5):
            errors.append(f"藍隊請選 1–5 名球員（目前 {len(team_a_players)} 名）。")
        if not (1 <= len(team_b_players) <= 5):
            errors.append(f"紅隊請選 1–5 名球員（目前 {len(team_b_players)} 名）。")
        if 1 <= len(team_a_players) <= 5 and 1 <= len(team_b_players) <= 5 and len(team_a_players) != len(team_b_players):
            errors.append(f"兩隊人數必須相等（藍隊：{len(team_a_players)} 名，紅隊：{len(team_b_players)} 名）。")
        overlap = set(team_a_players) & set(team_b_players)
        if overlap:
            errors.append(f"兩隊不能有相同球員：{', '.join(overlap)}。")
        if not errors and title.strip():
            existing_titles = {str(m["title"]) for m in get_seed_matchups() + get_custom_matchups()}
            if title.strip() in existing_titles:
                errors.append(f"對決標題「{title.strip()}」已存在，請使用不同名稱。")
        if errors:
            for e in errors:
                st.error(e)
        else:
            save_custom_matchup(title, team_a_name, team_b_name, team_a_players, team_b_players, creator_id)
            st.session_state["cm_created_msg"] = f"對決「{title.strip()}」已建立！"
            for k in ["cm_title", "cm_a_name", "cm_b_name", "cm_search_a", "cm_search_b", "cm_a_players", "cm_b_players"]:
                st.session_state.pop(k, None)
            st.rerun()


def _matchup_player_options(seed_players: list[Player], keyword: str, selected: list[str]) -> list[str]:
    """Build multiselect options: seed+API results merged, always including currently-selected names."""
    if keyword:
        found = get_searchable_players(keyword)
        names = list(dict.fromkeys([p.name for p in found]))
    else:
        names = [p.name for p in seed_players]
    # Prepend currently-selected so they're never dropped from options
    return list(dict.fromkeys(selected + names))


def _render_admin_panel(custom_matchups: list[dict]) -> None:
    if not st.session_state.get("is_admin"):
        pwd = st.text_input("輸入管理員密碼", type="password", key="admin_pwd_input")
        if st.button("解鎖", key="admin_unlock"):
            if pwd == get_admin_password():
                st.session_state["is_admin"] = True
                st.rerun()
            else:
                st.error("密碼錯誤。")
        return

    col_status, col_logout = st.columns([5, 1])
    col_status.success("管理員模式已解鎖")
    if col_logout.button("登出", key="admin_logout"):
        del st.session_state["is_admin"]
        st.rerun()

    if not custom_matchups:
        st.info("目前沒有自訂對決。")
        return

    for m in custom_matchups:
        creator = m.get("creator_id") or "（未設定）"
        col_info, col_del = st.columns([6, 1])
        col_info.markdown(f"**{m['title']}** — {m['team_a_name']} vs {m['team_b_name']} · 建立者：*{creator}*")
        if col_del.button("🗑️", key=f"admin_del_{m['id']}", help=f"刪除「{m['title']}」"):
            delete_custom_matchup(str(m["id"]))
            st.rerun()


def _render_popular_section(matchups: list[dict], vote_counts: dict[str, int]) -> None:
    voted = sorted(
        [(m, vote_counts.get(str(m["id"]), 0)) for m in matchups if vote_counts.get(str(m["id"]), 0) > 0],
        key=lambda x: x[1],
        reverse=True,
    )
    if not voted:
        return

    render_section("熱門對決")
    medals = ["🥇", "🥈", "🥉"]
    for idx, (m, count) in enumerate(voted[:5]):
        rank = medals[idx] if idx < 3 else f"#{idx + 1}"
        c_rank, c_info, c_count = st.columns([1, 6, 2])
        c_rank.markdown(f"## {rank}")
        c_info.markdown(f"**{m['title']}**  \n{m['team_a_name']} vs {m['team_b_name']}")
        c_count.markdown(f"**{count}** 票")
    st.divider()


def _resolve_players(player_names: list[str], player_map: dict[str, Player]) -> list[Player]:
    result = []
    for name in player_names:
        if name in player_map:
            result.append(player_map[name])
        else:
            result.append(Player(
                id=abs(hash(name)) % 10_000_000,
                name=name, team="N/A", position="N/A",
                points=0.0, rebounds=0.0, assists=0.0,
                steals=0.0, blocks=0.0, turnovers=0.0,
                image_url=None,
            ))
    return result
