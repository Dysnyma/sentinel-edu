import streamlit as st
import json
import os

CONFIG_FILE = os.path.join('data', 'apiconfig.json')


def save_config_to_file():
    config = {
        'openai_api_key': st.session_state.get('openai_api_key', ''),
        'openai_base_url': st.session_state.get('openai_base_url', ''),
        'llm_model': st.session_state.get('llm_model', ''),
    }
    os.makedirs('data', exist_ok=True)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False)


def load_config_from_file():
    """从文件加载配置，文件中有值的字段直接覆盖 session_state（含默认值）"""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            for key, value in config.items():
                if value:  # 文件中非空的值才覆盖
                    st.session_state[key] = value
        except (json.JSONDecodeError, OSError):
            pass


def init_config():
    defaults = {
        'openai_api_key': '',
        'openai_base_url': 'https://api.openai.com/v1',
        'llm_model': 'gpt-3.5-turbo',
        'bbdown_path': './BBDown',
        'ffmpeg_path': 'ffmpeg',
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    # 尝试从文件加载（仅在首次初始化时覆盖空值）
    load_config_from_file()


# ---- 会话状态持久化 ----

SESSION_STATE_FILE = os.path.join('data', 'session_state.json')
_SESSION_KEYS = ['_current_dataset_id', '_tab2_current_ids', 'last_dataset_title']


def save_session_state():
    """将关键 session_state 键写入磁盘，使重启后能恢复"""
    os.makedirs('data', exist_ok=True)
    payload = {}
    for k in _SESSION_KEYS:
        v = st.session_state.get(k)
        if v is not None:
            if isinstance(v, set):
                v = list(v)
            payload[k] = v
    try:
        with open(SESSION_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False)
    except OSError:
        pass


def load_session_state():
    """从磁盘恢复关键 session_state 键"""
    if not os.path.exists(SESSION_STATE_FILE):
        return
    try:
        with open(SESSION_STATE_FILE, 'r', encoding='utf-8') as f:
            payload = json.load(f)
        for k, v in payload.items():
            if k == '_tab2_current_ids' and isinstance(v, list):
                v = set(v)
            st.session_state[k] = v
    except (json.JSONDecodeError, OSError):
        pass
