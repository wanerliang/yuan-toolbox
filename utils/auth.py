"""Login gate shared by every page, backed by streamlit-authenticator's local
username/password accounts (.streamlit/auth_config.yaml - gitignored, managed via
scripts/manage_users.py). No external identity provider is required.

Also supports a "Continue as Guest" path for people without an account: a random
guest ID is generated once and stored in a browser cookie (independent of the
authenticator's own re-login cookie), so a guest's owned-character/used-pair state
persists across visits from the same browser without ever creating a real account.
"""
import secrets
from datetime import datetime, timedelta
from pathlib import Path

import extra_streamlit_components as stx
import streamlit as st
import streamlit_authenticator as stauth

from utils.bootstrap import ensure_deployment_bootstrap

AUTH_CONFIG_PATH = Path(".streamlit/auth_config.yaml")
GUEST_COOKIE_NAME = "ruyuan_guest_id"
GUEST_COOKIE_EXPIRY_DAYS = 365
LOGIN_FIELDS = {
    "Form name": "登录",
    "Username": "用户名",
    "Password": "密码",
    "Login": "登录",
}

# Session-state keys that identify *who* is logged in - preserved when
# _sync_identity() clears everything else. Everything not in this set is
# considered "that identity's app data" (owned characters, used pairs, widget
# state) and must not leak from one identity to the next within the same
# browser session (e.g. Alice logs out, a guest logs in, Alice logs back in).
_IDENTITY_KEYS = {
    "_active_user_id",
    "guest_id",
    "authentication_status",
    "username",
    "name",
    "email",
    "roles",
    "logout",
}


def _sync_identity(user_id: str) -> None:
    """Wipe all non-identity session_state the moment the logged-in identity
    changes. Without this, st.session_state.owned/used_pairs (loaded once via
    "if X not in st.session_state") and per-character checkbox widget keys from
    a previous identity get reused - and then re-saved - for whoever logs in
    next, silently corrupting their data."""
    if st.session_state.get("_active_user_id") == user_id:
        return
    for key in list(st.session_state.keys()):
        if key not in _IDENTITY_KEYS:
            del st.session_state[key]
    st.session_state["_active_user_id"] = user_id
    st.rerun()


def _get_cookie_manager(key: str) -> stx.CookieManager:
    # Only instantiated when actually writing a cookie (start/end guest mode) - reads
    # go through the race-free st.context.cookies instead (see _resume_guest_id).
    return stx.CookieManager(key=key)


def _resume_guest_id() -> str | None:
    if "guest_id" in st.session_state:
        return st.session_state["guest_id"]
    cookie_guest_id = st.context.cookies.get(GUEST_COOKIE_NAME)
    if cookie_guest_id:
        st.session_state["guest_id"] = cookie_guest_id
        return cookie_guest_id
    return None


def _start_guest_session() -> None:
    guest_id = f"guest_{secrets.token_hex(8)}"
    _get_cookie_manager("set_guest_cookie").set(
        GUEST_COOKIE_NAME,
        guest_id,
        key="set_guest_cookie_value",
        expires_at=datetime.now() + timedelta(days=GUEST_COOKIE_EXPIRY_DAYS),
    )
    st.session_state["guest_id"] = guest_id


def _end_guest_session() -> None:
    # CookieManager.delete() issues the browser-side deletion first, then tries to
    # drop the cookie from its own local cache dict - which is always empty here
    # since this instance is fresh and hasn't round-tripped from the browser yet.
    # The actual cookie deletion still goes through; only that bookkeeping raises,
    # same known quirk streamlit-authenticator's own delete_cookie() swallows.
    try:
        _get_cookie_manager("delete_guest_cookie").delete(GUEST_COOKIE_NAME, key="delete_guest_cookie_value")
    except KeyError:
        pass
    del st.session_state["guest_id"]


def _finish_real_login(authenticator: stauth.Authenticate) -> str | None:
    """If authentication just succeeded (either silently resumed from a cookie, or
    a credential submission processed this run), sync identity and render the
    logged-in sidebar. Called after every authenticator.login() call, since a
    fresh credential submission is only handled by the interactive (rendering)
    call, not the earlier silent "unrendered" one."""
    if st.session_state.get("authentication_status") is not True:
        return None
    user_id = st.session_state["username"]
    _sync_identity(user_id)
    with st.sidebar:
        st.caption(f"👤 已登录：{st.session_state['name']}")
        authenticator.logout("退出登录", "sidebar")
    return user_id


def require_login() -> str:
    """Render the login form (with a guest option) and halt the page if neither
    logged in nor a guest. Must be called right after st.set_page_config(), before
    any other page content. Returns the logged-in username, or a persistent
    `guest_<hex>` id for guests - either way, the per-user key into utils/db.py."""
    ensure_deployment_bootstrap()

    if not AUTH_CONFIG_PATH.exists():
        st.error(
            f"未找到登录配置文件 `{AUTH_CONFIG_PATH}`。请复制 "
            f"`{AUTH_CONFIG_PATH}.example` 为该文件，并用 `python scripts/manage_users.py "
            f"add <username> \"<显示名称>\"` 添加至少一个账号。"
        )
        st.stop()

    authenticator = stauth.Authenticate(
        str(AUTH_CONFIG_PATH),
        password_instructions="**密码要求：** 8-20 位，至少包含 1 个小写字母、1 个大写字母、"
                              "1 个数字、1 个特殊字符（!@#$%^&* 等）。",
    )

    # Silent check only (no widgets drawn) - lets a real login cookie resume the
    # session before we decide whether to fall back to guest mode or the login form.
    authenticator.login(location="unrendered", fields=LOGIN_FIELDS)
    user_id = _finish_real_login(authenticator)
    if user_id:
        return user_id

    guest_id = _resume_guest_id()
    if guest_id:
        _sync_identity(guest_id)
        with st.sidebar:
            st.caption("👤 访客模式（进度保存在本浏览器）")
            if st.button("退出访客模式", key="guest_logout"):
                _end_guest_session()
                st.rerun()
        return guest_id

    # Neither a real session nor a guest cookie - render the interactive form. This
    # re-attempts the same silent cookie check internally but only draws widgets if
    # that still fails, and _finish_real_login below catches a credential
    # submission made THIS run (login() only sets authentication_status - it
    # doesn't force a rerun, since the just-set cookie can't be read back via
    # st.context.cookies until the next request).
    authenticator.login(fields=LOGIN_FIELDS)
    user_id = _finish_real_login(authenticator)
    if user_id:
        return user_id

    if st.session_state.get("authentication_status") is False:
        st.error("用户名或密码错误。")

    with st.expander("📝 还没有账号？点击注册"):
        try:
            email, username, name = authenticator.register_user(
                fields={
                    "Form name": "注册新账号",
                    "First name": "名",
                    "Last name": "姓",
                    "Email": "邮箱",
                    "Username": "用户名",
                    "Password": "密码",
                    "Repeat password": "确认密码",
                    "Register": "注册",
                },
                captcha=False,
                password_hint=False,
            )
            if email:
                st.success(f"注册成功！请使用用户名「{username}」登录。")
        except stauth.RegisterError as e:
            st.error(str(e))

    st.divider()
    if st.button("👤 以访客身份继续（无需注册，进度保存在本浏览器）"):
        _start_guest_session()
        st.rerun()

    st.stop()
