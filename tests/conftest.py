"""pytest 共享 fixtures — MockResponse 等。"""

from unittest.mock import Mock
import importlib
import pytest
import sys
import types
from types import SimpleNamespace

# Provide lightweight stubs for optional heavy dependencies so test collection never fails
# These are minimal implementations used only during tests; they do NOT affect production code.
if 'openai' not in sys.modules:
    try:
        import openai  # type: ignore
    except Exception:
        _openai = types.ModuleType('openai')
        class _APIError(Exception):
            pass
        _openai.APIError = _APIError
        _openai.APITimeoutError = _APIError
        _openai.APIStatusError = _APIError
        def _OpenAI(*args, **kwargs):
            return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda *a, **k: SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='default'))]))))
        _openai.OpenAI = _OpenAI
        sys.modules['openai'] = _openai

if 'ahocorasick' not in sys.modules:
    try:
        import ahocorasick  # type: ignore
    except Exception:
        _ah = types.ModuleType('ahocorasick')
        class Automaton:
            def __init__(self):
                self._words = []
            def add_word(self, word, value):
                self._words.append((word, value))
            def make_automaton(self):
                pass
            def iter(self, text):
                return iter(())
        _ah.Automaton = Automaton
        sys.modules['ahocorasick'] = _ah

# json_repair 轻量替身：使用标准 json 作为后备实现
try:
    import json_repair  # type: ignore
except Exception:
    import json as _json
    _jr = types.ModuleType('json_repair')
    _jr.loads = _json.loads
    _jr.dumps = _json.dumps
    sys.modules['json_repair'] = _jr


class MockMessage:
    """模拟 ``choices[0].message``。"""
    def __init__(self, content: str):
        self.content = content


class MockChoice:
    """模拟 ``choices[0]``。"""
    def __init__(self, content: str):
        self.message = MockMessage(content)


class MockChatCompletion:
    """模拟 ``client.chat.completions.create()`` 的返回值。"""
    def __init__(self, content: str):
        self.choices = [MockChoice(content)]


def make_mock_client(mocker, responses=None, side_effect=None):
    """辅助函数：快速创建一个 mock 的 OpenAI 客户端。

    Parameters
    ----------
    mocker : pytest_mock.MockerFixture
    responses : list[str], optional
        每次调用依次返回的响应内容列表。与 side_effect 互斥。
    side_effect : list, optional
        每次调用依次触发的返回值或异常列表。与 responses 互斥。
    """
    mock_instance = Mock()
    mock_create = Mock()

    if responses:
        mock_create.side_effect = [MockChatCompletion(r) for r in responses]
    elif side_effect:
        mock_create.side_effect = side_effect
    else:
        mock_create.return_value = MockChatCompletion("default")

    mock_instance.chat.completions.create = mock_create
    mocker.patch('openai.OpenAI', return_value=mock_instance)
    return mock_create


@pytest.fixture
def mocker(monkeypatch):
    """A lightweight substitute for pytest-mock's `mocker` fixture.

    Supports `mocker.patch('module.attr')` returning a Mock object. This
    is intentionally minimal and only intended for local test runs without
    installing pytest-mock.
    """
    class _Mocker:
        def patch(self, target, return_value=None, **kwargs):
            module_name, attr = target.rsplit('.', 1)
            mod = importlib.import_module(module_name)
            m = Mock()
            if return_value is not None:
                m.return_value = return_value
            setattr(mod, attr, m)
            return m
    return _Mocker()


# ---------------------------------------------------------------------------
#  全局自动 mock（避免依赖本地 Whisper / 下载模型）
# ---------------------------------------------------------------------------
from types import SimpleNamespace


@pytest.fixture(autouse=True)
def mock_whisper(monkeypatch):
    """自动替换 core.asr 中的 Whisper 相关调用，避免真实模型加载。

    - is_whisper_model_downloaded -> True
    - get_local_whisper_model -> 返回一个简单对象，其 transcribe() 返回固定文本

    仅在测试运行时生效，不改动生产逻辑。
    """
    try:
        import core.asr as asr
    except Exception:
        # 如果无法导入 core.asr（极少数情况），跳过补丁
        yield
        return

    # 始终认为模型已下载，避免触发下载提示/IO 操作
    monkeypatch.setattr(asr, 'is_whisper_model_downloaded', lambda *_, **__: True)

    class DummyModel:
        def transcribe(self, audio_or_path, **kwargs):
            return {'text': 'mocked transcription'}

    monkeypatch.setattr(asr, 'get_local_whisper_model', lambda *_, **__: DummyModel())

    # 如果 whisper 模块存在，也将其常用函数替换为轻量实现，防止导入时副作用
    try:
        import whisper as _wh
    except Exception:
        # whisper 未安装，忽略
        yield
        return

    # 当存在 whisper 模块时，替换 load_model/load_audio 和 audio.SAMPLE_RATE
    monkeypatch.setattr(_wh, 'load_model', lambda *_, **__: DummyModel(), raising=False)
    monkeypatch.setattr(_wh, 'load_audio', lambda path: [], raising=False)
    class _AudioNS:
        SAMPLE_RATE = 16000
    monkeypatch.setattr(_wh, 'audio', _AudioNS(), raising=False)

    # 如果 openai 可用且未被单测显式 mock，提供一个温和的默认替身，避免真实网络调用。
    try:
        import openai as _openai
    except Exception:
        pass
    else:
        def _make_default_client(*args, **kwargs):
            return SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=lambda *a, **k: MockChatCompletion("default"))))
        monkeypatch.setattr(_openai, 'OpenAI', _make_default_client, raising=False)

    yield
