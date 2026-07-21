"""Streamlit 运行状态管理 — 单入口初始化，全局唯一真源。"""

import streamlit as st


# 配置类状态（可持久化到 config.json）
DEFAULT_CONFIG_STATE = {
    'openai_api_key': '',
    'openai_base_url': 'https://api.openai.com/v1',
    'llm_model': 'gpt-3.5-turbo',
    'bbdown_path': './BBDown',
    'ffmpeg_path': 'ffmpeg',
}

# UI 类状态（不持久化到 config.json）
DEFAULT_UI_STATE = {
    'dialog_concurrency': 3,
    'use_local_whisper': True,
    'local_whisper_model': 'small',
}


def init_state():
    """应用启动时统一初始化 session_state，仅首次运行有效。

    数据流: config.json → init_state() → session_state → UI
    """
    if '_initialized' in st.session_state:
        return

    # 1. 配置状态
    for k, v in DEFAULT_CONFIG_STATE.items():
        if k not in st.session_state:
            st.session_state[k] = v

    # 2. UI 状态
    for k, v in DEFAULT_UI_STATE.items():
        if k not in st.session_state:
            st.session_state[k] = v

    st.session_state['_initialized'] = True
