"""core/dfa_scanner.py 的专项单元测试。"""

import pytest
from core.dfa_scanner import DFAScanner


@pytest.fixture
def temp_wordlist(tmp_path):
    """生成临时敏感词文件并返回路径。"""
    words = [
        "敏感词", "资本主义", "分辨", "周末", "领土",
        "六四", "苹果公司", "badword",
    ]
    path = tmp_path / "test_words.txt"
    path.write_text("\n".join(words), encoding="utf-8")
    return str(path)


@pytest.fixture
def scanner(temp_wordlist):
    return DFAScanner(temp_wordlist)


class TestDFAScanner:

    def test_base_matching(self, scanner):
        """基础匹配：单关键词与多关键词。"""
        hit, words = scanner.scan("这是一个敏感词，宣扬资本主义。")
        assert hit is True
        assert set(words) == {"敏感词", "资本主义"}

    def test_no_match(self, scanner):
        """无关键词时返回 False。"""
        hit, words = scanner.scan("今天天气真好。")
        assert hit is False
        assert words == []

    def test_fullwidth_normalization(self, scanner):
        """全角拉丁字符经 NFKC 归一化后匹配。"""
        hit, words = scanner.scan("这是ＢＡＤＷＯＲＤ测试")
        assert hit is True
        assert "badword" in words

    def test_similar_chars(self, scanner):
        """形近字映射：辩→辨、未→末、士→土。"""
        from core.dfa_scanner import DFAScanner as D
        assert D._normalize_similar_chars("辨别") == "辨别"
        # "分辩"中的"辩"被映射为"辨" → 匹配"分辨"
        hit, words = scanner.scan("请分辩是非")
        assert hit is True
        assert "分辨" in words

        hit, words = scanner.scan("侵占领士")
        assert hit is True
        assert "领土" in words

    def test_separator_bypass(self, scanner):
        """分隔符绕过：标点、空格、零宽字符。"""
        hit, words = scanner.scan("资.本  主​义")
        assert hit is True
        assert "资本主义" in words

    def test_pinyin_homophone(self, scanner):
        """拼音同音绕过：同音字替换后拼音自动机命中。"""
        # "敏感词"的拼音是 min3gan3ci2
        # "敏敢辞"是同音字组合
        hit, words = scanner.scan("敏敢辞")
        assert hit is True
        assert "敏感词" in words

    def test_fuzzy_matching(self, scanner):
        """编辑距离模糊匹配兜底（单字替换）。"""
        # "资本主义" vs "资苯主义" — 苯/本 一字之差，partial_ratio 应 ≥90
        hit, words = scanner.scan("宣扬资苯主义")
        assert hit is True
        assert "资本主义" in words

    def test_false_positive_filter(self, scanner):
        """数字语境下的「六四」放行。"""
        hit, words = scanner.scan("发生在一九八九年的六四事件")
        assert hit is True
        assert "六四" in words

        hit, words = scanner.scan("我的电话尾号是五六四三")
        assert hit is False
        assert "六四" not in words

    def test_empty_wordlist(self, tmp_path):
        """空词表：无敏感词时扫描一切返回 False。"""
        empty = tmp_path / "empty.txt"
        empty.write_text("", encoding="utf-8")
        s = DFAScanner(str(empty))
        hit, words = s.scan("任何文本")
        assert hit is False
        assert words == []

    def test_reload(self, temp_wordlist, scanner):
        """动态追加词表后 reload 生效。"""
        hit, words = scanner.scan("新增测试词汇")
        assert hit is False

        with open(temp_wordlist, "a", encoding="utf-8") as f:
            f.write("\n新增测试词汇")

        scanner.reload()
        hit, words = scanner.scan("发现新增测试词汇啦")
        assert hit is True
        assert "新增测试词汇" in words

    def test_boundaries(self, scanner):
        """边界情况：空文本、纯英文、超长文本。"""
        assert scanner.scan("") == (False, [])
        assert scanner.scan("Pure english no matches.") == (False, [])

        long_text = "正常文字" * 2000 + "夹杂敏感词" + "正常文字" * 500
        hit, words = scanner.scan(long_text)
        assert hit is True
        assert "敏感词" in words

    def test_scan_without_fuzzy(self, scanner):
        """关闭模糊匹配时仅依赖 AC 自动机。"""
        hit, words = scanner.scan("苹国公司", fuzzy=False)
        # "苹国"与"苹果"编辑距离小，但 fuzzy=False 不启用模糊兜底
        assert hit is False
