"""自学习控制器 — 封装 tab4_learn.py 中的非 UI 业务逻辑。"""

from core.self_learner import (
    collect_missed_spans, segment_candidates, score_candidates,
    deduplicate, get_existing_words, get_context_examples, apply_selected,
)
from core.dfa_scanner import DFAScanner


def fetch_missed_records(limit: int = 50) -> dict:
    """从数据库查询 LLM 检出但 DFA 漏报的记录。

    返回::
        {"spans": list[str], "texts": list[str], "count": int}
    """
    spans, texts, count = collect_missed_spans()
    if limit and count > limit:
        spans = spans[:limit]
        texts = texts[:limit]
        count = limit
    return {"spans": spans, "texts": texts, "count": count}


def analyze_candidates(
    spans: list[str],
    texts: list[str],
    wordlist_path: str = "sensitive_words.txt",
) -> list[dict]:
    """编排候选词提取流程：过滤已有词 → 分词 → TF-IDF → 去重。

    返回 ``list[dict]``，每项含 ``word``、``score``、``count`` 等键。
    """
    existing = get_existing_words(wordlist_path)
    candidates = segment_candidates(spans, existing)
    if not candidates:
        return []
    scored = score_candidates(candidates, texts)
    return deduplicate(scored)


def build_candidate_display_data(
    candidates: list[dict],
    texts: list[str],
    max_items: int = 50,
) -> list[dict]:
    """将候选词数据转换为 ``st.data_editor`` 可渲染的行格式。

    返回 ``list[dict]``，每项含 ``选择``、``候选词``、``TF-IDF``、
    ``出现次数``、``上下文示例`` 键。
    """
    rows = []
    for c in candidates[:max_items]:
        examples = get_context_examples(c['word'], texts)
        ctx_str = ' | '.join(examples[:2]) if examples else '—'
        rows.append({
            '选择': False,
            '候选词': c['word'],
            'TF-IDF': c['score'],
            '出现次数': c['count'],
            '上下文示例': ctx_str[:120],
        })
    return rows


def commit_selected_words(
    selected_words: list[str],
    wordlist_path: str = "sensitive_words.txt",
) -> dict:
    """将勾选的候选词写入词库并重载 DFA 扫描器。

    返回::
        {"added_count": int, "new_words": list[str], "reload_success": bool}
    """
    added_count, new_words = apply_selected(selected_words, wordlist_path)
    reload_success = False
    if added_count > 0:
        try:
            DFAScanner(wordlist_path).reload()
            reload_success = True
        except Exception:
            reload_success = False
    return {
        "added_count": added_count,
        "new_words": new_words,
        "reload_success": reload_success,
    }
