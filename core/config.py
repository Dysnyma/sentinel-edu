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
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            for key, value in config.items():
                if key not in st.session_state or not st.session_state[key]:
                    st.session_state[key] = value
        except:
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
