import streamlit as st

from utils.auth import require_login
from utils.db import load_owned_characters
from utils.loader import load_buff_connections, load_characters, load_master_roster

st.set_page_config(page_title="如鸢工具箱", page_icon="🎮", layout="wide")

user_id = require_login()

st.title("🎮 如鸢工具箱")
st.caption("选择下面的工具开始，或使用左侧菜单在页面间切换。")

buff_df = load_buff_connections()
characters_df = load_characters()
roster = load_master_roster(buff_df, characters_df)
owned = load_owned_characters(user_id)

col1, col2 = st.columns(2)

with col1:
    with st.container(border=True):
        st.subheader("🎯 鸢报-突发情况")
        st.write("勾选拥有的角色，选择目标与天气，获取羁绊分数最高的队伍推荐。")
        st.page_link("pages/1_鸢报-突发情况.py", label="打开", icon="🎯", use_container_width=True)

with col2:
    with st.container(border=True):
        st.subheader("👥 角色管理")
        st.write(f"当前已选择 {len(owned)} / {len(roster)} 个角色。搜索、勾选、批量全选/取消。")
        st.page_link("pages/2_角色管理.py", label="打开", icon="👥", use_container_width=True)
