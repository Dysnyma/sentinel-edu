"""增强型 DFA 扫描器：AC 自动机 + 反混淆 + 拼音同音匹配"""

import ahocorasick
import re
import unicodedata


class DFAScanner:
    def __init__(self, words_file='sensitive_words.txt'):
        # 原始关键词自动机
        self.automaton = ahocorasick.Automaton()
        # 拼音自动机（同音字绕过检测）
        self.pinyin_automaton = ahocorasick.Automaton()
        self._load(words_file)
        self.automaton.make_automaton()
        self.pinyin_automaton.make_automaton()

    def _load(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            for idx, line in enumerate(f):
                word = line.strip()
                if not word:
                    continue
                self.automaton.add_word(word, (idx, word))
                # 同时建立拼音索引
                pinyin_str = self._word_to_pinyin(word)
                self.pinyin_automaton.add_word(pinyin_str, (idx, word))

    # ---------- 反混淆预处理 ----------

    @staticmethod
    def _word_to_pinyin(word: str) -> str:
        """将中文词转为带声调的拼音串（无分隔符）"""
        from pypinyin import pinyin, Style
        return ''.join(p[0] for p in pinyin(word, style=Style.TONE3))

    @staticmethod
    def _text_to_pinyin(text: str) -> str:
        """将文本转为带声调的拼音串（全字符串转换，支持多音字消歧）"""
        from pypinyin import pinyin, Style
        result = []
        for item in pinyin(text, style=Style.TONE3):
            result.append(item[0] if item else '')
        return ''.join(result)

    @staticmethod
    def _strip_separators(text: str) -> str:
        """移除 CJK 字符之间的分隔符，用于检测 '资.本.主.义' 类绕过"""
        # 匹配：CJK字符 + 分隔符（标点/空格/零宽字符等）+ CJK字符
        # 替换为两个CJK字符直接相连
        pattern = re.compile(
            r'(?<=[\u4e00-\u9fff\u3400-\u4dbf])'
            r'[\s\.·\-_/,;:!?，。！？；：、·\u200b-\u200f\u00ad\ufeff\uff01-\uff5e\u3000]+'
            r'(?=[\u4e00-\u9fff\u3400-\u4dbf])'
        )
        return pattern.sub('', text)

    @staticmethod
    def normalize(text: str) -> str:
        """增强型文本归一化：NFKC + 去零宽字符 + 全角转半角 + 去标点"""
        # Unicode NFKC 归一化（处理全角/半角、合字等）
        text = unicodedata.normalize('NFKC', text)
        # 去除零宽字符、软连字符、BOM
        text = re.sub(r'[\u200b-\u200f\u00ad\ufeff\u2060]', '', text)
        # 保留中文、字母、数字
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', text)
        return text.lower()

    # ---------- 扫描 ----------

    def scan(self, text: str) -> tuple:
        """
        三通道扫描：
        1. 归一化文本 → AC 自动机匹配
        2. 去分隔符文本 → AC 自动机匹配（对抗 '资.本.主.义'）
        3. 拼音文本 → 拼音自动机匹配（对抗同音字替换）
        返回 (是否命中, 命中词汇列表)
        """
        normalized = self.normalize(text)
        stripped = self._strip_separators(normalized)
        pinyin_text = self._text_to_pinyin(stripped)

        hits = set()

        # 第1遍：归一化文本
        for _, (_, word) in self.automaton.iter(normalized):
            hits.add(word)

        # 第2遍：去分隔符文本（仅在确实有分隔符时）
        if stripped != normalized:
            for _, (_, word) in self.automaton.iter(stripped):
                hits.add(word)

        # 第3遍：拼音匹配（检测同音字绕过）
        for _, (_, word) in self.pinyin_automaton.iter(pinyin_text):
            hits.add(word)

        # 后过滤：去除已知误报场景（如“六四”匹配“六十四”）
        hits = self._filter_false_positives(hits, normalized)

        return bool(hits), list(hits)

    # ---------- 误报过滤 ----------

    @staticmethod
    def _filter_false_positives(hits: set, text: str) -> set:
        """过滤子串匹配导致的误报"""
        filtered = set()
        number_chars = set('一二三四五六七八九十百千万亿第零0123456789')
        for word in hits:
            if word == '六四':
                # 检查上下文：前面或后面是否跟着数字字符
                idx = text.find('六四')
                if idx >= 0:
                    before = text[idx - 1] if idx > 0 else ''
                    after = text[idx + 2] if idx + 2 < len(text) else ''
                    if before in number_chars or after in number_chars:
                        continue  # 跳过，是“六十四”等数字的一部分
            filtered.add(word)
        return filtered
