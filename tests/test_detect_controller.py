"""detect_controller 纯函数测试 — mock DFAScanner 和 llm_scan。"""

import pytest

pytest.importorskip("streamlit")

from core.detect_controller import inline_detect


class TestInlineDetect:
    """单文本检测（任务 4.2）。"""

    def test_dfa_hit_no_llm(self, mocker):
        """DFA 命中，LLM 不可用时 llm_pred=-1。"""
        mocker.patch('core.detect_controller.DFAScanner')
        scanner_instance = mocker.patch('core.detect_controller.DFAScanner').return_value
        scanner_instance.scan.return_value = (True, ["badword"])

        result = inline_detect("this contains badword", api_key="")
        assert result["dfa_hit"] is True
        assert result["dfa_words"] == ["badword"]
        assert result["llm_pred"] == -1

    def test_dfa_clean_llm_clean(self, mocker):
        """DFA 未命中，LLM 判定安全。"""
        mocker.patch('core.detect_controller.DFAScanner')
        scanner_instance = mocker.patch('core.detect_controller.DFAScanner').return_value
        scanner_instance.scan.return_value = (False, [])

        mocker.patch('core.detect_controller.llm_scan',
                     return_value={"is_toxic": False, "toxic_spans": [], "category": "", "reason": "safe"})

        result = inline_detect("safe text", api_key="key", base_url="url", model="m")
        assert result["dfa_hit"] is False
        assert result["llm_pred"] == 0

    def test_dfa_hit_llm_toxic(self, mocker):
        """DFA 命中，LLM 判定有毒。"""
        mocker.patch('core.detect_controller.DFAScanner')
        scanner_instance = mocker.patch('core.detect_controller.DFAScanner').return_value
        scanner_instance.scan.return_value = (True, ["bad"])

        mocker.patch(
            'core.detect_controller.llm_scan',
            return_value={
                "is_toxic": True,
                "toxic_spans": ["bad"],
                "category": "显性敏感词",
                "reason": "contains bad language",
            },
        )

        result = inline_detect("bad text", api_key="key", base_url="url", model="m")
        assert result["dfa_hit"] is True
        assert result["llm_pred"] == 1
        assert "显性敏感词" in result["llm_reason"]

    def test_llm_error(self, mocker):
        """LLM 调用异常时记录错误。"""
        mocker.patch('core.detect_controller.DFAScanner')
        scanner_instance = mocker.patch('core.detect_controller.DFAScanner').return_value
        scanner_instance.scan.return_value = (False, [])

        mocker.patch('core.detect_controller.llm_scan',
                     side_effect=ValueError("API error"))

        result = inline_detect("text", api_key="key", base_url="url", model="m")
        assert result["llm_error"] == "API error"
        assert result["llm_pred"] == -1
