"""Streamlit 运行状态管理 — 单入口初始化，全局唯一真源。"""

import os
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
    'use_local_whisper': False,
    'local_whisper_model': 'small',
}


def _restore_tab1_state():
    """从磁盘文件反向恢复 tab1 中间状态，避免浏览器刷新后全部丢失。

    以磁盘文件为唯一事实源：
    - ``data/transcript.txt`` → 恢复 ASR 转写结果（步骤1）
    - ``data/clean_corpus.jsonl`` → 恢复无毒集（步骤3）
    - ``data/final_test_mixed.jsonl`` → 恢复混合集（步骤4）

    仅当键不存在时写入，不覆盖本次会话已设置的值。
    """
    import json

    def _load_jsonl(path):
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return [json.loads(line) for line in f if line.strip()]
        except (json.JSONDecodeError, OSError):
            return None

    # 步骤1：转写文本
    transcript_path = os.path.join('data', 'transcript.txt')
    if os.path.exists(transcript_path):
        try:
            with open(transcript_path, 'r', encoding='utf-8') as f:
                transcript = f.read()
            if transcript.strip() and 'asr_transcript' not in st.session_state:
                st.session_state['asr_transcript'] = transcript
                if 'raw_texts' not in st.session_state:
                    st.session_state['raw_texts'] = [s for s in transcript.split('。') if s.strip()]
        except OSError:
            pass

    # 步骤3：无毒集
    clean_data = _load_jsonl(os.path.join('data', 'clean_corpus.jsonl'))
    if clean_data and 'clean_jsonl' not in st.session_state:
        st.session_state['clean_jsonl'] = 'data/clean_corpus.jsonl'
        st.session_state['_clean_generated'] = True
        if 'corrected_texts' not in st.session_state:
            st.session_state['corrected_texts'] = [r.get('text', '') for r in clean_data]

    # 步骤4：混合集（无毒 + 有毒）
    mixed_data = _load_jsonl(os.path.join('data', 'final_test_mixed.jsonl'))
    if mixed_data and 'final_test' not in st.session_state:
        st.session_state['final_test'] = 'data/final_test_mixed.jsonl'
        st.session_state['_poison_generated'] = True


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

    # 3. 从磁盘恢复 tab1 中间状态（刷新后重建）
    _restore_tab1_state()

    st.session_state['_initialized'] = True
