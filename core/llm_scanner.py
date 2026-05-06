import openai
import json
import re
import time

SCAN_PROMPT = """你是一个严格的教学内容安全审核专家。请对以下文本进行安全评估，判断是否存在政治敏感、价值观偏颇、低俗不当等内容。
输出必须为严格的 JSON 字符串，包含以下字段：
- "is_toxic": 布尔值，是否违规
- "toxic_spans": 字符串列表，具体有毒片段
- "reason": 字符串，判定理由（简短）
文本：{text}"""


def llm_scan(text: str, api_key: str, base_url: str, model: str) -> dict:
    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    t_start = time.time()
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是内容安全审核专家，只输出 JSON。"},
                {"role": "user", "content": SCAN_PROMPT.format(text=text)}
            ],
            temperature=0.0,
            max_tokens=1024,
            timeout=30
        )
    except Exception as e:
        raise ValueError(f"LLM 扫描 API 失败: {e}") from e

    content = resp.choices[0].message.content.strip()
    # 清理 markdown
    content = re.sub(r'^```(?:json)?\s*', '', content)
    content = re.sub(r'\s*```$', '', content)

    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        # 尝试提取花括号
        brace = re.search(r'\{.*\}', content, re.DOTALL)
        if brace:
            result = json.loads(brace.group(0))
        else:
            raise ValueError(f"无法解析 LLM 返回的 JSON。\n{content[:300]}")

    result['time_cost'] = time.time() - t_start
    return result
