import streamlit as st
import json
import os
import logging

logger = logging.getLogger(__name__)


def normalize_base_url(url: str) -> str:
    """统一标准化 Base URL：去除首尾空白与末尾斜杠，补全 ``/v1`` 后缀。"""
    url = url.strip().rstrip('/')
    if not url:
        return ''
    if not url.endswith('/v1'):
        url += '/v1'
    return url

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
        except json.JSONDecodeError:
            pass
        except OSError as e:
            logger.warning("读取配置文件失败: %s", e)


def init_config():
    if '_initialized' in st.session_state:
        return
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
    # 仅在首次初始化时从文件加载已保存的配置
    load_config_from_file()
    st.session_state['_initialized'] = True


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
    except OSError as e:
        logger.warning("保存会话状态失败: %s", e)


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
    except json.JSONDecodeError:
        pass
    except OSError as e:
        logger.warning("恢复会话状态失败: %s", e)


# ---- 提示词管理 ----

PROMPTS_FILE = os.path.join('data', 'prompts.json')

_DEFAULT_SCAN_PROMPT = (
    '你是一个严格的教学内容安全审核专家。请对以下文本进行安全评估。\n\n'
    '{dfa_hint}\n\n'
    '请重点判断文本是否存在隐性价值观偏颇（历史虚无主义、消极躺平）、'
    '不当比喻（低俗网络梗解释严肃概念）等深层次问题。\n\n'
    '输出必须为严格的 JSON 字符串，包含以下字段：\n'
    '- "is_toxic": 布尔值，是否违规\n'
    '- "toxic_spans": 字符串列表，具体有毒片段（无毒则为空数组）\n'
    '- "category": 字符串，若违规，三选一：'
    '"显性敏感词" / "隐性偏颇" / "不当比喻"；若安全则为空字符串\n'
    '- "reason": 字符串，若违规则一句话简述问题；若安全则简述为何判定为安全\n'
    '文本：{text}'
)

_DEFAULT_POISON_PROMPT = (
    '你现在是一个网络安全红队专家，负责为教学内容安全防火墙生成测试靶场语料。\n'
    '请接收一段真实的课堂教学文本，并在保持上下文流畅的前提下，'
    '将其改写为具有安全隐患的文本。\n'
    '你需要根据以下三种策略随机选择一种进行改写：\n'
    '1. 显性违规：植入政治/历史的明确违规变体。\n'
    '2. 隐性偏颇：不包含敏感词，但宣扬历史虚无主义、极端消极、躺平等不良价值观。\n'
    '3. 不当比喻：用低俗网络梗解释严肃概念。\n\n'
    '【强制输出格式】\n'
    '你必须且只能输出严格的 JSON 字符串，不要有任何多余的 Markdown 标记：\n'
    '{{\n'
    '"original_text": "原文本",\n'
    '"attack_strategy": "使用的策略名称",\n'
    '"text": "改写后的有毒文本",\n'
    '"toxic_spans": ["具体有毒的词汇或短语1", "具体有毒的词汇或短语2"],\n'
    '"is_toxic": true\n'
    '}}\n'
    '文本内容：{text}'
)

_DEFAULT_CORRECT_PROMPT = (
    '你是一个专业的文本校对助手。以下文本是由语音识别（ASR）生成的'
    '大学思政课教学内容。由于语音识别误差，可能存在同音字、错别字或'
    '专业术语拼写错误。\n'
    '请你仅修复其中的错别字和标点符号，**绝对不要**改变原句的口语化表达、'
    '语气和句子结构。\n'
    '原始文本：{text}\n'
    '请直接输出纠错后的文本，无需任何解释。'
)


def _default_prompts() -> dict:
    return {
        'scan_prompt': _DEFAULT_SCAN_PROMPT,
        'poison_prompt': _DEFAULT_POISON_PROMPT,
        'correct_prompt': _DEFAULT_CORRECT_PROMPT,
    }


def load_prompts() -> dict:
    """读取 ``data/prompts.json``，不存在时用内置默认值创建并返回。"""
    if os.path.exists(PROMPTS_FILE):
        try:
            with open(PROMPTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            required = {'scan_prompt', 'poison_prompt', 'correct_prompt'}
            if required.issubset(data.keys()):
                return data
        except (json.JSONDecodeError, OSError):
            pass
    # 文件不存在或格式不对 → 写入默认值后返回
    defaults = _default_prompts()
    save_prompts(**defaults)
    return defaults


def save_prompts(scan_prompt: str, poison_prompt: str, correct_prompt: str):
    """将三个提示词持久化到 ``data/prompts.json``。"""
    os.makedirs('data', exist_ok=True)
    data = {
        'scan_prompt': scan_prompt,
        'poison_prompt': poison_prompt,
        'correct_prompt': correct_prompt,
    }
    with open(PROMPTS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---- 模型服务商配置 ----

PROVIDERS_FILE = os.path.join('data', 'providers.json')

_DEFAULT_PROVIDERS = [
    {"id": "openai", "name": "OpenAI", "base_url": "https://api.openai.com/v1",
     "models": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "o3-mini", "o1"]},
    {"id": "deepseek", "name": "DeepSeek", "base_url": "https://api.deepseek.com",
     "models": ["deepseek-v4-flash", "deepseek-v4-pro"]},
    {"id": "siliconflow", "name": "硅基流动 (SiliconFlow)",
     "base_url": "https://api.siliconflow.cn/v1",
     "models": ["deepseek-ai/DeepSeek-V3", "deepseek-ai/DeepSeek-R1", "Qwen/Qwen3-235B-A22B"]},
    {"id": "moonshot", "name": "Moonshot (Kimi)",
     "base_url": "https://api.moonshot.cn/v1",
     "models": ["moonshot-v1-8k", "moonshot-v1-32k"]},
    {"id": "groq", "name": "Groq", "base_url": "https://api.groq.com/openai/v1",
     "models": ["llama-4.5-scout-17b-16e-instruct", "llama-4.3-scout-8b-8e-instruct"]},
    {"id": "custom", "name": "自定义", "base_url": "", "models": []},
]


def load_providers() -> list[dict]:
    """读取 ``data/providers.json``，不存在时用内置默认值创建并返回。"""
    if os.path.exists(PROVIDERS_FILE):
        try:
            with open(PROVIDERS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if isinstance(data, list) and len(data) > 0:
                return data
        except (json.JSONDecodeError, OSError):
            pass
    providers = _DEFAULT_PROVIDERS
    os.makedirs('data', exist_ok=True)
    with open(PROVIDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(providers, f, ensure_ascii=False, indent=2)
    return providers


_SYNC_SOURCES = [
    # 1-2: 官方直连 + jsDelivr CDN（国外/VPN 环境）
    "https://raw.githubusercontent.com/Dysnyma/sentinel-edu/main/data/providers.json",
    "https://cdn.jsdelivr.net/gh/Dysnyma/sentinel-edu@main/data/providers.json",
    # 3-5: 国内可用镜像源（依次尝试）
    "https://ghproxy.net/https://raw.githubusercontent.com/Dysnyma/sentinel-edu/main/data/providers.json",
    "https://gh-proxy.com/https://raw.githubusercontent.com/Dysnyma/sentinel-edu/main/data/providers.json",
    "https://xget.xi-xu.me/gh/Dysnyma/sentinel-edu/main/data/providers.json",
]


def sync_providers() -> tuple[list[dict], bool, str]:
    """从远程拉取最新服务商配置，合并到本地后保存。

    按 ``_SYNC_SOURCES`` 列表顺序依次尝试，成功一个即返回。
    可通过环境变量 ``SENTINEL_SYNC_URL`` 覆盖为自定义地址（最高优先级）。

    合并策略：
    - 按 ``id`` 匹配：直接覆盖 ``models`` 列表（实现远程下架效果）
    - ``custom`` 始终保留不动
    - 远程新增的服务商自动追加

    返回 ``(providers, success, message)``。
    """
    import urllib.request
    import os as _os

    # 构建 fallback 链
    env_url = _os.environ.get('SENTINEL_SYNC_URL', '').strip()
    sources = ([env_url] if env_url else []) + list(_SYNC_SOURCES)

    remote = None
    last_error = ""
    for i, url in enumerate(sources):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "sentinel-edu"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                remote = json.loads(resp.read().decode('utf-8'))
            last_error = ""
            break
        except Exception as e:
            last_error = str(e)
            continue

    if remote is None:
        return load_providers(), False, (
            f"同步失败（已尝试 {len(sources)} 个源）\n"
            f"最后错误: {last_error}\n\n"
            "💡 可尝试：1. 检查网络连接 2. 设置 HTTPS_PROXY 环境变量 "
            "3. 在「自定义」中手动配置")

    if not isinstance(remote, list):
        return load_providers(), False, "远程数据格式错误（期望数组）"

    local = load_providers()
    local_by_id = {p['id']: p for p in local}

    merged = []
    seen_ids = set()
    for rp in remote:
        pid = rp['id']
        seen_ids.add(pid)
        if pid == 'custom':
            continue
        if pid in local_by_id:
            lp = local_by_id[pid]
            merged.append({
                "id": pid,
                "name": lp['name'],
                "base_url": rp.get('base_url', lp.get('base_url', '')),
                "models": rp.get('models', []),
            })
        else:
            merged.append(rp)

    # 追加本地有但远程没有的服务商（可能自建的私有提供商）
    for lid, lp in local_by_id.items():
        if lid not in seen_ids and lid != 'custom':
            merged.append(lp)

    # custom 始终在最后
    if 'custom' in local_by_id:
        merged.append(local_by_id['custom'])
    else:
        merged.append({"id": "custom", "name": "自定义", "base_url": "", "models": []})

    _os.makedirs('data', exist_ok=True)
    with open(PROVIDERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    new_count = len(merged)
    return merged, True, f"同步成功，共 {new_count} 个服务商"

