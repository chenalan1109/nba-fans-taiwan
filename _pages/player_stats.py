from __future__ import annotations

from typing import cast

import pandas as pd
import streamlit as st

from models.player import Player
from services.cached import find_players, get_player_chart_data, get_player_detail
from services.nba_api_service import get_data_mode
from services.player_service import get_player_data_quality
from ui.charts import player_radar_chart, player_trend_chart
from ui.components import (
    render_kpi_strip,
    render_page_header,
    render_section,
    render_source_badge,
    render_stat_card,
)


def render() -> None:
    render_page_header("球員百科", "搜尋 NBA 球員，檢視近年 per-game 數據、雷達圖與資料完整度。")

    keyword = st.text_input("搜尋球員", value="Curry", placeholder="輸入球員英文姓名，例如 Curry 或 LeBron")
    search_result = find_players(keyword, data_mode=get_data_mode())
    render_source_badge(str(search_result.get("source") or ""))
    _show_data_source(search_result)

    players = search_result["items"]
    if not players:
        st.warning("查無球員資料，請嘗試其他關鍵字。")
        return

    player_options = {player.name: player for player in players if isinstance(player, Player)}
    if not player_options:
        st.warning("查無可用球員資料，請嘗試其他關鍵字。")
        return

    selected_name = st.selectbox("選擇球員", list(player_options.keys()))
    selected_player = player_options[selected_name]

    detail_result = get_player_detail(selected_player.id, data_mode=get_data_mode())
    if isinstance(detail_result["item"], Player):
        selected_player = detail_result["item"]

    chart_result = get_player_chart_data(selected_player.id, data_mode=get_data_mode())
    render_source_badge(str(chart_result.get("source") or ""))
    _show_data_source(chart_result)
    stats = pd.DataFrame(chart_result["items"])
    quality = get_player_data_quality(selected_player, chart_result["items"])
    _show_data_quality(quality)

    render_section(selected_player.name)

    render_kpi_strip([
        ("隊伍", selected_player.team, selected_player.position),
        ("PPG", f"{selected_player.points:.1f}", "最近一季"),
        ("RPG", f"{selected_player.rebounds:.1f}", "最近一季"),
        ("APG", f"{selected_player.assists:.1f}", "最近一季"),
        ("資料狀態", str(quality["label"]), str(quality["status"])),
    ])

    if stats.empty:
        st.warning("目前沒有可視覺化的近年數據。")
        return

    render_section("數據視覺化")
    tab_trend, tab_radar, tab_table = st.tabs(["近年趨勢", "能力雷達", "完整數據"])
    with tab_trend:
        st.caption("PPG / RPG / APG 由 NBA career totals 依 GP 轉換成每場平均。")
        st.plotly_chart(player_trend_chart(stats), use_container_width=True, config={"displayModeBar": False})
    with tab_radar:
        st.caption("STL 與 BLK 在雷達圖上以 ×5 視覺化，hover 顯示原始數值。")
        st.plotly_chart(player_radar_chart(selected_player), use_container_width=True, config={"displayModeBar": False})
    with tab_table:
        _render_stats_table(stats)

    render_section("近期重點數據")
    col1, col2, col3 = st.columns(3)
    with col1:
        render_stat_card("Steals", f"{selected_player.steals:.1f}", "場均抄截", accent="silver")
    with col2:
        render_stat_card("Blocks", f"{selected_player.blocks:.1f}", "場均火鍋", accent="blue")
    with col3:
        render_stat_card("Turnovers", f"{selected_player.turnovers:.1f}", "場均失誤", accent="red")


def _show_data_source(result: dict[str, object]) -> None:
    if result.get("source") == "seed":
        st.info("目前使用展示資料，外部 NBA API 暫時無法連線或查無完整資料。")
    elif result.get("source") == "partial_api":
        st.warning("目前使用部分 NBA API 資料，部分欄位可能缺漏。")


def _show_data_quality(quality: dict[str, object]) -> None:
    if quality["status"] == "complete":
        st.success("球員資料完整：已取得隊伍、位置與近年 per-game 數據。")
        return

    missing_fields = ", ".join(cast(list[str], quality["missing_fields"]))
    st.warning(f"球員資料尚未完整，缺少欄位：{missing_fields}")


def _render_stats_table(stats: pd.DataFrame) -> None:
    display_columns = {
        "season": "賽季",
        "team": "隊伍",
        "games": "出賽",
        "points": "PPG",
        "rebounds": "RPG",
        "assists": "APG",
        "steals": "SPG",
        "blocks": "BPG",
        "turnovers": "TOV",
    }
    available_columns = [column for column in display_columns if column in stats.columns]
    table = stats[available_columns].rename(columns=display_columns)
    st.dataframe(table, use_container_width=True, hide_index=True)
