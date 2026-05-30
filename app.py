from __future__ import annotations

import streamlit as st

from config.settings import get_runtime_settings
from database.db import init_db
from _pages import fantasy_team, home, matchup_debate, player_stats, realtime_hub, voting
from services import prophet_service as ps
from services.nba_api_service import get_data_mode
from ui.theme import inject_global_styles


PAGES = {
    "首頁": home.render,
    "即時資訊牆": realtime_hub.render,
    "球員百科": player_stats.render,
    "球迷投票": voting.render,
    "Fantasy Team": fantasy_team.render,
    "Matchup Debate": matchup_debate.render,
}


def initialize_app() -> None:
    if "db_initialized" not in st.session_state:
        init_db()
        st.session_state["db_initialized"] = True


def main() -> None:
    st.set_page_config(
        page_title="NBA FANS TAIWAN",
        page_icon="basketball",
        layout="wide",
    )
    initialize_app()
    inject_global_styles()

    with st.sidebar:
        runtime_settings = get_runtime_settings()
        st.title("NBA FANS TAIWAN")
        st.caption("Spurs inspired · 黑銀視覺")

        user = st.session_state.get("logged_in_user")
        if user:
            nickname = user["nickname"]
            prophet_user = ps.get_or_create_user(nickname)
            st.markdown(f"👤 **{user['username']}**")
            st.caption(f"暱稱：{nickname}　💰 {prophet_user['coins']} 先知幣")
            if st.button("登出", key="sidebar_logout"):
                st.session_state.pop("logged_in_user", None)
                st.session_state.pop("voter_id", None)
                st.rerun()
        else:
            st.caption("尚未登入，請前往「球迷投票」登入。")

        st.divider()
        selected_page = st.radio("功能選單", list(PAGES.keys()))
        st.divider()
        st.caption(f"Milestone 10 | data mode: {get_data_mode()}")
        st.caption(f"app mode: {runtime_settings.app_mode}")
        st.caption(f"database: {runtime_settings.database_label}")

    PAGES[selected_page]()


if __name__ == "__main__":
    main()
