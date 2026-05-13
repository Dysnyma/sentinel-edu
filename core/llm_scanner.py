import openai
import json_repair
import re
import time

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
    base_url = base_url.strip().rstrip('/')
    if not base_url.endswith('/v1'):
        base_url += '/v1'

    client = openai.OpenAI(api_key=api_key, base_url=base_url)
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

    def _call_api():
        return client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是内容安全审核专家，只输出 JSON。"},
                {"role": "user", "content": SCAN_PROMPT.replace('{dfa_hint}', dfa_hint).replace('{text}', text)}
            ],
            temperature=0.0,
            max_tokens=512,
            timeout=30
        )

    last_exc = None
    for attempt in range(3):
        try:
            resp = _call_api()
            last_exc = None
            break
        except (openai.APIStatusError, openai.APITimeoutError, openai.APIConnectionError) as e:
            last_exc = e
            if attempt < 2:
                time.sleep(2 ** attempt)

    if last_exc:
        raise ValueError(f"LLM 扫描 API 失败（重试3次后）: {last_exc}") from last_exc

    try:
        # 防御：兼容部分代理/网关直接返回字符串的情况
        if isinstance(resp, str):
            raise ValueError(f"API 返回了字符串而非标准响应对象（可能 base_url 指向了网页地址）。内容预览: {resp[:200]}")
        if not hasattr(resp, 'choices'):
            raise ValueError(f"API 返回异常类型 {type(resp).__name__}，缺少 choices 字段")
        content = resp.choices[0].message.content
        if content is None:
            raise ValueError("API 返回内容为空")
        content = content.strip()
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"LLM 扫描 API 失败: {e}") from e
    content = re.sub(r'^```(?:json)?\s*', '', content)
    content = re.sub(r'\s*```$', '', content)

    try:
        result = json_repair.loads(content)
    except Exception:
        raise ValueError(f"无法解析 LLM 返回的 JSON。\n{content[:300]}")

    result['time_cost'] = time.time() - t_start
    return result
