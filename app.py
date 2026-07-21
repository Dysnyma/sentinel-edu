"""Sentinel-Edu — 课堂思政元素安全性分析原型系统"""
import streamlit as st
import os
import shutil
import time

from core.config import (
    init_config, save_config_to_file, CONFIG_FILE, load_session_state,
    load_prompts, save_prompts, normalize_base_url,
)
from core.database import init_db
from core.asr import is_whisper_model_downloaded
from views.helpers import check_api_connection
from views.tab1_build import render_tab1
from views.tab2_detect import render_tab2
from views.tab3_analysis import render_tab3
from views.tab4_learn import render_tab4

# ---------- 页面配置 ----------
st.set_page_config(
    page_title="思政课堂安全分析原型",
    layout="wide",
    menu_items={'Get help': None, 'Report a bug': None, 'About': None}
)

# ---------- 初始化 ----------
init_config()
load_session_state()
init_db()
os.makedirs("data", exist_ok=True)
os.makedirs("downloads", exist_ok=True)

# ---------------------------------------------------------------------------
#  全局设置模态弹窗
# ---------------------------------------------------------------------------
@st.dialog("⚙️ 全局系统设置", width="large")
def global_settings_dialog():
    tab1, tab2, tab3 = st.tabs(["🔌 API 与网络", "🛠️ 本地工具", "🧠 提示词工程"])

    with tab1:
        st.subheader("大模型 API 配置")
        st.caption("填写 API 地址与模型名，点击「测试连接」验证连通性。")

        # 唯一编辑入口，直接绑定 session_state（侧边栏不再有 widget 冲突）
        st.text_input("API Key（本地模型可留空）", type="password", key="openai_api_key")
        st.text_input("API Base URL（例如 https://api.openai.com/v1）", key="openai_base_url")
        st.text_input("LLM 模型（例如 gpt-4o-mini）", key="llm_model")

        st.markdown("---")
        col_test, col_save = st.columns([1, 1])
        with col_test:
            if st.button("🔍 测试连接", use_container_width=True):
                with st.spinner("测试 API 连通性..."):
                    ok, msg = check_api_connection(
                        st.session_state.get('openai_api_key', '').strip(),
                        st.session_state.get('openai_base_url', '').strip(),
                        st.session_state.get('llm_model', '').strip(),
                    )
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)
        with col_save:
            if st.button("💾 保存配置到文件", type="primary", use_container_width=True):
                save_config_to_file()
                st.success("配置已持久化保存")
                time.sleep(0.5)
                st.rerun()

        st.markdown("---")
        st.slider("并发请求数（加速生成/检测）", 1, 6,
                  key="dialog_concurrency",
                  help="同时调用大模型的数量，提高速度但可能触发限流。")

        col_clear, _ = st.columns([1, 1])
        with col_clear:
            if st.button("🗑️ 清除本地保存", use_container_width=True):
                try:
                    os.remove(CONFIG_FILE)
                    st.success("已清除本地保存的配置")
                except OSError:
                    pass

    with tab2:
        st.subheader("语音识别 (ASR)")
        st.checkbox("使用本地 Whisper 模型（免费，离线）", key="use_local_whisper")
        if st.session_state.use_local_whisper:
            st.selectbox(
                "模型大小", ["tiny", "base", "small", "medium", "large"],
                key="local_whisper_model",
                help="越大越准确，但更慢更占内存。推荐 small 或 medium。",
            )
            if is_whisper_model_downloaded(st.session_state.local_whisper_model):
                st.caption(f"✅ Whisper {st.session_state.local_whisper_model} 模型已下载")
            else:
                st.caption(f"📥 Whisper {st.session_state.local_whisper_model} 模型未下载，首次使用时将自动下载")

        st.markdown("---")
        st.subheader("系统工具路径")
        st.text_input("FFmpeg 自定义路径", key="ffmpeg_path")
        st.text_input("BBDown 自定义路径", key="bbdown_path")

    with tab3:
        if 'prompts' not in st.session_state:
            st.session_state['prompts'] = load_prompts()

        st.subheader("🤖 提示词编辑（热重载）")
        st.caption("编辑后点击保存，下次 LLM 调用即生效")

        scan = st.text_area("🛡️ 扫描提示词 (SCAN_PROMPT)",
                            value=st.session_state['prompts'].get('scan_prompt', ''),
                            height=200)
        poison = st.text_area("🦠 投毒提示词 (POISON_PROMPT)",
                              value=st.session_state['prompts'].get('poison_prompt', ''),
                              height=200)
        correct = st.text_area("✏️ 纠错提示词 (CORRECT_PROMPT)",
                               value=st.session_state['prompts'].get('correct_prompt', ''),
                               height=200)

        col_reset, col_save_p = st.columns(2)
        with col_reset:
            if st.button("↩️ 恢复默认", use_container_width=True):
                from core.config import _default_prompts
                defaults = _default_prompts()
                st.session_state['prompts'] = defaults
                save_prompts(**defaults)
                st.rerun()
        with col_save_p:
            if st.button("💾 保存并应用提示词", type="primary", use_container_width=True):
                st.session_state['prompts'] = {
                    'scan_prompt': scan,
                    'poison_prompt': poison,
                    'correct_prompt': correct,
                }
                save_prompts(scan, poison, correct)
                st.success("✅ 提示词已保存")

# ---------- 快捷侧边栏 ----------
st.sidebar.header("🛡️ Sentinel-Edu")
st.sidebar.subheader("快捷配置")

# 计算规范化值用于状态判定（不直接绑定 widget，避免与 dialog 冲突）
_normalized_base_url = normalize_base_url(st.session_state.get('openai_base_url', ''))
_api_key = st.session_state.get('openai_api_key', '').strip()
_llm_model = st.session_state.get('llm_model', '').strip()

# API 就绪只需 Base URL 和模型名，API Key 在测试连接时验证
api_ready = bool(_normalized_base_url) and bool(_llm_model)

# 显示当前配置摘要
_current_provider = "DeepSeek" if "deepseek" in (_normalized_base_url or "") else \
    "SiliconFlow" if "siliconflow" in (_normalized_base_url or "") else \
    "OpenAI" if "openai" in (_normalized_base_url or "") else "自定义"
st.sidebar.caption(f"当前服务商: {_current_provider}")
st.sidebar.caption(f"模型: {_llm_model or '(未设置)'}")
st.sidebar.markdown(f"{'🟢' if api_ready else '🔴'} **API**: {'已就绪' if api_ready else '未配置'}")

ffmpeg_ready = shutil.which(st.session_state.get('ffmpeg_path', 'ffmpeg')) is not None
st.sidebar.markdown(f"{'🟢' if ffmpeg_ready else '🔴'} **FFmpeg**: {'可用' if ffmpeg_ready else '未找到'}")

bbdown_ready = shutil.which(st.session_state.get('bbdown_path', './BBDown')) is not None
st.sidebar.markdown(f"{'🟢' if bbdown_ready else '🔴'} **BBDown**: {'可用' if bbdown_ready else '未找到'}")

if st.session_state.use_local_whisper:
    whisper_ready = is_whisper_model_downloaded(st.session_state.local_whisper_model)
    st.sidebar.markdown(f"{'🟢' if whisper_ready else '🟡'} **Whisper**: {'已下载' if whisper_ready else '待下载'}")
else:
    st.sidebar.markdown("⚪ **Whisper**: 走云端 API")

st.sidebar.markdown("---")
if st.sidebar.button("⚙️ 全局设置", use_container_width=True, type="primary"):
    global_settings_dialog()

# ---------- 自动持久化配置（用 session_state 原始值比较，避免 normalize 干扰） ----------
_raw_base = st.session_state.get('openai_base_url', '').strip()
_current = {'openai_api_key': _api_key, 'openai_base_url': _raw_base, 'llm_model': _llm_model}
_last_saved = st.session_state.get('_last_saved_config', {})
if _current != _last_saved:
    save_config_to_file()
    st.session_state['_last_saved_config'] = _current

concurrency = st.session_state.dialog_concurrency
use_local_whisper = st.session_state.use_local_whisper
local_whisper_model = st.session_state.local_whisper_model

# ---------- 主界面渲染 ----------
st.title("🛡️ 课堂思政元素安全性分析原型系统")
st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(["📦 测试集构建", "🔍 安全检测", "📊 可视化分析", "🧠 自学习优化"])

with tab1:
    render_tab1(api_ready, _api_key, _normalized_base_url, _llm_model, concurrency,
                use_local_whisper, local_whisper_model)

with tab2:
    render_tab2(api_ready, _api_key, _normalized_base_url, _llm_model, concurrency)

with tab3:
    render_tab3()

with tab4:
    render_tab4()
