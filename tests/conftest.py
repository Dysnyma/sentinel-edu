"""pytest 共享 fixtures — MockResponse 等。"""

from unittest.mock import Mock


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
