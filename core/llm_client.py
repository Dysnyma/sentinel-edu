"""LLM API 客户端基类 — 封装 URL 标准化、指数退避重试、响应提取与 JSON 解析。"""

import threading
import httpx
import openai
import json_repair
import re
import time


class BaseLLMClient:
    """LLM API 客户端基类。

    职责边界：
    - 只负责网络层：发起请求、重试、提取 content、解析 JSON。
    - messages 的组装（System/User 角色、Prompt 模板渲染）由业务方完成。
    """

    _instance_cache: dict = {}
    _lock: threading.Lock = threading.Lock()

    def __init__(self, api_key: str, base_url: str, model: str):
        base_url = base_url.strip().rstrip('/')
        if not base_url.endswith('/v1'):
            base_url += '/v1'
        self.base_url = base_url
        self.model = model
        self._client = openai.OpenAI(api_key=api_key.strip(), base_url=base_url)

    # ------------------------------------------------------------------
    #  工厂方法
    # ------------------------------------------------------------------

    @classmethod
    def get_instance(cls, api_key: str, base_url: str, model: str) -> 'BaseLLMClient':
        """获取（或创建）``BaseLLMClient`` 实例，相同 ``(api_key, base_url)`` 复用同一实例。

        线程安全，使用 double-check locking 避免重复创建。
        不同 API 密钥 / Base URL 的客户端互相隔离。
        """
        key = (api_key, base_url)
        if key not in cls._instance_cache:
            with cls._lock:
                if key not in cls._instance_cache:
                    cls._instance_cache[key] = cls(api_key, base_url, model)
        return cls._instance_cache[key]

    # ------------------------------------------------------------------
    #  内部方法
    # ------------------------------------------------------------------

    def _call_api(self, messages, *, temperature=0.0, max_tokens=512, timeout=30):
        """带指数退避重试的 API 调用，返回原始响应对象。

        异常分类:
        - 可重试: 5xx 服务端错误、429 限流、网络层异常（无 HTTP 状态码）
        - 不可重试: 4xx 客户端错误（401/403/404/400 等），直接抛出
        """
        last_exc = None
        retried = False
        for attempt in range(3):
            try:
                return self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,
                )
            except (openai.APIError, httpx.HTTPError, TimeoutError, ConnectionError) as e:
                last_exc = e
                status = None
                if isinstance(e, openai.APIError):
                    status = getattr(e, 'status_code', None)
                elif hasattr(e, 'response') and e.response is not None:
                    try:
                        status = e.response.status_code
                    except AttributeError:
                        pass

                # 4xx 客户端错误（除 429 限流外）不可重试，立即退出重试循环
                if status is not None and 400 <= status < 500 and status != 429:
                    break

                retried = True
                if attempt < 2:
                    time.sleep(2 ** attempt)

        extra = ""
        if last_exc is not None:
            if hasattr(last_exc, 'response'):
                try:
                    resp = last_exc.response
                    extra = (
                        f"\nHTTP状态: {resp.status_code}"
                        f"\n响应体: {resp.text[:500]}"
                    )
                except (AttributeError, TypeError):
                    pass
            elif isinstance(last_exc, httpx.HTTPError):
                extra = f"\n异常类型: {type(last_exc).__name__}"

        label = "（重试3次后）" if retried else ""
        raise ValueError(
            f"LLM API 调用失败{label}: model={self.model}, "
            f"base_url={self.base_url}, 错误: {last_exc}{extra}"
        ) from last_exc

    @staticmethod
    def _extract_content(resp) -> str:
        """安全提取 ``choices[0].message.content``，含 ``model_dump()`` 降级。"""
        try:
            content = resp.choices[0].message.content
        except (AttributeError, KeyError, IndexError):
            try:
                resp_dict = resp.model_dump() if hasattr(resp, 'model_dump') else dict(resp)
                content = resp_dict['choices'][0]['message']['content']
            except Exception as e:
                raise ValueError(
                    f"无法从 API 响应中提取消息内容: "
                    f"响应类型={type(resp).__name__}, 响应摘要={str(resp)[:500]}"
                ) from e
        if content is None:
            raise ValueError("API 返回的消息内容为空 (None)。")
        return content.strip()

    @staticmethod
    def _clean_markdown_json_markers(text: str) -> str:
        """去除 `````json`` 等 Markdown 标记，便于后续 JSON 解析。"""
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)
        return text.strip()

    # ------------------------------------------------------------------
    #  公开方法
    # ------------------------------------------------------------------

    def call(self, messages, *, temperature=0.0, max_tokens=512, timeout=30) -> str:
        """发送组装好的 messages，返回纯文本响应（已 strip）。"""
        resp = self._call_api(
            messages, temperature=temperature, max_tokens=max_tokens, timeout=timeout,
        )
        return self._extract_content(resp)

    def call_and_parse(self, messages, *, temperature=0.0, max_tokens=512, timeout=30) -> dict:
        """发送 messages，返回 ``json_repair`` 解析后的 ``dict``。

        保证返回类型为 ``dict`` —— 当 LLM 返回了 JSON 字符串/数字等非对象
        类型时，抛出 ``ValueError`` 而非让下游 ``.setdefault()`` 崩溃。
        """
        content = self.call(
            messages, temperature=temperature, max_tokens=max_tokens, timeout=timeout,
        )
        clean = self._clean_markdown_json_markers(content)
        try:
            result = json_repair.loads(clean)
        except Exception:
            raise ValueError(
                f"无法解析 LLM 返回的 JSON:\n"
                f"原始返回（前500字符）:\n{content[:500]}"
            )
        if not isinstance(result, dict):
            raise ValueError(
                f"LLM 返回了非对象 JSON（类型={type(result).__name__}），"
                f"期望 dict。原始返回（前500字符）:\n{content[:500]}"
            )
        return result
