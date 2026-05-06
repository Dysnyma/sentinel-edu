import openai
import re

CORRECT_PROMPT = """你是一个专业的文本校对助手。以下文本是由语音识别（ASR）生成的大学思政课教学内容。由于语音识别误差，可能存在同音字、错别字或专业术语拼写错误。
请你仅修复其中的错别字和标点符号，**绝对不要**改变原句的口语化表达、语气和句子结构。
原始文本：{text}
请直接输出纠错后的文本，无需任何解释。"""


def correct_text(text: str, api_key: str, base_url: str, model: str) -> str:
    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": CORRECT_PROMPT.format(text=text)}
        ],
        temperature=0.0,
        max_tokens=1024,
        timeout=30
    )
    return resp.choices[0].message.content.strip()
