"""Streamlit-aware caching wrappers for nba_api_service, player_service, and season_service.

Caching is kept in this module so that service modules remain plain Python
(no streamlit import), making them fully testable without a Streamlit runtime.
"""
from __future__ import annotations

from typing import Any

import streamlit as st

from services import nba_api_service, player_service, season_service


@st.cache_data(ttl=60)
def get_scoreboard(data_mode: str) -> dict[str, Any]:
    return nba_api_service.get_scoreboard()


@st.cache_data(ttl=300)
def get_recent_games(data_mode: str) -> dict[str, Any]:
    return nba_api_service.get_recent_games()


@st.cache_data(ttl=30)
def get_game_boxscore(game_id: str, data_mode: str) -> dict[str, Any]:
    return nba_api_service.get_game_boxscore(game_id)


@st.cache_data(ttl=300)
def get_game_officials(game_id: str, data_mode: str) -> list[dict[str, Any]]:
    return nba_api_service.get_game_officials(game_id)


@st.cache_data(ttl=1800)
def get_season_phase(data_mode: str) -> str:
    return season_service.detect_season_phase().value


@st.cache_data(ttl=900)
def get_playoff_series(data_mode: str) -> list[dict[str, Any]]:
    return season_service.get_playoff_series()


@st.cache_data(ttl=3600)
def get_standings(data_mode: str) -> dict[str, list[dict[str, Any]]]:
    return season_service.get_standings()


@st.cache_data(ttl=300)
def find_players(keyword: str, data_mode: str) -> dict[str, Any]:
    return player_service.find_players(keyword)


@st.cache_data(ttl=600)
def get_player_detail(player_id: int, data_mode: str) -> dict[str, Any]:
    return player_service.get_player_detail(player_id)


@st.cache_data(ttl=600)
def get_player_chart_data(player_id: int, data_mode: str) -> dict[str, Any]:
    return player_service.get_player_chart_data(player_id)
