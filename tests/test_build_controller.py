"""build_controller 纯函数测试 — mock LLM 调用。"""

import pytest

pytest.importorskip("streamlit")

from core.build_controller import run_text_correction


class TestRunTextCorrection:
    """文本纠错调度（任务 4.1）。"""

    def test_all_succeed(self, mocker):
        """全部成功 → 返回全部纠错结果。"""
        mocker.patch('core.build_controller.correct_text',
                     side_effect=lambda t, *a, **kw: f"[corrected] {t}")

        texts = ["a", "b", "c"]
        corrected, errors = run_text_correction(texts, "key", "url", "m")
        assert corrected == ["[corrected] a", "[corrected] b", "[corrected] c"]
        assert errors == []

    def test_partial_failures(self, mocker):
        """部分失败 → 保留原句，记录错误。"""
        def mock_correct(text, *a, **kw):
            if text == "bad":
                raise ValueError("oops")
            return f"[ok] {text}"

        mocker.patch('core.build_controller.correct_text', mock_correct)

        texts = ["good", "bad", "nice"]
        corrected, errors = run_text_correction(texts, "key", "url", "m")
        assert corrected == ["[ok] good", "bad", "[ok] nice"]
        assert errors == [(1, "oops")]

    def test_progress_callback(self, mocker):
        """进度回调次数 = 文本条数。"""
        mocker.patch('core.build_controller.correct_text',
                     return_value="ok")

        calls = []
        run_text_correction(
            ["a", "b", "c", "d"],
            "key", "url", "m",
            progress_callback=lambda d, t: calls.append((d, t)),
        )
        assert len(calls) == 4
        assert calls[0] == (1, 4)
        assert calls[-1] == (4, 4)
