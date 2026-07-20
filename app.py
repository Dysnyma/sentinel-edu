"""Sentinel-Edu — 课堂思政元素安全性分析原型系统"""
import streamlit as st
import os
import shutil

from core.config import init_config, save_config_to_file, CONFIG_FILE, load_session_state, load_prompts, save_prompts, load_providers, sync_providers
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

# ---------- 侧边栏 ----------
st.sidebar.header("⚙️ 全局配置")
st.sidebar.subheader("大模型 API")
api_key = st.sidebar.text_input(
    "API Key", type="password", value=st.session_state.openai_api_key)

providers = load_providers()
provider_ids = [p['id'] for p in providers]
provider_names = [p['name'] for p in providers]
current_provider_id = st.session_state.get('openai_provider_id', 'openai')
default_idx = provider_ids.index(current_provider_id) if current_provider_id in provider_ids else 0

selected_provider_idx = st.sidebar.selectbox(
    "服务商", range(len(providers)),
    format_func=lambda i: provider_names[i], index=default_idx)
selected_provider = providers[selected_provider_idx]

# 服务商切换时重置模型
if st.session_state.get('_last_provider_id', None) != selected_provider['id']:
    st.session_state['_last_provider_id'] = selected_provider['id']
    st.session_state['openai_provider_id'] = selected_provider['id']
    if selected_provider['id'] != 'custom':
        st.session_state.openai_base_url = selected_provider['base_url']
        st.session_state.llm_model = ''

if selected_provider['id'] == 'custom':
    base_url = st.sidebar.text_input(
        "API Base URL", value=st.session_state.openai_base_url)
    llm_model = st.sidebar.text_input(
        "LLM 模型", value=st.session_state.llm_model)
else:
    base_url = selected_provider['base_url']
    models = selected_provider.get('models', [])
    model_idx = models.index(st.session_state.llm_model) if st.session_state.llm_model in models else 0
    llm_model = st.sidebar.selectbox(
        "模型", models, index=model_idx, help=f"Base URL: {base_url}")

    st.sidebar.caption("")
    if st.sidebar.button("🔄 同步最新模型列表", use_container_width=True,
                         help="从远程拉取最新的服务商和模型配置"):
        synced, ok, msg = sync_providers()
        if ok:
            st.sidebar.success(msg)
            st.rerun()
        else:
            st.sidebar.error(msg)

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
    if is_whisper_model_downloaded(local_whisper_model):
        st.sidebar.caption(f"✅ Whisper {local_whisper_model} 模型已下载")
    else:
        st.sidebar.caption(f"📥 Whisper {local_whisper_model} 模型未下载，首次使用时将自动下载")

# 工具状态
st.sidebar.subheader("系统工具状态")
ffmpeg_available = shutil.which(st.session_state.ffmpeg_path) is not None
bbdown_available = shutil.which(st.session_state.bbdown_path) is not None
st.sidebar.caption(
    f"{'✅' if ffmpeg_available else '❌'} FFmpeg: {'可用' if ffmpeg_available else '未找到'}")
st.sidebar.caption(
    f"{'✅' if bbdown_available else '❌'} BBDown: {'可用' if bbdown_available else '未找到'}")

with st.sidebar.expander("⚙️ 高级工具配置（可选）"):
    new_ffmpeg = st.text_input(
        "FFmpeg 自定义路径", value=st.session_state.ffmpeg_path)
    new_bbdown = st.text_input(
        "BBDown 自定义路径", value=st.session_state.bbdown_path)
    if new_ffmpeg != st.session_state.ffmpeg_path:
        st.session_state.ffmpeg_path = new_ffmpeg
    if new_bbdown != st.session_state.bbdown_path:
        st.session_state.bbdown_path = new_bbdown

concurrency = st.sidebar.slider("并发请求数（加速生成/检测）", 1, 6, 3,
                                help="同时调用大模型的数量，提高速度但可能触发限流。")

# ── 提示词编辑器 ────────────────────────────────────────────
if 'prompts' not in st.session_state:
    st.session_state['prompts'] = load_prompts()

with st.sidebar.expander("🤖 提示词编辑（热重载）"):
    st.caption("编辑后点击保存，下次 LLM 调用即生效")
    scan = st.text_area("🛡️ 扫描提示词 (SCAN_PROMPT)",
                        st.session_state['prompts'].get('scan_prompt', ''),
                        height=200)
    poison = st.text_area("🦠 投毒提示词 (POISON_PROMPT)",
                          st.session_state['prompts'].get('poison_prompt', ''),
                          height=200)
    correct = st.text_area("✏️ 纠错提示词 (CORRECT_PROMPT)",
                           st.session_state['prompts'].get('correct_prompt', ''),
                           height=200)
    col_reset, col_save = st.columns(2)
    with col_reset:
        if st.button("↩️ 恢复默认", use_container_width=True):
            from core.config import _default_prompts
            defaults = _default_prompts()
            st.session_state['prompts'] = defaults
            save_prompts(**defaults)
            st.rerun()
    with col_save:
        if st.button("💾 保存并应用", type="primary", use_container_width=True):
            st.session_state['prompts'] = {
                'scan_prompt': scan,
                'poison_prompt': poison,
                'correct_prompt': correct,
            }
            save_prompts(scan, poison, correct)
            st.success("✅ 已保存，将在下次 LLM 调用时生效")

# 规范化 base_url：补全 /v1 后缀
base_url = base_url.strip().rstrip('/')
if base_url and not base_url.endswith('/v1'):
    base_url += '/v1'

# 更新 session_state，仅在变化时自动保存
st.session_state.openai_api_key = api_key.strip()
st.session_state.openai_base_url = base_url
st.session_state.llm_model = llm_model.strip()
_last_saved = st.session_state.get('_last_saved_config', {})
_current = {'openai_api_key': api_key,
            'openai_base_url': base_url, 'llm_model': llm_model}
if _current != _last_saved:
    save_config_to_file()
    st.session_state['_last_saved_config'] = _current

api_ready = bool(api_key) and bool(base_url) and bool(llm_model)

# ---------- 主界面 ----------
st.title("🛡️ 课堂思政元素安全性分析原型系统")
st.markdown("---")

tab1, tab2, tab3, tab4 = st.tabs(["📦 测试集构建", "🔍 安全检测", "📊 可视化分析", "🧠 自学习优化"])

with tab1:
    render_tab1(api_ready, api_key, base_url, llm_model, concurrency,
                use_local_whisper, local_whisper_model)

with tab2:
    render_tab2(api_ready, api_key, base_url, llm_model, concurrency)

with tab3:
    render_tab3()

with tab4:
    render_tab4()
