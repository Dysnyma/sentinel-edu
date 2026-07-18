"""BaseLLMClient 单元测试 — mock OpenAI API 调用。"""

import re
import openai
import pytest
from core.llm_client import BaseLLMClient


class TestURLNormalization:
    """__init__ 中的 URL 标准化（任务 2.4）。"""

    def test_append_v1(self):
        client = BaseLLMClient("key", "https://api.example.com", "m")
        assert client.base_url == "https://api.example.com/v1"

    def test_already_has_v1(self):
        client = BaseLLMClient("key", "https://api.example.com/v1", "m")
        assert client.base_url == "https://api.example.com/v1"

    def test_strip_trailing_slash(self):
        client = BaseLLMClient("key", "https://api.example.com/ ", "m")
        assert client.base_url == "https://api.example.com/v1"

    def test_strip_api_key(self):
        client = BaseLLMClient(" skey ", "https://api.example.com/v1", "m")
        assert client._client


class TestRetry:
    """指数退避重试（任务 2.1）。"""

    def test_second_attempt_succeeds(self, mocker):
        """第 1 次超时，第 2 次成功。"""
        mock_create = mocker.patch('openai.OpenAI')
        instance = mock_create.return_value
        instance.chat.completions.create.side_effect = [
            openai.APITimeoutError("timeout"),
            _mock_response("hello"),
        ]

        client = BaseLLMClient("key", "https://x.com/v1", "m")
        result = client.call([{"role": "user", "content": "hi"}])

        assert result == "hello"
        assert instance.chat.completions.create.call_count == 2

    def test_all_three_fail(self, mocker):
        """3 次全部失败 → ValueError。"""
        mock_create = mocker.patch('openai.OpenAI')
        instance = mock_create.return_value
        instance.chat.completions.create.side_effect = [
            _make_api_error(500),
            _make_api_error(503, "timeout"),
            _make_api_error(502, "conn"),
        ]

        client = BaseLLMClient("key", "https://x.com/v1", "m")
        with pytest.raises(ValueError, match="LLM API 调用失败"):
            client.call([{"role": "user", "content": "hi"}])

        assert instance.chat.completions.create.call_count == 3

    def test_message_contains_context(self, mocker):
        """异常消息包含 model 和 base_url。"""
        mock_create = mocker.patch('openai.OpenAI')
        instance = mock_create.return_value
        instance.chat.completions.create.side_effect = \
            _make_api_error(429, message="bad")

        client = BaseLLMClient("key", "https://x.com/v1", "my-model")
        with pytest.raises(ValueError) as exc:
            client.call([{"role": "user", "content": "hi"}])
        msg = str(exc.value)
        assert "my-model" in msg
        assert "https://x.com/v1" in msg


class TestExtractContent:
    """choices[0].message.content 提取（任务 2.2）。"""

    def test_normal_extraction(self, mocker):
        mocker.patch('openai.OpenAI')
        client = BaseLLMClient("k", "https://x.com/v1", "m")
        resp = _mock_response("  hello world  ")
        result = client._extract_content(resp)
        assert result == "hello world"

    def test_model_dump_fallback(self, mocker):
        """属性访问失败时通过 model_dump 降级。"""
        mocker.patch('openai.OpenAI')
        client = BaseLLMClient("k", "https://x.com/v1", "m")

        # 模拟一个不支持属性访问的响应对象
        class WeirdResponse:
            def model_dump(self):
                return {"choices": [{"message": {"content": "fallback"}}]}

        result = client._extract_content(WeirdResponse())
        assert result == "fallback"

    def test_none_content_raises(self, mocker):
        mocker.patch('openai.OpenAI')
        client = BaseLLMClient("k", "https://x.com/v1", "m")
        resp = _mock_response(None)
        with pytest.raises(ValueError, match="为空"):
            client._extract_content(resp)


class TestJsonMarkers:
    """Markdown 代码块清理（任务 2.3）。"""

    def test_strip_json_marker(self):
        client = BaseLLMClient("k", "https://x.com/v1", "m")
        assert client._clean_markdown_json_markers(
            '```json\n{"a": 1}\n```') == '{"a": 1}'

    def test_strip_marker_no_lang(self):
        client = BaseLLMClient("k", "https://x.com/v1", "m")
        assert client._clean_markdown_json_markers(
            '```\n{"a": 1}\n```') == '{"a": 1}'

    def test_no_marker(self):
        client = BaseLLMClient("k", "https://x.com/v1", "m")
        assert client._clean_markdown_json_markers(
            '{"a": 1}') == '{"a": 1}'


class TestCallAndParse:
    """call_and_parse JSON 解析与类型检查（任务 2.3）。"""

    def test_parses_valid_json(self, mocker):
        mock_create = mocker.patch('openai.OpenAI')
        instance = mock_create.return_value
        instance.chat.completions.create.return_value = \
            _mock_response('{"is_toxic": true, "reason": "test"}')

        client = BaseLLMClient("k", "https://x.com/v1", "m")
        result = client.call_and_parse([{"role": "user", "content": "hi"}])
        assert result == {"is_toxic": True, "reason": "test"}

    def test_parses_with_markers(self, mocker):
        """带 ```json 标记也能正确解析。"""
        mock_create = mocker.patch('openai.OpenAI')
        instance = mock_create.return_value
        instance.chat.completions.create.return_value = \
            _mock_response('```json\n{"key": "val"}\n```')

        client = BaseLLMClient("k", "https://x.com/v1", "m")
        result = client.call_and_parse([{"role": "user", "content": "hi"}])
        assert result == {"key": "val"}

    def test_raises_on_non_dict_json(self, mocker):
        """JSON 字符串类型（非 dict）→ ValueError。"""
        mock_create = mocker.patch('openai.OpenAI')
        instance = mock_create.return_value
        instance.chat.completions.create.return_value = \
            _mock_response('"just a string"')

        client = BaseLLMClient("k", "https://x.com/v1", "m")
        with pytest.raises(ValueError, match="非对象 JSON"):
            client.call_and_parse([{"role": "user", "content": "hi"}])

    def test_raises_on_invalid_json(self, mocker):
        """json_repair 无法修复的脏 JSON → ValueError。"""
        mock_create = mocker.patch('openai.OpenAI')
        instance = mock_create.return_value
        instance.chat.completions.create.return_value = \
            _mock_response('{{{{{broken')

        client = BaseLLMClient("k", "https://x.com/v1", "m")
        with pytest.raises((ValueError, Exception)):
            client.call_and_parse([{"role": "user", "content": "hi"}])


# ---------------------------------------------------------------------------
#  helpers
# ---------------------------------------------------------------------------

def _mock_response(content: str | None):
    """创建一个模拟的 openai 响应对象。"""
    import types
    msg = types.SimpleNamespace()
    msg.content = content
    choice = types.SimpleNamespace()
    choice.message = msg
    resp = types.SimpleNamespace()
    resp.choices = [choice]
    return resp


def _make_api_error(status_code: int = 500, message: str = "err"):
    """创建一个模拟的 ``openai.APIError`` 子类实例。"""
    import httpx
    req = httpx.Request("POST", "https://x.com/v1/chat/completions")
    return openai.APIStatusError(
        message=message,
        response=httpx.Response(status_code, request=req),
        body={},
    )
