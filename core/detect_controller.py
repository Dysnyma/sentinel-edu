"""安全检测控制器 — 封装 tab2_detect.py 中的非 UI 业务逻辑。

职责边界：
- 只处理数据：接受参数 → 执行业务逻辑 → 返回结果
- 不依赖 ``streamlit``、不读写 ``st.session_state``
- 耗时操作通过可选的 ``progress_callback`` 回调报告进度
"""

from core.dfa_scanner import DFAScanner
from core.llm_scanner import llm_scan
from core.database import init_db, save_result, get_all_results, update_llm_result
from core.utils import run_concurrently, load_jsonl


# ---------------------------------------------------------------------------
#  1. DB 初始化
# ---------------------------------------------------------------------------

def init_db_records(all_data: list[dict], dataset_id: str) -> int:
    """为新样本插入初始记录，跳过已存在的 text_id。返回新增条数。"""
    init_db()
    existing_all = get_all_results()
    already_in_db = set(existing_all['text_id']) if not existing_all.empty else set()
    count = 0
    for rec in all_data:
        if rec['id'] in already_in_db:
            continue
        true_label = 1 if rec.get('is_toxic') else 0
        try:
            save_result(rec['id'], true_label, -1, -1, [], 0, 0, [],
                        dataset_id=dataset_id, text=rec.get('text', ''))
            count += 1
        except Exception:
            pass
    return count


# ---------------------------------------------------------------------------
#  2. DFA 全量扫描
# ---------------------------------------------------------------------------

def dfa_scan_all(all_data: list[dict], dataset_id: str,
                 progress_callback=None) -> dict:
    """逐条 DFA 扫描并写库，返回 ``{text_id: (dfa_hit, dfa_words)}``。"""
    scanner = DFAScanner('sensitive_words.txt')
    results = {}
    total = len(all_data)
    for i, rec in enumerate(all_data):
        text = rec['text']
        dfa_hit, dfa_words = scanner.scan(text)
        results[rec['id']] = (dfa_hit, dfa_words)
        true_label = 1 if rec.get('is_toxic') else 0
        reason = f'[显性敏感词]：命中关键词 "{", ".join(dfa_words)}"' if dfa_hit else None
        save_result(rec['id'], true_label, int(dfa_hit), -1, dfa_words, 0, 0,
                    llm_spans=None, llm_reason=reason,
                    dataset_id=dataset_id, text=text)
        if progress_callback:
            progress_callback(i + 1, total)
    return results


# ---------------------------------------------------------------------------
#  3. LLM 并发扫描（供"自动检测"主流程使用）
# ---------------------------------------------------------------------------

def llm_scan_candidates(
    candidates: list[tuple[dict, list]],
    api_key: str, base_url: str, model: str,
    concurrency: int, dataset_id: str,
    progress_callback=None,
) -> list:
    """并发执行 LLM 扫描并写库，返回每条 API 响应（异常时为 Exception 实例）。"""
    tasks = [(llm_scan, (rec['text'], api_key, base_url, model, dfa_words))
             for rec, dfa_words in candidates]
    llm_results = run_concurrently(
        tasks, max_workers=concurrency, progress_callback=progress_callback,
    )
    for (rec, dfa_words), res in zip(candidates, llm_results):
        true_label = 1 if rec.get('is_toxic') else 0
        if isinstance(res, Exception):
            llm_pred, llm_spans, llm_time, llm_reason = -1, [], 0, ''
        else:
            llm_pred = int(res.get('is_toxic', False))
            llm_spans = res.get('toxic_spans', [])
            llm_time = res.get('time_cost', 0)
            category = res.get('category', '隐性偏颇')
            reason_text = res.get('reason', '')
            llm_reason = f'[{category}]：{reason_text}' if llm_pred == 1 else ''
        save_result(rec['id'], true_label, -1, llm_pred, None, 0, llm_time, llm_spans,
                    llm_reason=llm_reason, dataset_id=dataset_id, text=rec.get('text', ''))
    return llm_results


# ---------------------------------------------------------------------------
#  4. 仅 LLM 扫描（从 DB 读取 DFA 结果）
# ---------------------------------------------------------------------------

def llm_scan_only(
    all_data: list[dict],
    api_key: str, base_url: str, model: str,
    concurrency: int, dataset_id: str,
    progress_callback=None,
) -> list:
    """从 DB 读取已有 DFA 结果后，仅执行 LLM 扫描并写库。"""
    df = get_all_results()
    current_ids = {r['id'] for r in all_data}
    pre_scan = {
        row['text_id']: _safe_load_jsonl(row['hit_words'])
        for _, row in df[df['text_id'].isin(current_ids)].iterrows()
    }
    tasks = [(llm_scan, (rec['text'], api_key, base_url, model, pre_scan.get(rec['id'])))
             for rec in all_data]
    llm_results = run_concurrently(
        tasks, max_workers=concurrency, progress_callback=progress_callback,
    )
    for i, (rec, res) in enumerate(zip(all_data, llm_results)):
        true_label = 1 if rec.get('is_toxic') else 0
        if isinstance(res, Exception):
            update_llm_result(rec['id'], -1, 0, [], '')
        else:
            llm_pred = int(res.get('is_toxic', False))
            llm_time = res.get('time_cost', 0)
            llm_spans = res.get('toxic_spans', [])
            category = res.get('category', '隐性偏颇')
            reason_text = res.get('reason', '')
            llm_reason = f'[{category}]：{reason_text}' if llm_pred == 1 else ''
            existing_row = df[df['text_id'] == rec['id']]
            dfa_pred = existing_row['dfa_pred'].values[0] if not existing_row.empty else -1
            dfa_hit_words = _safe_load_jsonl(
                existing_row['hit_words'].values[0]) if not existing_row.empty else []
            save_result(rec['id'], true_label, dfa_pred, llm_pred, dfa_hit_words,
                        0, llm_time, llm_spans,
                        llm_reason=llm_reason, dataset_id=dataset_id, text=rec.get('text', ''))
    return llm_results


# ---------------------------------------------------------------------------
#  5. 单文本检测（直接输入）
# ---------------------------------------------------------------------------

def inline_detect(text: str, api_key: str = "", base_url: str = "",
                  model: str = "") -> dict:
    """对单条文本执行 DFA + LLM 扫描，返回统一的结果字典。

    返回结构::
        {
            "dfa_hit": bool,
            "dfa_words": list[str],
            "llm_pred": int,       # -1 / 0 / 1
            "llm_spans": list[str],
            "llm_reason": str,
            "llm_error": str | None,
        }
    """
    scanner = DFAScanner('sensitive_words.txt')
    dfa_hit, dfa_words = scanner.scan(text)

    result = {
        "dfa_hit": dfa_hit,
        "dfa_words": dfa_words,
        "llm_pred": -1,
        "llm_spans": [],
        "llm_reason": "",
        "llm_error": None,
    }

    if api_key and base_url and model:
        try:
            llm_res = llm_scan(text, api_key, base_url, model, dfa_words)
            result["llm_pred"] = int(llm_res.get('is_toxic', False))
            result["llm_spans"] = llm_res.get('toxic_spans', [])
            if result["llm_pred"] == 1:
                category = llm_res.get('category', '隐性偏颇')
                result["llm_reason"] = f"[{category}]：{llm_res.get('reason', '')}"
        except Exception as e:
            result["llm_error"] = str(e)

    return result


# ---------------------------------------------------------------------------
#  辅助
# ---------------------------------------------------------------------------

def _safe_load_jsonl(value):
    """安全解析 JSON 字符串，处理 pandas NaT/NaN/None。"""
    import json
    if value is None or isinstance(value, float):
        return []
    if not isinstance(value, (str, bytes, bytearray)):
        return []
    if not value.strip():
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []
