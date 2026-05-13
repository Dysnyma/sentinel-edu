"""Sentinel-Edu — 课堂思政元素安全性分析原型系统"""
import streamlit as st
import os
import shutil
from pathlib import Path

from core.config import init_config, save_config_to_file, CONFIG_FILE
from core.database import init_db
from views.helpers import check_api_connection
from views.tab1_build import render_tab1
from views.tab2_detect import render_tab2
from views.tab3_analysis import render_tab3

# ---------- 页面配置 ----------
st.set_page_config(
    page_title="思政课堂安全分析原型",
    layout="wide",
    menu_items={'Get help': None, 'Report a bug': None, 'About': None}
)

# ---------- 初始化 ----------
init_config()
init_db()
os.makedirs("data", exist_ok=True)
os.makedirs("downloads", exist_ok=True)

# ---------- 侧边栏 ----------
st.sidebar.header("⚙️ 全局配置")
st.sidebar.subheader("大模型 API")
api_key = st.sidebar.text_input("API Key", type="password", value=st.session_state.openai_api_key)
base_url = st.sidebar.text_input("API Base URL", value=st.session_state.openai_base_url)
llm_model = st.sidebar.text_input("LLM 模型", value=st.session_state.llm_model)
col_save, col_clear = st.sidebar.columns(2)
with col_save:
    if st.button("💾 保存配置"):
        save_config_to_file()
        st.success("配置已保存")
with col_clear:
    if st.button("🗑️ 清除保存"):
        try:
            os.remove(CONFIG_FILE)
            st.success("已清除")
        except OSError:
            pass
if st.sidebar.button("🔍 测试连接"):
    ok, msg = check_api_connection(api_key, base_url, llm_model)
    if ok:
        st.sidebar.success(msg)
    else:
        st.sidebar.error(msg)

st.sidebar.caption("若无 API Key，大模型功能不可用。")

# 语音识别设置
st.sidebar.subheader("语音识别 (ASR)")
use_local_whisper = st.sidebar.checkbox("使用本地 Whisper 模型（免费，离线）", value=True)
local_whisper_model = None
if use_local_whisper:
    local_whisper_model = st.sidebar.selectbox(
        "模型大小", ["tiny", "base", "small", "medium", "large"],
        index=2, help="越大越准确，但更慢更占内存。推荐 small 或 medium。"
    )

# 工具状态
st.sidebar.subheader("系统工具状态")
ffmpeg_available = shutil.which(st.session_state.ffmpeg_path) is not None
bbdown_available = shutil.which(st.session_state.bbdown_path) is not None
st.sidebar.caption(f"{'✅' if ffmpeg_available else '❌'} FFmpeg: {'可用' if ffmpeg_available else '未找到'}")
st.sidebar.caption(f"{'✅' if bbdown_available else '❌'} BBDown: {'可用' if bbdown_available else '未找到'}")

with st.sidebar.expander("⚙️ 高级工具配置（可选）"):
    new_ffmpeg = st.text_input("FFmpeg 自定义路径", value=st.session_state.ffmpeg_path)
    new_bbdown = st.text_input("BBDown 自定义路径", value=st.session_state.bbdown_path)
    if new_ffmpeg != st.session_state.ffmpeg_path:
        st.session_state.ffmpeg_path = new_ffmpeg
    if new_bbdown != st.session_state.bbdown_path:
        st.session_state.bbdown_path = new_bbdown

concurrency = st.sidebar.slider("并发请求数（加速生成/检测）", 1, 6, 3,
                                help="同时调用大模型的数量，提高速度但可能触发限流。")

# 规范化 base_url：补全 /v1 后缀
base_url = base_url.strip().rstrip('/')
if base_url and not base_url.endswith('/v1'):
    base_url += '/v1'

# 更新 session_state，仅在变化时自动保存
st.session_state.openai_api_key = api_key.strip()
st.session_state.openai_base_url = base_url
st.session_state.llm_model = llm_model.strip()
_last_saved = st.session_state.get('_last_saved_config', {})
_current = {'openai_api_key': api_key, 'openai_base_url': base_url, 'llm_model': llm_model}
if _current != _last_saved:
    save_config_to_file()
    st.session_state['_last_saved_config'] = _current

api_ready = bool(api_key) and bool(base_url) and bool(llm_model)

# ---------- 主界面 ----------
st.title("🛡️ 课堂思政元素安全性分析原型系统")
st.markdown("---")

tab1, tab2, tab3 = st.tabs(["📦 测试集构建", "🔍 安全检测", "📊 可视化分析"])

with tab1:
    render_tab1(api_ready, api_key, base_url, llm_model, concurrency,
                use_local_whisper, local_whisper_model)

with tab2:
    render_tab2(api_ready, api_key, base_url, llm_model, concurrency)

with tab3:
    render_tab3()
