from __future__ import annotations

from typing import Any

import streamlit as st

from services import auth_service
from services import prophet_service as ps
from ui.components import render_page_header, render_section


def _current_user() -> dict[str, Any] | None:
    return st.session_state.get("logged_in_user")


def render() -> None:
    render_page_header("登入 / 註冊", "建立帳號、登入後即可投票、預測、購買球員。")

    user = _current_user()
    if user:
        _render_account_panel(user)
    else:
        _render_auth_form()


def _render_account_panel(user: dict[str, Any]) -> None:
    nickname = user["nickname"]
    prophet_user = ps.get_or_create_user(nickname)

    st.success(f"已登入為 **{user['username']}**")
    col_info, col_logout = st.columns([3, 1])
    col_info.markdown(f"暱稱：**{nickname}**　💰 先知幣：**{prophet_user['coins']}** 枚")
    if col_logout.button("登出", key="auth_page_logout"):
        st.session_state.pop("logged_in_user", None)
        st.session_state.pop("voter_id", None)
        st.rerun()

    st.divider()
    render_section("修改密碼")
    old_pwd = st.text_input("目前密碼", type="password", key="chg_old_pwd").strip()
    new_pwd = st.text_input("新密碼（至少 4 字元）", type="password", key="chg_new_pwd").strip()
    new_pwd2 = st.text_input("確認新密碼", type="password", key="chg_new_pwd2").strip()
    if st.button("修改密碼", key="chg_pwd_btn", use_container_width=True):
        if not old_pwd or not new_pwd:
            st.warning("請輸入目前密碼與新密碼。")
        elif new_pwd != new_pwd2:
            st.error("兩次新密碼不一致。")
        else:
            ok, msg = auth_service.change_password(user["username"], old_pwd, new_pwd)
            st.success(msg) if ok else st.error(msg)


def _render_auth_form() -> None:
    tab_login, tab_register = st.tabs(["登入", "註冊"])
    with tab_login:
        _render_login_tab()
    with tab_register:
        _render_register_tab()


def _render_login_tab() -> None:
    username = st.text_input("帳號", key="auth_login_username", placeholder="輸入帳號").strip()
    password = st.text_input("密碼", type="password", key="auth_login_password").strip()
    if st.button("登入", key="auth_btn_login", use_container_width=True):
        if not username or not password:
            st.warning("請輸入帳號與密碼。")
        else:
            user = auth_service.login_user(username, password)
            if user:
                st.session_state["logged_in_user"] = user
                st.session_state["voter_id"] = user["nickname"]
                st.rerun()
            else:
                st.error("帳號或密碼錯誤。")


def _render_register_tab() -> None:
    new_username = st.text_input("帳號（4–30 字元）", key="auth_reg_username", placeholder="設定登入帳號").strip()
    new_nickname = st.text_input("暱稱（公開顯示）", key="auth_reg_nickname", placeholder="設定你的暱稱").strip()
    new_password = st.text_input("密碼（至少 4 字元）", type="password", key="auth_reg_password").strip()
    new_password2 = st.text_input("確認密碼", type="password", key="auth_reg_password2").strip()
    if st.button("建立帳號", key="auth_btn_register", use_container_width=True):
        if new_password != new_password2:
            st.error("兩次密碼不一致。")
        else:
            ok, msg = auth_service.register_user(new_username, new_password, new_nickname)
            if ok:
                st.success("帳號建立成功！請切換到「登入」頁面登入。")
            else:
                st.error(msg)
