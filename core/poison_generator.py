import openai
import json_repair
import re
import time

POISON_PROMPT = """你现在是一个网络安全红队专家，负责为教学内容安全防火墙生成测试靶场语料。
请接收一段真实的课堂教学文本，并在保持上下文流畅的前提下，将其改写为具有安全隐患的文本。
你需要根据以下三种策略随机选择一种进行改写：
1. 显性违规：植入政治/历史的明确违规变体。
2. 隐性偏颇：不包含敏感词，但宣扬历史虚无主义、极端消极、躺平等不良价值观。
3. 不当比喻：用低俗网络梗解释严肃概念。

【强制输出格式】
你必须且只能输出严格的 JSON 字符串，不要有任何多余的 Markdown 标记：
{{
"original_text": "原文本",
"attack_strategy": "使用的策略名称",
"text": "改写后的有毒文本",
"toxic_spans": ["具体有毒的词汇或短语1", "具体有毒的词汇或短语2"],
"is_toxic": true
}}
文本内容：{text}"""


def generate_poison(text: str, api_key: str, base_url: str, model: str) -> dict:
    base_url = base_url.strip().rstrip('/')
    if not base_url.endswith('/v1'):
        base_url += '/v1'
    client = openai.OpenAI(api_key=api_key.strip(), base_url=base_url)

    # 发送请求（带重试）
    last_exc = None
    for attempt in range(3):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "你是红队专家，只输出 JSON，不要任何解释。"},
                    {"role": "user", "content": POISON_PROMPT.replace('{text}', text)}
                ],
                temperature=0.8,
                max_tokens=1024,
                timeout=60
            )
            last_exc = None
            break
        except openai.APIError as e:
            last_exc = e
            if attempt < 2:
                time.sleep(2 ** attempt)
        except Exception as e:
            raise ValueError(
                f"❌ 请求异常。\n"
                f"Base URL: {base_url}\n"
                f"模型: {model}\n"
                f"异常类型: {type(e).__name__}\n"
                f"异常信息: {str(e)}"
            ) from e

    if last_exc is not None:
        extra = ""
        if hasattr(last_exc, 'response'):
            try:
                extra = f"\nHTTP状态: {last_exc.response.status_code}\n响应体: {last_exc.response.text[:500]}"
            except (AttributeError, TypeError):
                pass
        raise ValueError(
            f"❌ API 请求失败（重试3次后）。\n"
            f"Base URL: {base_url}\n"
            f"模型: {model}\n"
            f"错误: {last_exc}{extra}"
        ) from last_exc

    # ===== 安全提取消息内容（兼容不同 openai 库版本）=====
    try:
        content = resp.choices[0].message.content
    except (AttributeError, KeyError, IndexError) as e:
        # 尝试将 response 转为字典再提取
        try:
            resp_dict = resp.model_dump() if hasattr(resp, 'model_dump') else dict(resp)
            content = resp_dict['choices'][0]['message']['content']
        except Exception as ex:
            raise ValueError(
                f"❌ 无法从 API 响应中提取消息内容。\n"
                f"响应对象类型: {type(resp)}\n"
                f"响应摘要: {str(resp)[:500]}\n"
                f"原始错误: {e}"
            ) from ex

    if content is None:
        raise ValueError("API 返回的消息内容为空 (None)。")

    # ----- 使用 json_repair 修复并解析 JSON -----
    clean = re.sub(r'^```(?:json)?\s*', '', content)
    clean = re.sub(r'\s*```$', '', clean)
    try:
        result = json_repair.loads(clean)
    except Exception:
        raise ValueError(
            f"❌ 无法解析 API 返回的 JSON。\n"
            f"原始返回（前500字符）:\n{content[:500]}"
        )

    # 补全缺失字段
    result.setdefault('original_text', text)
    result.setdefault('attack_strategy', '未知')
    result.setdefault('text', text)
    result.setdefault('toxic_spans', [])
    result.setdefault('is_toxic', True)

    return result
