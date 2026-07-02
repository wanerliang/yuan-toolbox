from pathlib import Path

import streamlit as st

from utils.constants import SQUAD_SIZES, TARGETS, WEATHERS
from utils.loader import (
    load_buff_connections,
    load_characters,
    load_master_roster,
    load_owned_characters,
    load_used_pairs,
    save_used_pairs,
    used_pair_key,
)
from utils.rules import MODE_HIGHEST, MODE_UNMARKED, recommend_squads

MODE_LABELS = {MODE_HIGHEST: "最高分", MODE_UNMARKED: "未标记优先"}
WEATHER_ICON_DIR = Path("assets/weather")

st.set_page_config(page_title="如鸢 突发情况 助手", page_icon="🎮", layout="wide")
st.title("🎮 鸢报-突发情况 队伍推荐")
st.caption("勾选你拥有的角色，选择当前突发情况的目标与天气，获取羁绊分数最高的队伍推荐。")

buff_df = load_buff_connections()
characters_df = load_characters()
roster = load_master_roster(buff_df, characters_df)

if "owned" not in st.session_state:
    st.session_state.owned = load_owned_characters()
if "used_pairs" not in st.session_state:
    st.session_state.used_pairs = load_used_pairs()
if "selected_weather" not in st.session_state:
    st.session_state.selected_weather = WEATHERS[0]

# Sidebar is kept minimal - just the persistent "how many characters do I own" status
# and a link to the 角色管理 page. Everything that's a per-search parameter (目标, 天气,
# 队伍人数, 排序方式) lives on the main page instead, where there's enough width for the
# weather icon row and a clean multi-column control layout - same reasoning as moving
# character selection to its own page.
with st.sidebar:
    st.header("👥 我拥有的角色")
    st.metric("已选择", f"{len(st.session_state.owned)} / {len(roster)}")
    st.page_link("pages/2_角色管理.py", label="管理角色", icon="👥")
    st.page_link("app.py", label="返回首页", icon="🏠")

st.subheader("⚡ 突发情况")
target_col, _ = st.columns([1, 3])
with target_col:
    target = st.selectbox("目标", TARGETS)

# Icons downloaded locally via scripts/download_weather_icons.py (source: the same wiki
# page's 天气 column headers, see BUSINESS_REQUIREMENTS.md §6.1) so there's no runtime
# dependency on the wiki being reachable.
weather_cols = st.columns(len(WEATHERS))
for w, col in zip(WEATHERS, weather_cols):
    with col:
        icon_path = WEATHER_ICON_DIR / f"{w}.png"
        if icon_path.exists():
            st.image(str(icon_path), width=48)
        is_selected = st.session_state.selected_weather == w
        if st.button(
            w, key=f"weather_{w}", use_container_width=True,
            type="primary" if is_selected else "secondary",
        ):
            # The just-clicked button's type= above was computed from the *pre-click*
            # session_state (Streamlit doesn't auto-rerun mid-script just because
            # session_state changed), so without forcing a rerun here the highlight
            # would only catch up on the *next* interaction - looking like the first
            # click "didn't work."
            st.session_state.selected_weather = w
            st.rerun()
weather = st.session_state.selected_weather

st.subheader("⚙️ 队伍设置")
setting_cols = st.columns([1, 1, 1.4, 1])
with setting_cols[0]:
    squad_size = st.selectbox("队伍人数", SQUAD_SIZES, index=len(SQUAD_SIZES) - 1)
with setting_cols[1]:
    top_n = st.slider("显示前 N 个推荐", 1, 20, 5)
with setting_cols[2]:
    mode = st.radio(
        "推荐模式",
        [MODE_HIGHEST, MODE_UNMARKED],
        format_func=lambda m: MODE_LABELS[m],
        horizontal=True,
    )
with setting_cols[3]:
    st.write("")
    st.write("")
    run_btn = st.button("🔍 获取推荐", use_container_width=True)

st.divider()

if run_btn:
    # Store only the search parameters, not a precomputed result - st.button() is only
    # True on the single rerun right after the click, so gating the *results* (which
    # contain their own interactive checkboxes, plus the reverse toggle below) behind
    # `if run_btn` would make them disappear the instant any of those widgets is clicked
    # (that click triggers a rerun where run_btn is False again). Recomputing from the
    # stored search params on every rerun keeps results live and correctly reflects the
    # reverse toggle and any used_pairs changes immediately, without needing to
    # re-click "获取推荐".
    if len(st.session_state.owned) < squad_size:
        st.session_state.pop("last_search", None)
        st.warning(f"你拥有的角色不足 {squad_size} 个，无法组成队伍。")
    else:
        st.session_state.last_search = {
            "target": target,
            "weather": weather,
            "squad_size": squad_size,
            "mode": mode,
            "top_n": top_n,
        }

if not st.session_state.owned:
    st.info("👈 请先前往侧边栏「角色管理」页面勾选你拥有的角色。")
elif "last_search" not in st.session_state:
    st.info("设置好角色和突发情况参数后，点击“获取推荐”。")
else:
    search = st.session_state.last_search
    reverse = st.checkbox(
        "🔃 倒序显示（显示相反顺序的队伍）",
        key="reverse_display",
        help="最高分模式倒序 = 最低分优先，用于故意打出较差结果的场景；"
             "未标记优先模式倒序 = 改为优先显示由已收集羁绊组成的队伍。",
    )

    result = recommend_squads(
        buff_df,
        st.session_state.owned,
        search["target"],
        search["weather"],
        search["squad_size"],
        used_pairs=st.session_state.used_pairs,
        mode=search["mode"],
        reverse=reverse,
        top_n=search["top_n"],
    )
    r_target, r_weather, r_squad_size, r_mode = (
        search["target"], search["weather"], search["squad_size"], search["mode"]
    )
    if result["truncated"]:
        st.warning(
            f"目标={r_target} · 天气={r_weather} 下相关角色数量较多，"
            f"仅保留影响最大的部分羁绊参与计算。"
        )
    squads = result["squads"]
    if not squads:
        st.warning("没有找到符合条件的队伍。")
    else:
        mode_label = MODE_LABELS[r_mode] + ("（倒序）" if reverse else "")
        st.subheader(
            f"✅ 目标={r_target} · 天气={r_weather} · 队伍人数={r_squad_size} · 排序：{mode_label}"
        )
        rendered_combo_keys = set()
        for i, sq in enumerate(squads, start=1):
            with st.container(border=True):
                if r_mode == MODE_UNMARKED and reverse:
                    score_line = (
                        f"**#{i} 已收集贡献分数：{sq['marked_score']:+d}%**"
                        f"（原始分数：{sq['score']:+d}%）"
                    )
                elif r_mode == MODE_UNMARKED:
                    score_line = (
                        f"**#{i} 新进度分数：{sq['new_progress_score']:+d}%**"
                        f"（原始分数：{sq['score']:+d}%）"
                    )
                else:
                    score_line = f"**#{i} 分数：{sq['score']:+d}%**"
                st.markdown(f"{score_line} — {' / '.join(sq['squad'])}")
                if not sq["active_combos"]:
                    st.caption("此队伍未触发任何已知羁绊（分数 0）。")
                    continue
                for combo in sq["active_combos"]:
                    key = used_pair_key(combo["combo_id"], r_target, r_weather)
                    already_used = key in st.session_state.used_pairs
                    label = f"{combo['combination']}（{combo['value_pct']:+d}%）"
                    if combo["value_pct"] < 0:
                        label = f"⚠️ {label} — 减益"

                    if key in rendered_combo_keys:
                        # Same 羁绊 also appears in an earlier squad above - avoid a
                        # duplicate Streamlit widget key, just show its current status.
                        status = "✅ 已标记" if already_used else "尚未标记"
                        st.caption(f"{label} — {status}（见上方队伍中的复选框）")
                        continue
                    rendered_combo_keys.add(key)

                    checked = st.checkbox(label, value=already_used, key=f"used_{key}")
                    if checked != already_used:
                        if checked:
                            st.session_state.used_pairs.add(key)
                        else:
                            st.session_state.used_pairs.discard(key)
                        save_used_pairs(st.session_state.used_pairs)

st.divider()
with st.expander("📖 羁绊收集进度（成就用）"):
    all_keys = {
        used_pair_key(row.combo_id, row.target, row.weather)
        for row in buff_df.itertuples()
    }
    used_count = len(all_keys & st.session_state.used_pairs)
    st.metric("已收集 / 总数", f"{used_count} / {len(all_keys)}")

    filter_option = st.radio("筛选", ["全部", "已收集", "未收集"], horizontal=True, index=0)

    progress_df = buff_df[["combination", "target", "weather", "value_pct", "combo_id"]].copy()
    progress_df["key"] = progress_df.apply(
        lambda r: used_pair_key(r["combo_id"], r["target"], r["weather"]), axis=1
    )
    progress_df["已收集"] = progress_df["key"].isin(st.session_state.used_pairs)

    if filter_option == "已收集":
        progress_df = progress_df[progress_df["已收集"]]
    elif filter_option == "未收集":
        progress_df = progress_df[~progress_df["已收集"]]

    display_df = progress_df.drop(columns=["combo_id", "key"]).rename(
        columns={
            "combination": "组合",
            "target": "目标",
            "weather": "天气",
            "value_pct": "数值",
        }
    )

    # Keying by filter_option gives a fresh editor whenever the row set changes shape
    # (switching filters), avoiding stale edit-state carried over from a different view.
    edited_df = st.data_editor(
        display_df,
        use_container_width=True,
        hide_index=True,
        disabled=["组合", "目标", "天气", "数值"],
        column_config={"已收集": st.column_config.CheckboxColumn("已收集")},
        key=f"progress_editor_{filter_option}",
    )

    changed = False
    for idx in edited_df.index:
        new_val = edited_df.loc[idx, "已收集"]
        if new_val != progress_df.loc[idx, "已收集"]:
            key = progress_df.loc[idx, "key"]
            if new_val:
                st.session_state.used_pairs.add(key)
            else:
                st.session_state.used_pairs.discard(key)
            changed = True
    if changed:
        save_used_pairs(st.session_state.used_pairs)
        st.rerun()
