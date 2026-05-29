"""球迷投票 + 先知幣預測系統（合併頁面）."""
from __future__ import annotations

import datetime
import os
from typing import Any

import streamlit as st

from config.settings import get_runtime_settings
from services import prophet_service as ps
from services.cached import get_playoff_series, get_season_phase
from services.hall_service import HALL_POLLS, get_hall_distribution, get_hall_ranking, get_hall_vote, upsert_hall_vote
from services.nba_api_service import get_data_mode
from services.season_service import SeasonPhase, get_current_season
from services.vote_service import (
    ensure_playoff_polls,
    get_completed_polls,
    get_selected_option,
    get_vote_summary,
    has_voted,
    list_active_polls,
    submit_vote,
)
from ui.charts import vote_donut_chart
from ui.components import render_kpi_strip, render_page_header, render_section

_ROUND_ZH: dict[int, str] = {
    1: "第一輪", 2: "分區準決賽", 3: "分區決賽", 4: "NBA Finals",
}


# ── Entry point ───────────────────────────────────────────────────────────────

def render() -> None:
    render_page_header(
        "球迷投票 · 先知幣預測",
        "投票、押注、競猜，一站完成。越早押注先知幣越多。",
    )
    ensure_playoff_polls()

    season = get_current_season()
    ps.init_prophet(season)

    data_mode = get_data_mode()
    phase = SeasonPhase(get_season_phase(data_mode))
    series_list: list[dict[str, Any]] = []
    if phase in (SeasonPhase.PLAYOFFS, SeasonPhase.PLAY_IN):
        series_list = get_playoff_series(data_mode)
        ps.sync_instant_items(series_list, season)
        ps.settle_finished_series(series_list, season)

    _render_runtime_notice()

    nickname = st.text_input(
        "暱稱",
        value=st.session_state.get("voter_id", ""),
        placeholder="輸入暱稱（投票與先知幣共用，跨次保留記錄）",
        help="同一暱稱在同一投票只能投一次；先知幣與暱稱永久綁定。",
    ).strip()
    st.session_state["voter_id"] = nickname

    polls = [p for p in list_active_polls() if p["category"] != "referee"]
    total_votes = sum(sum(get_vote_summary(int(p["id"])).values()) for p in polls)

    if nickname:
        user = ps.get_or_create_user(nickname)
        lb_full = ps.get_leaderboard(200)
        rank = next((i + 1 for i, u in enumerate(lb_full) if u["nickname"] == nickname), "—")
        all_preds = ps.get_user_all_predictions(nickname, season)
        correct = sum(1 for p in all_preds if p.get("coins_earned", 0) > 0)
        render_kpi_strip([
            ("先知幣", str(user["coins"]), "累積總數"),
            ("排名", f"#{rank}", "全體預測者"),
            ("命中", str(correct), f"共 {len(all_preds)} 筆預測"),
            ("投票主題", str(len(polls)), f"{total_votes} 票"),
        ])
    else:
        render_kpi_strip([
            ("投票主題", str(len(polls)), "Active"),
            ("已收到票數", str(total_votes), "全部主題加總"),
        ])
        st.info("請輸入暱稱後開始押注與投票，先知幣與你的暱稱永久綁定。")

    tab_polls, tab_instant, tab_longterm, tab_records, tab_lb = st.tabs(
        ["🏛️ 球員殿堂", "⚡ 即時預測", "🏆 長期預測", "📋 我的紀錄", "🥇 排行榜"]
    )

    with tab_polls:
        _render_hall_tab(nickname)
    with tab_instant:
        _render_instant_tab(nickname, series_list, season)
    with tab_longterm:
        _render_longterm_tab(nickname, season)
    with tab_records:
        _render_records_tab(nickname, season)
    with tab_lb:
        _render_leaderboard_tab()


# ── Tab: 球員殿堂 ─────────────────────────────────────────────────────────────

def _render_hall_tab(nickname: str) -> None:
    render_section("球員殿堂")
    st.caption("沒有正確答案、不結算先知幣。純粹表達你的立場與熱情，看看自己跟大家的品味差多遠。")

    tab_labels = [p["title"] for p in HALL_POLLS]
    sub_tabs = st.tabs(tab_labels)

    for tab, poll in zip(sub_tabs, HALL_POLLS):
        with tab:
            st.caption(str(poll["subtitle"]))
            _render_hall_poll(poll, nickname)


def _render_hall_poll(poll: dict[str, Any], nickname: str) -> None:
    poll_key = str(poll["key"])
    poll_type = str(poll["type"])
    current_vote = get_hall_vote(poll_key, nickname) if nickname else None

    col_input, col_chart = st.columns([1, 1])

    with col_input:
        if current_vote:
            st.info(f"你目前的選擇：**{current_vote}**")

        choice: str | None = None

        if poll_type == "player":
            keyword = st.text_input(
                "搜尋球員",
                value=st.session_state.get(f"hall_kw_{poll_key}", ""),
                placeholder='輸入姓名關鍵字，如 "LeBron"',
                key=f"hall_kw_input_{poll_key}",
            )
            st.session_state[f"hall_kw_{poll_key}"] = keyword
            hits = ps.search_players(keyword) if len(keyword) >= 2 else []
            if hits:
                default_idx = hits.index(current_vote) if current_vote in hits else 0
                choice = st.selectbox(
                    f"搜尋結果（{len(hits)} 位）",
                    hits,
                    index=default_idx,
                    key=f"hall_sel_{poll_key}",
                )
            elif keyword and len(keyword) >= 2:
                st.caption("找不到符合的球員，請換關鍵字。")
            else:
                st.caption("輸入 2 個字以上開始搜尋。")

        elif poll_type == "team":
            team_names = ps.get_nba_team_names()
            default_idx = team_names.index(current_vote) if current_vote in team_names else 0
            choice = st.selectbox(
                "選擇球隊",
                team_names,
                index=default_idx,
                key=f"hall_sel_{poll_key}",
            )

        elif poll_type == "custom":
            options: list[str] = list(poll.get("options", []))
            default_idx = options.index(current_vote) if current_vote in options else 0
            choice = st.radio(
                "選擇",
                options,
                index=default_idx,
                key=f"hall_radio_{poll_key}",
                horizontal=False,
            )

        if not nickname:
            st.caption("請先輸入暱稱才能投票。")
        else:
            btn_label = "更改選擇" if current_vote else "送出"
            if choice and st.button(btn_label, key=f"hall_btn_{poll_key}", use_container_width=True):
                if upsert_hall_vote(poll_key, nickname, str(choice)):
                    if poll_type == "player":
                        st.session_state.pop(f"hall_kw_{poll_key}", None)
                    st.rerun()
                else:
                    st.error("送出失敗，請稍後再試。")

    with col_chart:
        _render_hall_chart(poll_key)


def _render_hall_chart(poll_key: str) -> None:
    labels, values = get_hall_distribution(poll_key)
    if not labels:
        st.info("目前尚無人投票，快來第一個表態！")
        return
    fig = vote_donut_chart(labels, values, other_label="其他")
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    detail_key = f"hall_detail_{poll_key}"
    if st.button("看詳細資料", key=f"hall_detail_btn_{poll_key}", use_container_width=True):
        st.session_state[detail_key] = not st.session_state.get(detail_key, False)

    if st.session_state.get(detail_key, False):
        ranking = get_hall_ranking(poll_key)
        if ranking:
            import pandas as pd
            df = pd.DataFrame(ranking)
            st.dataframe(df, use_container_width=True, hide_index=True)


# ── Tab: 即時預測 ─────────────────────────────────────────────────────────────

def _render_instant_tab(nickname: str, series_list: list[dict[str, Any]], season: str) -> None:
    render_section("季後賽晉級預測")
    st.caption("每個系列賽開賽前開放下注 → 第一場開打後進入進行中 → 系列賽結束自動結算先知幣。")

    items = [it for it in ps.get_all_items(season) if it["category"] == "instant"]
    if not items:
        st.info("目前沒有開放的即時預測。\n\n季後賽開始後，系統會自動依輪次開放各系列賽預測。")
        return

    series_map: dict[str, dict[str, Any]] = {}
    for s in series_list:
        k = ps.series_item_key(s, season)
        if k:
            series_map[k] = s

    by_round: dict[int, list[dict[str, Any]]] = {}
    for item in items:
        rnd = _parse_round_from_key(item["item_key"])
        by_round.setdefault(rnd, []).append(item)

    for rnd in sorted(by_round.keys()):
        round_label = _ROUND_ZH.get(rnd, f"第{rnd}輪")
        round_items = by_round[rnd]
        has_active = any(it["status"] != "settled" for it in round_items)
        with st.expander(round_label, expanded=has_active):
            for item in round_items:
                series = series_map.get(item["item_key"])
                _render_instant_item(nickname, item, series)


def _render_instant_item(
    nickname: str, item: dict[str, Any], series: dict[str, Any] | None
) -> None:
    item_key  = item["item_key"]
    status    = item["status"]
    label     = item["item_label"]
    options   = _teams_from_series_or_label(series, label)
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
            return

        # open or locked — both allow predictions; locked just yields fewer coins
        is_locked = status == "locked"
        score = ""
        if series:
            score = f"（{series['team_a']} **{series['wins_a']}**–**{series['wins_b']}** {series['team_b']}）"
        icon = "🔒" if is_locked else "🟢"
        st.markdown(f"{icon} **{label}** {score}")

        if is_locked:
            st.caption("系列賽進行中，仍可押注，但幣數較低。")

        if not nickname:
            st.caption("請先輸入暱稱才能下注。")
            return

        default_idx = 0
        if user_pred and user_pred["prediction"] in options:
            default_idx = options.index(user_pred["prediction"])

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


# ── Tab: 長期預測 ─────────────────────────────────────────────────────────────

def _render_longterm_tab(nickname: str, season: str) -> None:
    render_section("年度獎項預測")
    st.caption("越早押注、先知幣越多。獎項公布後由管理員結算，正確答案不分大小寫。")

    items = [it for it in ps.get_all_items(season) if it["category"] == "longterm"]
    if not items:
        st.info("長期預測項目尚未初始化，請稍後再試。")
        return

    team_names = ps.get_nba_team_names()
    season_prefix = season + "_"

    for item in items:
        item_key  = item["item_key"]
        status    = item["status"]
        label     = item["item_label"]
        user_pred = ps.get_user_prediction(nickname, item_key) if nickname else None
        suffix    = item_key[len(season_prefix):] if item_key.startswith(season_prefix) else item_key

        with st.container(border=True):
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

            if suffix == "champion":
                choice: str | None = st.selectbox(
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
                        placeholder='輸入姓名關鍵字，如 "Shai"',
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

    _render_admin_panel(season)


# ── Tab: 我的紀錄 ─────────────────────────────────────────────────────────────

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
            hit = bool(correct and pred_val.strip().lower() == correct.strip().lower())
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


# ── Tab: 排行榜 ───────────────────────────────────────────────────────────────

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

        team_names = ps.get_nba_team_names()
        season_prefix = season + "_"

        for item in items:
            item_key = item["item_key"]
            suffix = item_key[len(season_prefix):] if item_key.startswith(season_prefix) else item_key

            with st.container(border=True):
                st.markdown(f"**{item['item_label']}**")

                answer: str | None
                if suffix == "champion":
                    answer = st.selectbox(
                        "正確答案（隊伍）",
                        team_names,
                        key=f"admin_ans_{item_key}",
                    )
                else:
                    col_kw, col_sel = st.columns([1, 1])
                    with col_kw:
                        kw = st.text_input(
                            "搜尋球員",
                            placeholder="輸入姓名關鍵字",
                            key=f"admin_kw_{item_key}",
                        )
                    hits = ps.search_players(kw) if len(kw) >= 2 else []
                    with col_sel:
                        if hits:
                            answer = st.selectbox(
                                f"搜尋結果（{len(hits)} 位）",
                                hits,
                                key=f"admin_ans_{item_key}",
                            )
                        else:
                            answer = None
                            if kw and len(kw) >= 2:
                                st.caption("找不到符合球員，請換關鍵字。")
                            else:
                                st.caption("輸入 2 個字以上開始搜尋。")

                if st.button(
                    f"結算：{item['item_label']}",
                    key=f"admin_btn_{item_key}",
                    disabled=not answer,
                ):
                    n, err = ps.settle_longterm_item(item_key, str(answer))
                    if err:
                        st.error(err)
                    else:
                        st.success(f"結算完成，共結算 {n} 位使用者。")
                        st.rerun()

        _render_admin_revoke_panel(season)


def _render_admin_revoke_panel(season: str) -> None:
    settled_items = [
        it for it in ps.get_all_items(season)
        if it["category"] == "longterm" and it["status"] == "settled"
    ]
    if not settled_items:
        return

    st.divider()
    st.markdown("**撤銷結算**")
    st.caption("撤銷後，該項目回到「開放」狀態，所有已發出的先知幣將收回，預測紀錄重置為未結算。")

    for item in settled_items:
        item_key = item["item_key"]
        correct = item.get("correct_answer", "?")
        with st.container(border=True):
            col_info, col_btn = st.columns([3, 1])
            col_info.markdown(f"**{item['item_label']}**")
            col_info.caption(f"已結算答案：{correct}")
            if col_btn.button("撤銷", key=f"admin_revoke_{item_key}", use_container_width=True):
                n, err = ps.revoke_longterm_item(item_key)
                if err:
                    st.error(err)
                else:
                    st.success(f"已撤銷，{n} 位使用者的先知幣已收回。")
                    st.rerun()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _render_runtime_notice() -> None:
    settings = get_runtime_settings()
    if settings.supports_shared_voting:
        st.success(f"Cloud voting mode：{settings.database_label}。多人可連同一個部署網址投票。")
    else:
        st.info(f"Local demo mode：{settings.database_label}。目前投票資料只會保存在這個執行環境。")
    if settings.warning:
        st.caption(settings.warning)


def _parse_round_from_key(item_key: str) -> int:
    for part in item_key.split("_"):
        if part.startswith("r") and part[1:].isdigit():
            return int(part[1:])
    return 0


def _teams_from_series_or_label(series: dict[str, Any] | None, label: str) -> list[str]:
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
        return dt.astimezone().strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ts
