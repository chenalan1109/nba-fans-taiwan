from __future__ import annotations

import hashlib
from typing import Any

import pandas as pd
import streamlit as st

from services.auth_service import is_admin_user
from services.cached import get_game_boxscore, get_game_officials, get_recent_games, get_scoreboard
from services.comment_service import (
    add_comment,
    delete_comment,
    get_comments,
    has_liked_comment,
    like_comment,
    unlike_comment,
)
from services.nba_api_service import get_data_mode
from services.rating_service import (
    get_player_rating,
    get_ratings_for_players,
    has_rated_player,
    submit_player_rating,
)
from ui.components import (
    render_game_card,
    render_kpi_strip,
    render_page_header,
    render_section,
    render_source_badge,
)

_BOXSCORE_COLS = {
    "player_name": "球員",
    "minutes": "上場時間",
    "points": "得分",
    "rebounds": "籃板",
    "assists": "助攻",
    "steals": "抄截",
    "blocks": "火鍋",
    "fg_pct": "FG%",
    "fg3_pct": "3P%",
    "turnovers": "失誤",
}


_STARS = ["⭐", "⭐⭐", "⭐⭐⭐", "⭐⭐⭐⭐", "⭐⭐⭐⭐⭐"]
_STAR_MAP = {s: i + 1 for i, s in enumerate(_STARS)}


def _referee_id(game_id: str, name: str) -> int:
    """Stable integer ID for a referee in a specific game (never collides with NBA player IDs)."""
    digest = hashlib.md5(f"ref:{game_id}:{name}".encode()).hexdigest()
    return int(digest[:8], 16) + 10**9


def render() -> None:
    render_page_header("即時資訊牆", "近期 NBA 賽程與比分卡片化呈現，API 失效時自動 fallback 展示資料。")

    tab_today, tab_recent = st.tabs(["今日賽程", "近期比賽"])

    with tab_today:
        scoreboard = get_scoreboard(data_mode=get_data_mode())
        render_source_badge(str(scoreboard.get("source") or ""))
        _render_game_section(scoreboard["items"], "今日賽程", "today")

    with tab_recent:
        recent_data = get_recent_games(data_mode=get_data_mode())
        render_source_badge(str(recent_data.get("source") or ""))
        _render_game_section(recent_data["items"], "最近 7 天", "recent")


def _render_game_section(games: list[dict[str, Any]], kpi_sub: str, section: str = "") -> None:
    if not games:
        st.info("目前沒有可顯示的賽程資料。")
        return

    finals = sum(1 for g in games if str(g.get("status", "")).lower() == "final")
    render_kpi_strip([
        ("賽事總數", str(len(games)), kpi_sub),
        ("已完賽", str(finals), "Final"),
        ("進行中 / 未開賽", str(len(games) - finals), "Live / Upcoming"),
    ])

    render_section("賽程卡片")
    for game in games:
        render_game_card(
            home_team=str(game.get("home_team", "")),
            away_team=str(game.get("away_team", "")),
            home_score=int(game.get("home_score", 0) or 0),
            away_score=int(game.get("away_score", 0) or 0),
            status=str(game.get("status", "")),
        )
        _render_boxscore_expander(game, section)
        _render_comment_expander(game, section)


def _render_boxscore_expander(game: dict[str, object], section: str = "") -> None:
    game_id = str(game.get("game_id") or "")
    status = str(game.get("status") or "")
    home_team = str(game.get("home_team") or "主隊")
    away_team = str(game.get("away_team") or "客隊")

    if status.lower() == "scheduled" and not game_id.startswith("seed"):
        return

    label = "查看球員數據"
    with st.expander(label, expanded=False):
        if not game_id:
            st.info("此場比賽暫無球員數據。")
            return

        boxscore = get_game_boxscore(game_id, data_mode=get_data_mode())
        players = boxscore.get("items", [])

        if not players:
            st.info("球員數據尚未取得，請稍後再試。")
            return

        home_players = [p for p in players if p.get("side") == "home"]
        away_players = [p for p in players if p.get("side") == "away"]

        tab_home, tab_away = st.tabs([f"🏠 {home_team}", f"✈️ {away_team}"])
        with tab_home:
            _render_player_table(home_players, game_id, "home", section)
        with tab_away:
            _render_player_table(away_players, game_id, "away", section)

        st.divider()
        _render_referee_vote_section(game_id, home_team, away_team, section)


def _render_player_table(players: list[dict[str, Any]], game_id: str = "", side: str = "", section: str = "") -> None:
    if not players:
        st.info("暫無球員數據。")
        return
    rows = [{_BOXSCORE_COLS[k]: v for k, v in p.items() if k in _BOXSCORE_COLS} for p in players]
    df = pd.DataFrame(rows)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "FG%": st.column_config.NumberColumn("FG%", format="%.1f%%"),
            "3P%": st.column_config.NumberColumn("3P%", format="%.1f%%"),
        },
    )
    _render_rating_section(players, game_id, side, section)


def _render_rating_section(players: list[dict[str, Any]], game_id: str = "", side: str = "", section: str = "") -> None:
    st.divider()
    render_section("球員評分")

    base_scope = f"{game_id}_{side}" if game_id else "_".join(str(p.get("player_id", 0)) for p in players)
    scope = f"{section}_{base_scope}" if section else base_scope
    logged_user = st.session_state.get("logged_in_user")
    voter_id = logged_user["nickname"] if logged_user else ""

    player_ids = [int(p.get("player_id") or 0) for p in players if p.get("player_id")]
    ratings_map = get_ratings_for_players(player_ids)

    st.markdown(
        """
        <style>
        div[data-testid="stRadio"] > div[role="radiogroup"] {
            flex-wrap: nowrap;
            gap: 0.15rem;
        }
        div[data-testid="stRadio"] > div[role="radiogroup"] label {
            font-size: 1.15rem;
            padding: 0.15rem 0.35rem;
            border-radius: 6px;
            transition: background 0.15s;
        }
        div[data-testid="stRadio"] > div[role="radiogroup"] label:hover {
            background: rgba(196,206,212,0.12);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    for player in players:
        pid = int(player.get("player_id") or 0)
        if not pid:
            continue
        name = str(player.get("player_name") or "")
        avg_info = ratings_map.get(pid)
        avg_str = f"⭐ {avg_info['avg']:.1f}（{avg_info['count']} 人評分）" if avg_info else "尚無評分"

        col_name, col_avg = st.columns([4, 3])
        col_name.markdown(f"**{name}**")
        col_avg.markdown(
            f"<div style='text-align:right;color:#7E8A97;font-size:0.85em;padding-top:4px'>{avg_str}</div>",
            unsafe_allow_html=True,
        )

        if not voter_id:
            continue

        already_rated = has_rated_player(pid, voter_id)
        if already_rated:
            my_rating = get_player_rating(pid, voter_id)
            stars = _STARS[(my_rating or 1) - 1]
            st.markdown(
                f"<p style='color:#C4CED4;font-size:0.9em;margin:2px 0 10px'>你已給 {stars}</p>",
                unsafe_allow_html=True,
            )
        else:
            col_stars, col_btn = st.columns([7, 1])
            with col_stars:
                choice = st.radio(
                    "評分",
                    _STARS,
                    index=2,
                    key=f"rate_{scope}_{pid}",
                    horizontal=True,
                    label_visibility="collapsed",
                )
            with col_btn:
                st.write("")
                if st.button("送出", key=f"rate_btn_{scope}_{pid}"):
                    rating_val = _STAR_MAP.get(str(choice), 3)
                    if submit_player_rating(pid, voter_id, rating_val):
                        st.success("評分成功！")
                        st.rerun()
                    else:
                        st.error("評分失敗，請確認暱稱是否已評分過此球員。")

    if not voter_id:
        st.info("登入後即可為球員評分。")
        if st.button("前往登入/註冊", key=f"go_login_rate_{scope}", type="primary"):
            st.session_state["main_nav"] = "登入/註冊"
            st.rerun()


def _render_referee_vote_section(game_id: str, home_team: str, away_team: str, section: str = "") -> None:
    render_section("裁判執法評分")
    st.caption("針對這場比賽的裁判評分，同一帳號對同一裁判只能評分一次。")

    officials = get_game_officials(game_id, data_mode=get_data_mode())
    if not officials:
        st.info("裁判資料尚無法取得，請稍後再試。")
        return

    logged_user = st.session_state.get("logged_in_user")
    voter_id = logged_user["nickname"] if logged_user else ""

    ref_ids = [_referee_id(game_id, o["name"]) for o in officials]
    ratings_map = get_ratings_for_players(ref_ids)

    pfx = f"{section}_" if section else ""

    for official, rid in zip(officials, ref_ids):
        name = official["name"]
        jersey = official.get("jersey_num", "")
        display_name = f"{name} #{jersey}" if jersey else name

        avg_info = ratings_map.get(rid)
        avg_str = f"⭐ {avg_info['avg']:.1f}（{avg_info['count']} 人評分）" if avg_info else "尚無評分"

        col_name, col_avg = st.columns([4, 3])
        col_name.markdown(f"**{display_name}**")
        col_avg.markdown(
            f"<div style='text-align:right;color:#7E8A97;font-size:0.85em;padding-top:4px'>{avg_str}</div>",
            unsafe_allow_html=True,
        )

        if not voter_id:
            continue

        already_rated = has_rated_player(rid, voter_id)
        if already_rated:
            my_rating = get_player_rating(rid, voter_id)
            stars = _STARS[(my_rating or 1) - 1]
            st.markdown(
                f"<p style='color:#C4CED4;font-size:0.9em;margin:2px 0 10px'>你已給 {stars}</p>",
                unsafe_allow_html=True,
            )
        else:
            col_stars, col_btn = st.columns([7, 1])
            with col_stars:
                choice = st.radio(
                    "評分",
                    _STARS,
                    index=2,
                    key=f"{pfx}ref_rate_{rid}",
                    horizontal=True,
                    label_visibility="collapsed",
                )
            with col_btn:
                st.write("")
                if st.button("送出", key=f"{pfx}ref_rate_btn_{rid}"):
                    rating_val = _STAR_MAP.get(str(choice), 3)
                    if submit_player_rating(rid, voter_id, rating_val):
                        st.success("評分成功！")
                        st.rerun()
                    else:
                        st.error("評分失敗，請確認是否已評分過此裁判。")

    if not voter_id:
        st.info("登入後即可為裁判評分。")
        if st.button("前往登入/註冊", key=f"{pfx}go_login_ref_{game_id}", type="primary"):
            st.session_state["main_nav"] = "登入/註冊"
            st.rerun()


def _render_comment_expander(game: dict[str, object], section: str = "") -> None:
    game_id = str(game.get("game_id") or "")
    if not game_id:
        return

    comments = get_comments(game_id)
    count = len(comments)
    label = f"💬 留言討論（{count}）" if count else "💬 留言討論"
    pfx = f"{section}_" if section else ""

    with st.expander(label, expanded=False):
        logged_user = st.session_state.get("logged_in_user")
        voter_id = logged_user["nickname"] if logged_user else ""

        if voter_id:
            new_comment = st.text_area(
                "留言",
                placeholder="分享你對這場比賽的想法...",
                key=f"{pfx}comment_text_{game_id}",
                height=80,
                label_visibility="collapsed",
            )
            if st.button("送出留言", key=f"{pfx}comment_btn_{game_id}"):
                content = new_comment.strip()
                if content:
                    if add_comment(game_id, voter_id, content):
                        st.rerun()
                    else:
                        st.error("留言失敗，請再試一次。")
                else:
                    st.warning("留言內容不可為空。")
        else:
            st.info("登入後即可留言與按讚。")
            if st.button("前往登入/註冊", key=f"{pfx}go_login_comment_{game_id}", type="primary"):
                st.session_state["main_nav"] = "登入/註冊"
                st.rerun()

        st.divider()

        is_admin = is_admin_user(logged_user)

        if not comments:
            st.caption("目前尚無留言，成為第一個！")
            return

        for comment in comments:
            cid = int(comment["id"])
            author = str(comment["voter_id"])
            content_text = str(comment["content"])
            like_count = int(comment["like_count"])
            ts = str(comment["created_at"])[:16]

            already_liked = has_liked_comment(cid, voter_id) if voter_id else False
            is_mine = bool(voter_id) and author == voter_id

            col_main, col_like, col_del = st.columns([8, 1, 1])

            with col_main:
                st.markdown(f"**{author}** · <span style='color:#7E8A97;font-size:0.82em'>{ts}</span>", unsafe_allow_html=True)
                st.write(content_text)

            with col_like:
                like_icon = "❤️" if already_liked else "👍"
                if st.button(
                    f"{like_icon} {like_count}",
                    key=f"{pfx}like_{game_id}_{cid}",
                    disabled=not voter_id or is_mine,
                    use_container_width=True,
                ):
                    if already_liked:
                        unlike_comment(cid, voter_id)
                    else:
                        like_comment(cid, voter_id)
                    st.rerun()

            with col_del:
                if is_mine or is_admin:
                    if st.button(
                        "🗑",
                        key=f"{pfx}del_{game_id}_{cid}",
                        use_container_width=True,
                        help="刪除留言" if is_mine else "管理員刪除",
                    ):
                        delete_comment(cid, voter_id)
                        st.rerun()

            st.divider()
