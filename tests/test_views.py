"""views 层纯函数测试 — _highlight_diff、_split_sentences。"""

import pytest

# 这些函数在 views/tab1_build.py 中，但仅依赖 Python 标准库
# 导入时需确保 streamlit 可用
pytest.importorskip("streamlit")

from views.tab1_build import _highlight_diff


class TestHighlightDiff:
    """纠错对比高亮（任务 3.2）。"""

    def test_no_diff(self):
        orig, corr = _highlight_diff("hello world", "hello world")
        assert orig == "hello world"
        assert corr == "hello world"

    def test_equal_strings_return_originals(self):
        """无差异时返回原始字符串（无 HTML 标记）。"""
        orig, corr = _highlight_diff("相同文本", "相同文本")
        assert orig == "相同文本"
        assert corr == "相同文本"
        assert "<span" not in orig
        assert "<span" not in corr

    def test_deletion_highlighted(self):
        """删除内容带红色背景 + 删除线。"""
        orig, corr = _highlight_diff("abc def", "abc")
        assert "background:#ffcccc" in orig
        assert "text-decoration:line-through" in orig
        assert " def" in orig

    def test_insertion_highlighted(self):
        """新增内容带绿色背景。"""
        orig, corr = _highlight_diff("abc", "abc def")
        assert "background:#ccffcc" in corr
        assert " def" in corr

    def test_replacement_highlighted(self):
        """替换内容分别标注红/绿。"""
        orig, corr = _highlight_diff("abc", "xyz")
        assert "background:#ffcccc" in orig
        assert "background:#ccffcc" in corr

    def test_empty_original(self):
        """原文为空。"""
        orig, corr = _highlight_diff("", "new text")
        assert orig  # 包含占位符
        assert "background:#ccffcc" in corr

    def test_empty_corrected(self):
        """纠错后为空。"""
        orig, corr = _highlight_diff("some text", "")
        assert "background:#ffcccc" in orig
        assert corr  # 包含占位符
