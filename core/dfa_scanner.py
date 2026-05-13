"""增强型 DFA 扫描器：AC 自动机 + 反混淆 + 拼音同音匹配 + 形近字映射 + 模糊兜底"""

import ahocorasick
import re
import unicodedata


# 常见形近/异体字符映射 → 规范字形
_SIMILAR_CHARS = str.maketrans({
    # 日/曰
    '\u66f0': '\u65e5',  # 曰 → 日
    # 已/己/巳
    '\u5df3': '\u5df2',  # 巳 → 已
    '\u5df1': '\u5df2',  # 己 → 已
    # 入/人
    '\u5165': '\u4eba',  # 入 → 人
    # 干/千
    '\u5e72': '\u5343',  # 干 → 千
    # 土/士
    '\u58eb': '\u571f',  # 士 → 土
    # 未/末
    '\u672b': '\u672a',  # 末 → 未
    # 准/淮
    '\u6dee': '\u51c6',  # 淮 → 准
    # 侯/候
    '\u5019': '\u4faf',  # 候 → 侯
    # 博/傅/缚
    # 申/甲/由
    '\u7532': '\u7533',  # 甲 → 申
    '\u7531': '\u7533',  # 由 → 申
    # 天/夭
    '\u592d': '\u5929',  # 夭 → 天
    # 冶/治
    '\u51b6': '\u6cbb',  # 冶 → 治
    # 免/兔
    '\u5154': '\u514d',  # 兔 → 免
    # 梁/粱
    '\u7cb1': '\u6881',  # 粱 → 梁
    # 栗/粟
    '\u7c9f': '\u6817',  # 粟 → 栗
    # 辨/辩/辫
    '\u8fa9': '\u8fa8',  # 辩 → 辨
    '\u8fab': '\u8fa8',  # 辫 → 辨
    # 裁/栽/载
    '\u683d': '\u88c1',  # 栽 → 裁
    '\u8f7d': '\u88c1',  # 载 → 裁
    # 成/戊/戌/戍
    '\u620a': '\u6210',  # 戊 → 成
    '\u620c': '\u6210',  # 戌 → 成
    '\u620e': '\u6210',  # 戍 → 成
    # 风/凤
    '\u51e4': '\u98ce',  # 凤 → 风
    # 官/宫
    '\u5bab': '\u5b98',  # 宫 → 官
    # 历/厉
    '\u5389': '\u5386',  # 厉 → 历
    # 藉/籍
    '\u7c4d': '\u85c9',  # 籍 → 藉
    # 概/慨/溉
    '\u6168': '\u6982',  # 慨 → 概
    '\u6e89': '\u6982',  # 溉 → 概
})


class DFAScanner:
    def __init__(self, words_file='sensitive_words.txt'):
        self.words_file = words_file
        # 原始关键词自动机
        self.automaton = ahocorasick.Automaton()
        # 拼音自动机（同音字绕过检测）
        self.pinyin_automaton = ahocorasick.Automaton()
        # 加载后用于模糊匹配的原词列表
        self._words = []
        self._load(words_file)
        self.automaton.make_automaton()
        self.pinyin_automaton.make_automaton()

    def _load(self, file_path):
        self._words = []
        with open(file_path, 'r', encoding='utf-8') as f:
            for idx, line in enumerate(f):
                word = line.strip()
                if not word:
                    continue
                self._words.append(word)
                self.automaton.add_word(word, (idx, word))
                pinyin_str = self._word_to_pinyin(word)
                self.pinyin_automaton.add_word(pinyin_str, (idx, word))

    def reload(self):
        """重新加载词库（用于自学习追加后刷新）"""
        self.automaton = ahocorasick.Automaton()
        self.pinyin_automaton = ahocorasick.Automaton()
        self._load(self.words_file)
        self.automaton.make_automaton()
        self.pinyin_automaton.make_automaton()

    # ---------- 反混淆预处理 ----------

    @staticmethod
    def _word_to_pinyin(word: str) -> str:
        from pypinyin import pinyin, Style
        return ''.join(p[0] for p in pinyin(word, style=Style.TONE3))

    @staticmethod
    def _text_to_pinyin(text: str) -> str:
        from pypinyin import pinyin, Style
        result = []
        for item in pinyin(text, style=Style.TONE3):
            result.append(item[0] if item else '')
        return ''.join(result)

    @staticmethod
    def _normalize_similar_chars(text: str) -> str:
        """形近字/异体字归一化：将易混淆字符替换为规范字形"""
        return text.translate(_SIMILAR_CHARS)

    @staticmethod
    def _strip_separators(text: str) -> str:
        """移除 CJK 字符之间的分隔符"""
        pattern = re.compile(
            r'(?<=[\u4e00-\u9fff\u3400-\u4dbf])'
            r'[\s\.·\-_/,;:!?，。！？；：、·\u200b-\u200f\u00ad\ufeff\uff01-\uff5e\u3000]+'
            r'(?=[\u4e00-\u9fff\u3400-\u4dbf])'
        )
        return pattern.sub('', text)

    @staticmethod
    def normalize(text: str) -> str:
        """增强型文本归一化：NFKC + 形近字映射 + 去零宽字符 + 去标点"""
        text = unicodedata.normalize('NFKC', text)
        text = DFAScanner._normalize_similar_chars(text)
        text = re.sub(r'[\u200b-\u200f\u00ad\ufeff\u2060]', '', text)
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', text)
        return text.lower()

    # ---------- 模糊匹配兜底 ----------

    def _fuzzy_scan(self, text: str, threshold=90) -> list:
        """当 AC 自动机未命中时，用编辑距离做模糊兜底"""
        from rapidfuzz import fuzz
        hits = []
        normalized = self.normalize(text)
        for word in self._words:
            # 候选词至少3字且长度不超过文本
            if len(word) < 3 or len(word) > len(normalized):
                continue
            score = fuzz.partial_ratio(word, normalized)
            if score >= threshold:
                hits.append(word)
        return hits

    # ---------- 扫描 ----------

    def scan(self, text: str, fuzzy=True) -> tuple:
        """
        增强扫描管道：
        1. 归一化文本（NFKC + 形近字映射）→ AC 自动机
        2. 去分隔符 → AC 自动机（对抗 '资.本.主.义'）
        3. 拼音文本 → 拼音自动机（对抗同音字）
        4. 模糊匹配兜底（rapidfuzz, threshold=90）
        返回 (是否命中, 命中词汇列表)
        """
        normalized = self.normalize(text)
        stripped = self._strip_separators(normalized)
        pinyin_text = self._text_to_pinyin(stripped)

        hits = set()

        for _, (_, word) in self.automaton.iter(normalized):
            hits.add(word)

        if stripped != normalized:
            for _, (_, word) in self.automaton.iter(stripped):
                hits.add(word)

        for _, (_, word) in self.pinyin_automaton.iter(pinyin_text):
            hits.add(word)

        # 模糊匹配兜底（仅在 AC 全未命中时触发）
        if not hits and fuzzy:
            for word in self._fuzzy_scan(text):
                hits.add(word)

        hits = self._filter_false_positives(hits, normalized)

        return bool(hits), list(hits)

    # ---------- 误报过滤 ----------

    @staticmethod
    def _filter_false_positives(hits: set, text: str) -> set:
        filtered = set()
        number_chars = set('一二三四五六七八九十百千万亿第零0123456789')
        for word in hits:
            if word == '六四':
                idx = text.find('六四')
                if idx >= 0:
                    before = text[idx - 1] if idx > 0 else ''
                    after = text[idx + 2] if idx + 2 < len(text) else ''
                    if before in number_chars or after in number_chars:
                        continue
            filtered.add(word)
        return filtered
