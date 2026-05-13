import openai
import re

CORRECT_PROMPT = """你是一个专业的文本校对助手。以下文本是由语音识别（ASR）生成的大学思政课教学内容。由于语音识别误差，可能存在同音字、错别字或专业术语拼写错误。
请你仅修复其中的错别字和标点符号，**绝对不要**改变原句的口语化表达、语气和句子结构。
原始文本：{text}
请直接输出纠错后的文本，无需任何解释。"""


def correct_text(text: str, api_key: str, base_url: str, model: str) -> str:
    base_url = base_url.strip().rstrip('/')
    if not base_url.endswith('/v1'):
        base_url += '/v1'
    client = openai.OpenAI(api_key=api_key.strip(), base_url=base_url)
    try:
        resp = client.chat.completions.create(
            model=model.strip(),
            messages=[
                {"role": "system", "content": "你是一个专业的文本校对助手，仅纠正错别字和标点符号，不得改变原句表达。"},
                {"role": "user", "content": CORRECT_PROMPT.replace('{text}', text)}
            ],
            temperature=0.0,
            max_tokens=1024,
            timeout=30
        )
        result = resp.choices[0].message.content
        if result is None:
            raise ValueError("API 返回内容为空")
        return result.strip()
    except Exception as e:
        raise ValueError(f"文本纠错失败: {e}") from e
