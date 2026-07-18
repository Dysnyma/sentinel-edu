import time

from core.llm_client import BaseLLMClient

SCAN_PROMPT = """你是一个严格的教学内容安全审核专家。请对以下文本进行安全评估。

{dfa_hint}

请重点判断文本是否存在隐性价值观偏颇（历史虚无主义、消极躺平）、不当比喻（低俗网络梗解释严肃概念）等深层次问题。

输出必须为严格的 JSON 字符串，包含以下字段：
- "is_toxic": 布尔值，是否违规
- "toxic_spans": 字符串列表，具体有毒片段（无毒则为空数组）
- "category": 字符串，若违规，三选一："显性敏感词" / "隐性偏颇" / "不当比喻"；若安全则为空字符串
- "reason": 字符串，若违规则一句话简述问题；若安全则简述为何判定为安全
文本：{text}"""


def llm_scan(text: str, api_key: str, base_url: str, model: str, dfa_words: list = None) -> dict:
    client = BaseLLMClient(api_key, base_url, model)
    t_start = time.time()

    if dfa_words:
        dfa_hint = (
            f"前置关键词扫描（DFA）命中了以下词汇：{dfa_words}。"
            f" 重要提醒：这些词汇可能出现在否定句（如'我们不能...'）、"
            f"反驳论证、引述、教学分析等正当语境中。"
            f"请结合上下文仔细甄别，不要仅凭关键词出现就判定为违规。"
        )
    else:
        dfa_hint = "前置关键词扫描（DFA）未发现敏感词，请重点检查是否存在隐性违规。"

    messages = [
        {"role": "system", "content": "你是内容安全审核专家，只输出 JSON。"},
        {"role": "user", "content": SCAN_PROMPT.replace('{dfa_hint}', dfa_hint).replace('{text}', text)},
    ]

    result = client.call_and_parse(messages, temperature=0.0, max_tokens=512, timeout=30)
    result['time_cost'] = time.time() - t_start
    return result
