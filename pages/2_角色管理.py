import streamlit as st

from utils.loader import (
    get_avatar_path,
    load_buff_connections,
    load_characters,
    load_master_roster,
    load_owned_characters,
    save_owned_characters,
)

st.set_page_config(page_title="角色管理", page_icon="👥", layout="wide")
st.title("👥 角色管理")
st.caption("勾选你已拥有的角色，更改会自动保存。")
st.page_link("app.py", label="返回首页", icon="🏠")

buff_df = load_buff_connections()
characters_df = load_characters()
roster = load_master_roster(buff_df, characters_df)

if "owned" not in st.session_state:
    st.session_state.owned = load_owned_characters()


def _widget_key(name: str) -> str:
    return f"owned_char_{name}"


col_a, col_b, col_c = st.columns([1, 1, 4])
with col_a:
    select_all_clicked = st.button("✅ 全选", use_container_width=True)
with col_b:
    deselect_all_clicked = st.button("❌ 全部取消", use_container_width=True)
with col_c:
    st.metric("已选择", f"{len(st.session_state.owned)} / {len(roster)}")

# Applied before the checkboxes below are instantiated in this same run, so their
# displayed state picks up the change immediately (setting a widget's session_state
# value after it has already rendered in the same run is not allowed - before is fine).
if select_all_clicked:
    st.session_state.owned = set(roster)
    for name in roster:
        st.session_state[_widget_key(name)] = True
    save_owned_characters(st.session_state.owned)
elif deselect_all_clicked:
    st.session_state.owned = set()
    for name in roster:
        st.session_state[_widget_key(name)] = False
    save_owned_characters(st.session_state.owned)

search = st.text_input("🔍 搜索角色", "").strip()
filtered_roster = [c for c in roster if search in c] if search else roster
st.caption(f"显示 {len(filtered_roster)} / {len(roster)} 个角色")

st.divider()

N_COLS = 6
cols = st.columns(N_COLS)
for idx, name in enumerate(filtered_roster):
    col = cols[idx % N_COLS]
    with col:
        avatar_path = get_avatar_path(characters_df, name)
        if avatar_path:
            st.image(avatar_path, width=64)
        key = _widget_key(name)
        checked = st.checkbox(name, value=name in st.session_state.owned, key=key)
        if checked and name not in st.session_state.owned:
            st.session_state.owned.add(name)
            save_owned_characters(st.session_state.owned)
        elif not checked and name in st.session_state.owned:
            st.session_state.owned.discard(name)
            save_owned_characters(st.session_state.owned)
