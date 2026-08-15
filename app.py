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

    # ---- 草稿区：只读快照到局部变量，编辑不直接改动 session_state ----
    # 标准模式：所有修改在「保存」按钮一次性提交（见下方提交区）
    with tab1:
        st.subheader("大模型 API 配置")
        st.caption("填写 API 地址与模型名，点击「测试连接」验证连通性。")

        draft_api_key = st.text_input(
            "API Key（本地模型可留空）", type="password",
            value=st.session_state.get('openai_api_key', ''))
        draft_base_url = st.text_input(
            "API Base URL（例如 https://api.openai.com/v1）",
            value=st.session_state.get('openai_base_url', ''))
        draft_llm_model = st.text_input(
            "LLM 模型（例如 gpt-4o-mini）",
            value=st.session_state.get('llm_model', ''))
        draft_concurrency = st.slider(
            "并发请求数（加速生成/检测）", 1, 6,
            value=st.session_state.get('dialog_concurrency', 3),
            help="同时调用大模型的数量，提高速度但可能触发限流。")

        st.markdown("---")
        if st.button("🔍 测试连接", use_container_width=True):
            with st.spinner("测试 API 连通性..."):
                ok, msg = check_api_connection(
                    draft_api_key.strip(), draft_base_url.strip(), draft_llm_model.strip(),
                )
                if ok:
                    st.success(msg)
                else:
                    st.error(msg)

    with tab2:
        st.subheader("语音识别 (ASR)")
        draft_use_local_whisper = st.checkbox(
            "使用本地 Whisper 模型（免费，离线）",
            value=st.session_state.get('use_local_whisper', False))
        if draft_use_local_whisper:
            _whisper_options = ["tiny", "base", "small", "medium", "large"]
            _current_model = st.session_state.get('local_whisper_model', 'small')
            _current_index = _whisper_options.index(_current_model) if _current_model in _whisper_options else 2
            draft_whisper_model = st.selectbox(
                "模型大小", _whisper_options,
                index=_current_index,
                help="越大越准确，但更慢更占内存。推荐 small 或 medium。",
            )
            if is_whisper_model_downloaded(draft_whisper_model):
                st.caption(f"✅ Whisper {draft_whisper_model} 模型已下载")
            else:
                st.caption(f"📥 Whisper {draft_whisper_model} 模型未下载，首次使用时将自动下载")
        else:
            draft_whisper_model = st.session_state.get('local_whisper_model', 'small')

        st.markdown("---")
        st.subheader("系统工具路径")
        draft_ffmpeg_path = st.text_input(
            "FFmpeg 自定义路径",
            value=st.session_state.get('ffmpeg_path', 'ffmpeg'))
        draft_bbdown_path = st.text_input(
            "BBDown 自定义路径",
            value=st.session_state.get('bbdown_path', './BBDown'))

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

    # ---- 提交区：一次性写回 session_state，再落盘，最后关闭弹窗 ----
    st.markdown("---")
    col_save, col_clear = st.columns([1, 1])
    with col_save:
        if st.button("💾 保存配置到文件", type="primary", use_container_width=True):
            st.session_state.openai_api_key = draft_api_key.strip()
            st.session_state.openai_base_url = normalize_base_url(draft_base_url)
            st.session_state.llm_model = draft_llm_model.strip()
            st.session_state.dialog_concurrency = draft_concurrency
            st.session_state.use_local_whisper = draft_use_local_whisper
            st.session_state.local_whisper_model = draft_whisper_model
            st.session_state.ffmpeg_path = draft_ffmpeg_path.strip()
            st.session_state.bbdown_path = draft_bbdown_path.strip()
            save_config_to_file()
            st.success("配置已保存")
            time.sleep(0.5)
            st.rerun()
    with col_clear:
        if st.button("🗑️ 清除本地保存", use_container_width=True):
            try:
                os.remove(CONFIG_FILE)
                st.success("已清除本地保存的配置")
            except OSError:
                pass

# ---------- 快捷侧边栏 ----------
st.sidebar.header("🛡️ Sentinel-Edu")
st.sidebar.subheader("快捷配置")

# 计算规范化值用于展示（不绑定 widget，不与 dialog 冲突）
_normalized_base_url = normalize_base_url(st.session_state.get('openai_base_url', ''))
_api_key = st.session_state.get('openai_api_key', '').strip()
_llm_model = st.session_state.get('llm_model', '').strip()

# API 就绪：同时需要 Base URL + 模型名 + API Key
api_ready = bool(_normalized_base_url) and bool(_llm_model) and bool(_api_key)

# 显示当前配置详情（只读）
_current_provider = "DeepSeek" if "deepseek" in (_normalized_base_url or "") else \
    "SiliconFlow" if "siliconflow" in (_normalized_base_url or "") else \
    "OpenAI" if "openai" in (_normalized_base_url or "") else "自定义"
_key_masked = _api_key[:6] + "..." + _api_key[-4:] if len(_api_key) > 12 else bool(_api_key)
st.sidebar.markdown(f"**服务商:** {_current_provider}")
st.sidebar.markdown(f"**模型:** `{_llm_model or '(未设置)'}`")
st.sidebar.markdown(f"**Base URL:** `{_normalized_base_url or '(未设置)'}`")
st.sidebar.markdown(f"**API Key:** `{_key_masked if _api_key else '(未设置)'}`")
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
