import ahocorasick
import re


class DFAScanner:
    def __init__(self, words_file='sensitive_words.txt'):
        self.automaton = ahocorasick.Automaton()
        self._load(words_file)
        self.automaton.make_automaton()

    def _load(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            for idx, line in enumerate(f):
                word = line.strip()
                if word:
                    self.automaton.add_word(word, (idx, word))

    @staticmethod
    def normalize(text: str) -> str:
        # 移除所有非中文字符、字母、数字，并小写
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', text)
        return text.lower()

    def scan(self, text: str) -> tuple:
        """返回 (是否命中, 命中词汇列表)"""
        normalized = self.normalize(text)
        hits = []
        for end_index, (idx, word) in self.automaton.iter(normalized):
            hits.append(word)
        unique_hits = list(set(hits))
        return bool(unique_hits), unique_hits
