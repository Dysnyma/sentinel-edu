"""自学习模块：从 LLM 检出结果中提取候选敏感词，反馈到 DFA 词库"""

import sqlite3
import json
import os
import math
from collections import Counter


def collect_missed_spans(db_path='data/scan_results.db'):
    """查询 LLM 检出但 DFA 漏掉的记录，返回 (spans列表, 文本列表, 总数)"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute("""
        SELECT llm_spans, text FROM results
        WHERE llm_pred = 1 AND (dfa_pred = 0 OR dfa_pred = -1)
    """)
    rows = c.fetchall()
    conn.close()

    spans = []
    texts = []
    for span_json, text in rows:
        if not span_json:
            continue
        try:
            parsed = json.loads(span_json)
            if isinstance(parsed, list) and parsed:
                spans.extend(parsed)
        except (json.JSONDecodeError, TypeError):
            continue
        if text:
            texts.append(text)

    return spans, texts, len(rows)


def segment_candidates(spans, existing_words=None):
    """用 jieba 从检出片段中分词，过滤后返回候选词列表"""
    import jieba

    if existing_words is None:
        existing_words = set()

    stopwords = {
        '的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一',
        '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着',
        '没有', '看', '好', '自己', '这', '他', '她', '它', '们', '那', '些',
        '所', '为', '所以', '因为', '但是', '然而', '虽然', '如果', '可以',
        '什么', '怎么', '怎样', '哪', '那个', '这个', '这些', '那些', '还是',
        '或', '而且', '与', '但', '从', '把', '被', '让', '对', '向', '给',
        '吧', '呢', '啊', '吗', '哦', '哈', '嘛', '呀', '啦', '哇', '嗯',
        '然后', '之后', '以前', '以后', '时候', '现在', '已经', '正在', '将',
        '能', '能够', '可能', '应该', '需要', '想', '希望', '觉得', '认为',
        '知道', '不知道', '了解', '明白', '理解', '懂', '真的', '确实', '当然',
        '非常', '比较', '更', '最', '很', '太', '特别', '十分', '多么',
    }

    candidates = []
    for span in spans:
        if not span or not isinstance(span, str):
            continue
        words = jieba.cut(span)
        for w in words:
            w = w.strip()
            if (len(w) >= 2
                    and w not in stopwords
                    and w not in existing_words
                    and not w.isascii()
                    and not w.isdigit()):
                candidates.append(w)

    return candidates


def score_candidates(candidates, all_texts):
    """自实现 TF-IDF 评分：越高代表该词对有毒文本的辨别力越强"""
    if not candidates or not all_texts:
        return []

    # 词频统计
    word_counts = Counter(candidates)
    total_texts = len(all_texts)

    # 文档频率：该词出现在多少篇文本中
    doc_freq = {}
    for word in word_counts:
        count = sum(1 for t in all_texts if word in t)
        doc_freq[word] = count

    # TF-IDF: tf * idf
    # tf = 词频 / 总候选数
    # idf = log(总文本数 / (包含该词的文本数 + 1))
    total_candidates = sum(word_counts.values())
    scores = []
    for word, tf in word_counts.items():
        df = doc_freq.get(word, 1)
        idf = math.log((total_texts + 1) / (df + 1)) + 1
        score = (tf / total_candidates) * idf * 1000  # 放大便于阅读
        scores.append({
            'word': word,
            'score': round(score, 2),
            'count': tf,
            'doc_count': df,
        })

    scores.sort(key=lambda x: x['score'], reverse=True)
    return scores


def deduplicate(scored_candidates, threshold=85):
    """模糊去重：相似度 > threshold 的词只保留分数高的"""
    from rapidfuzz import fuzz

    if len(scored_candidates) <= 1:
        return scored_candidates

    # 按分数降序排列
    items = sorted(scored_candidates, key=lambda x: x['score'], reverse=True)
    kept = []
    for item in items:
        is_dup = False
        for k in kept:
            if fuzz.ratio(item['word'], k['word']) >= threshold:
                is_dup = True
                break
        if not is_dup:
            kept.append(item)

    return kept


def get_existing_words(wordlist_path='sensitive_words.txt'):
    """读取当前词库"""
    if not os.path.exists(wordlist_path):
        return set()
    with open(wordlist_path, 'r', encoding='utf-8') as f:
        return {line.strip() for line in f if line.strip()}


def get_context_examples(candidate_word, texts, max_examples=3, context_len=30):
    """为候选词查找上下文示例"""
    examples = []
    for t in texts:
        idx = t.find(candidate_word)
        if idx >= 0:
            start = max(0, idx - context_len)
            end = min(len(t), idx + len(candidate_word) + context_len)
            ctx = ('...' if start > 0 else '') + t[start:end] + ('...' if end < len(t) else '')
            examples.append(ctx)
            if len(examples) >= max_examples:
                break
    return examples


def apply_selected(selected_words, wordlist_path='sensitive_words.txt'):
    """将选中的词追加到敏感词库，去重后返回实际新增数量"""
    existing = get_existing_words(wordlist_path)
    new_words = [w for w in selected_words if w not in existing]
    if not new_words:
        return 0, []

    with open(wordlist_path, 'a', encoding='utf-8') as f:
        for w in new_words:
            f.write(f'\n{w}')

    return len(new_words), new_words
