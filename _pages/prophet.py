"""先知幣預測系統頁面.

布局：暱稱 → KPI → Tabs（即時預測 / 長期預測 / 我的紀錄 / 排行榜）→ 管理員結算。
"""
from __future__ import annotations

import datetime
import os
from typing import Any

import streamlit as st

from services import prophet_service as ps
from services.cached import get_playoff_series, get_season_phase
from services.nba_api_service import get_data_mode
from services.season_service import SeasonPhase, get_current_season
from ui.components import render_kpi_strip, render_page_header, render_section

_ROUND_ZH: dict[int, str] = {
    1: "第一輪", 2: "分區準決賽", 3: "分區決賽", 4: "NBA Finals",
}


# ── Entry point ───────────────────────────────────────────────────────────────

def render() -> None:
    render_page_header(
        "先知幣預測",
        "預測季後賽晉級隊伍與年度獎項，越早押注、獎金越豐厚。正確預測可獲得先知幣，誰能稱霸排行榜？",
    )

    season = get_current_season()
    ps.init_prophet(season)

    data_mode = get_data_mode()
    phase = SeasonPhase(get_season_phase(data_mode))
    series_list: list[dict[str, Any]] = []

    if phase in (SeasonPhase.PLAYOFFS, SeasonPhase.PLAY_IN):
        series_list = get_playoff_series(data_mode)
        ps.sync_instant_items(series_list, season)
        ps.settle_finished_series(series_list, season)

    # ── Nickname ──────────────────────────────────────────────────────────────
    nickname = st.text_input(
        "暱稱",
        value=st.session_state.get("prophet_nickname", ""),
        placeholder="輸入你的暱稱（同一暱稱跨次瀏覽會保留先知幣）",
        help="先知幣與暱稱綁定，請使用固定的暱稱。",
    ).strip()
    st.session_state["prophet_nickname"] = nickname

    if nickname:
        user      = ps.get_or_create_user(nickname)
        all_preds = ps.get_user_all_predictions(nickname, season)
        lb_full   = ps.get_leaderboard(200)
        rank      = next((i + 1 for i, u in enumerate(lb_full) if u["nickname"] == nickname), "—")
        correct   = sum(1 for p in all_preds if p.get("coins_earned", 0) > 0)
        render_kpi_strip([
            ("先知幣", str(user["coins"]), "累積總數"),
            ("排名", f"#{rank}", "全體預測者"),
            ("已結算命中", str(correct), f"共 {len(all_preds)} 筆預測"),
        ])
    else:
        st.info("請輸入暱稱後開始押注，先知幣與你的暱稱永久綁定。")

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab_instant, tab_longterm, tab_records, tab_lb = st.tabs(
        ["⚡ 即時預測", "🏆 長期預測", "📋 我的紀錄", "🥇 排行榜"]
    )

    with tab_instant:
        _render_instant_tab(nickname, series_list, season)

    with tab_longterm:
        _render_longterm_tab(nickname, season)

    with tab_records:
        _render_records_tab(nickname, season)

    with tab_lb:
        _render_leaderboard_tab()

    _render_admin_panel(season)


# ── Tab 1: 即時預測 ───────────────────────────────────────────────────────────

def _render_instant_tab(nickname: str, series_list: list[dict[str, Any]], season: str) -> None:
    render_section("季後賽晉級預測")
    st.caption(
        "每個系列賽開賽前開放下注 → 第一場開打後鎖定 → 系列賽結束自動結算先知幣。"
    )

    items = [it for it in ps.get_all_items(season) if it["category"] == "instant"]
    if not items:
        st.info("目前沒有開放的即時預測。\n\n季後賽開始後，系統會自動依輪次開放各系列賽預測。")
        return

    # Build item_key → series lookup
    series_map: dict[str, dict[str, Any]] = {}
    for s in series_list:
        k = ps.series_item_key(s, season)
        if k:
            series_map[k] = s

    # Group by round (parsed from item_key "SEASON_rN_A_B")
    by_round: dict[int, list[dict[str, Any]]] = {}
    for item in items:
        rnd = _parse_round_from_key(item["item_key"])
        by_round.setdefault(rnd, []).append(item)

    for rnd in sorted(by_round.keys()):
        st.markdown(f"#### {_ROUND_ZH.get(rnd, f'第{rnd}輪')}")
        for item in by_round[rnd]:
            series = series_map.get(item["item_key"])
            _render_instant_item(nickname, item, series)


def _render_instant_item(
    nickname: str, item: dict[str, Any], series: dict[str, Any] | None
) -> None:
    item_key = item["item_key"]
    status   = item["status"]
    label    = item["item_label"]

    # Derive team options from series or label
    options = _teams_from_series_or_label(series, label)

    user_pred = ps.get_user_prediction(nickname, item_key) if nickname else None

    with st.container(border=True):
        if status == "settled":
            correct_answer = item.get("correct_answer", "?")
            st.markdown(f"✅ **{label}**")
            st.success(f"正確答案：**{correct_answer}**")
            if user_pred:
                coins = int(user_pred.get("coins_earned", 0))
                if user_pred["prediction"] == correct_answer:
                    st.markdown(f"🎉 你押對了！獲得 **+{coins}** 先知幣")
                else:
                    st.markdown(f"❌ 你押的是：{user_pred['prediction']}（未命中）")

        elif status == "locked":
            score = ""
            if series:
                score = f"（{series['team_a']} **{series['wins_a']}**–**{series['wins_b']}** {series['team_b']}）"
            st.markdown(f"🔒 **{label}** {score}")
            if user_pred:
                ts = _fmt_ts(user_pred["last_changed_at"])
                st.info(f"你的預測：**{user_pred['prediction']}**（{ts} 鎖定）")
            else:
                st.caption("系列賽已開打，預測已鎖定，你尚未下注此場。")

        else:  # open
            score = ""
            if series and (series["wins_a"] + series["wins_b"]) > 0:
                score = f"（目前 {series['team_a']} {series['wins_a']}–{series['wins_b']} {series['team_b']}）"
            st.markdown(f"🟢 **{label}** {score}")

            if not nickname:
                st.caption("請先輸入暱稱才能下注。")
                return

            default_idx = options.index(user_pred["prediction"]) if (
                user_pred and user_pred["prediction"] in options
            ) else 0

            if options:
                choice = st.radio(
                    "預測哪隊晉級",
                    options,
                    index=default_idx,
                    key=f"radio_{item_key}",
                    horizontal=True,
                )
            else:
                choice = st.text_input(
                    "預測晉級隊伍",
                    value=user_pred["prediction"] if user_pred else "",
                    key=f"text_{item_key}",
                )

            btn = "更改預測" if user_pred else "確認下注"
            if st.button(btn, key=f"btn_{item_key}", use_container_width=True):
                ok, msg = ps.upsert_prediction(nickname, item_key, str(choice))
                if ok:
                    st.success(f"已押注：**{choice}**")
                    st.rerun()
                else:
                    st.error(msg)

            if user_pred:
                st.caption(
                    f"目前押注：{user_pred['prediction']}　"
                    f"最後更改：{_fmt_ts(user_pred['last_changed_at'])}"
                )


# ── Tab 2: 長期預測 ───────────────────────────────────────────────────────────

def _render_longterm_tab(nickname: str, season: str) -> None:
    render_section("年度獎項預測")
    st.caption(
        "越早押注、先知幣越多。獎項公布後由管理員結算，"
        "正確答案不分大小寫。"
    )

    items = [it for it in ps.get_all_items(season) if it["category"] == "longterm"]
    if not items:
        st.info("長期預測項目尚未初始化，請稍後再試。")
        return

    team_names = ps.get_nba_team_names()

    for item in items:
        item_key = item["item_key"]
        status   = item["status"]
        label    = item["item_label"]
        user_pred = ps.get_user_prediction(nickname, item_key) if nickname else None

        with st.container(border=True):
            suffix = item_key.split("_")[-1]  # mvp / champion / dpoy / ...

            if status == "settled":
                correct_answer = item.get("correct_answer", "?")
                st.markdown(f"✅ **{label}**")
                st.success(f"正確答案：**{correct_answer}**")
                if user_pred:
                    coins = int(user_pred.get("coins_earned", 0))
                    if user_pred["prediction"].lower() == correct_answer.lower():
                        st.markdown(f"🎉 你押對了！獲得 **+{coins}** 先知幣")
                    else:
                        st.markdown(f"❌ 你押的是：{user_pred['prediction']}（未命中）")
                continue

            st.markdown(f"{'🔒' if status == 'locked' else '🟢'} **{label}**")

            if user_pred:
                st.caption(
                    f"目前押注：{user_pred['prediction']}　"
                    f"最後更改：{_fmt_ts(user_pred['last_changed_at'])}"
                )

            if status == "locked":
                st.caption("此項目已鎖定，無法更改預測。")
                continue

            if not nickname:
                st.caption("請先輸入暱稱。")
                continue

            # Champion uses team dropdown; others use player search
            if suffix == "champion":
                choice = st.selectbox(
                    "選擇隊伍",
                    team_names,
                    index=team_names.index(user_pred["prediction"])
                    if user_pred and user_pred["prediction"] in team_names
                    else 0,
                    key=f"lt_{item_key}",
                )
            else:
                col_search, col_result = st.columns([1, 1])
                with col_search:
                    keyword = st.text_input(
                        "搜尋球員",
                        value=st.session_state.get(f"kw_{item_key}", ""),
                        placeholder="輸入姓名關鍵字，如 \"Shai\"",
                        key=f"kw_input_{item_key}",
                    )
                    st.session_state[f"kw_{item_key}"] = keyword

                hits = ps.search_players(keyword) if len(keyword) >= 2 else []
                default_pred = user_pred["prediction"] if user_pred else ""

                with col_result:
                    if hits:
                        default_in_hits = hits.index(default_pred) if default_pred in hits else 0
                        choice = st.selectbox(
                            f"搜尋結果（{len(hits)} 位）",
                            hits,
                            index=default_in_hits,
                            key=f"lt_sel_{item_key}",
                        )
                    elif keyword and len(keyword) >= 2:
                        st.caption("找不到符合的球員，請換關鍵字。")
                        choice = None
                    else:
                        st.caption("輸入 2 個字以上開始搜尋。")
                        choice = None

            if suffix == "champion":
                if st.button(
                    "更改預測" if user_pred else "確認下注",
                    key=f"lt_btn_{item_key}",
                    use_container_width=True,
                ):
                    ok, msg = ps.upsert_prediction(nickname, item_key, str(choice))
                    st.success(f"已押注：**{choice}**") if ok else st.error(msg)
                    if ok:
                        st.rerun()
            else:
                if choice and st.button(
                    "更改預測" if user_pred else "確認下注",
                    key=f"lt_btn_{item_key}",
                    use_container_width=True,
                ):
                    ok, msg = ps.upsert_prediction(nickname, item_key, str(choice))
                    st.success(f"已押注：**{choice}**") if ok else st.error(msg)
                    if ok:
                        st.session_state.pop(f"kw_{item_key}", None)
                        st.rerun()


# ── Tab 3: 我的紀錄 ───────────────────────────────────────────────────────────

def _render_records_tab(nickname: str, season: str) -> None:
    render_section("我的預測紀錄")
    if not nickname:
        st.info("請先輸入暱稱。")
        return

    preds = ps.get_user_all_predictions(nickname, season)
    if not preds:
        st.info("你尚未在本賽季做出任何預測。")
        return

    for p in preds:
        item_status = p.get("item_status", "")
        pred_val    = p["prediction"]
        correct     = p.get("correct_answer")
        coins       = int(p.get("coins_earned", 0))

        if item_status == "settled":
            hit = correct and pred_val.strip().lower() == correct.strip().lower()
            icon = "✅" if hit else "❌"
            result = f"正確答案：{correct}　{'+' + str(coins) + ' 先知幣' if hit else '未命中'}"
        elif item_status == "locked":
            icon, result = "🔒", "系列賽進行中"
        else:
            icon, result = "🟢", "開放中"

        with st.expander(f"{icon} {p['item_label']}"):
            col1, col2 = st.columns(2)
            col1.markdown(f"**你的預測：** {pred_val}")
            col1.caption(f"最後更改：{_fmt_ts(p['last_changed_at'])}")
            col2.markdown(f"**狀態：** {result}")


# ── Tab 4: 排行榜 ─────────────────────────────────────────────────────────────

def _render_leaderboard_tab() -> None:
    render_section("先知幣排行榜")
    lb = ps.get_leaderboard(20)
    if not lb:
        st.info("還沒有任何人獲得先知幣，快去下注吧！")
        return

    for i, entry in enumerate(lb):
        medal = ("🥇", "🥈", "🥉")[i] if i < 3 else f"{i + 1}."
        st.markdown(
            f"<div style='display:flex;justify-content:space-between;"
            f"padding:6px 0;border-bottom:1px solid #2d2d44;'>"
            f"<span style='color:#E8E8E8'>{medal} {entry['nickname']}</span>"
            f"<span style='color:#C4A100;font-weight:bold'>{entry['coins']} 先知幣</span>"
            f"</div>",
            unsafe_allow_html=True,
        )


# ── Admin settlement panel ────────────────────────────────────────────────────

def _render_admin_panel(season: str) -> None:
    st.divider()
    with st.expander("🔑 管理員結算（長期獎項）"):
        pwd = st.text_input("管理員密碼", type="password", key="admin_pwd")
        expected = os.getenv("PROPHET_ADMIN_PASSWORD", "admin")
        if not pwd:
            st.caption("輸入密碼後解鎖結算功能。")
            return
        if pwd != expected:
            st.error("密碼錯誤。")
            return

        st.success("已驗證，可進行結算操作。")
        items = [
            it for it in ps.get_all_items(season)
            if it["category"] == "longterm" and it["status"] != "settled"
        ]
        if not items:
            st.info("本賽季所有長期預測均已結算。")
            return

        for item in items:
            with st.container(border=True):
                st.markdown(f"**{item['item_label']}**")
                answer = st.text_input(
                    "正確答案",
                    placeholder="輸入獲獎球員全名或隊伍名稱（不分大小寫）",
                    key=f"admin_ans_{item['item_key']}",
                )
                if st.button(f"結算：{item['item_label']}", key=f"admin_btn_{item['item_key']}"):
                    if not answer.strip():
                        st.error("請輸入正確答案。")
                    else:
                        n, err = ps.settle_longterm_item(item["item_key"], answer)
                        if err:
                            st.error(err)
                        else:
                            st.success(f"結算完成，共結算 {n} 位使用者。")
                            st.rerun()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _parse_round_from_key(item_key: str) -> int:
    for part in item_key.split("_"):
        if part.startswith("r") and part[1:].isdigit():
            return int(part[1:])
    return 0


def _teams_from_series_or_label(
    series: dict[str, Any] | None, label: str
) -> list[str]:
    if series:
        return [series["team_a"], series["team_b"]]
    if "：" in label and " vs " in label:
        teams_part = label.split("：", 1)[1]
        return [t.strip() for t in teams_part.split(" vs ")]
    return []


def _fmt_ts(ts: str) -> str:
    try:
        dt = datetime.datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        local = dt.astimezone()
        return local.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ts
