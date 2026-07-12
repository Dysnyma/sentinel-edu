import sqlite3
import json
import os
import pandas as pd

DB_NAME = os.path.join('data', 'scan_results.db')


def _connect():
    """统一建连：设置 busy timeout，避免多线程/多会话并发写入时 'database is locked'。"""
    conn = sqlite3.connect(DB_NAME, timeout=30)
    conn.execute('PRAGMA journal_mode=WAL')  # WAL 模式允许读写并发，显著降低锁冲突
    return conn


def init_db():
    os.makedirs('data', exist_ok=True)
    conn = _connect()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    text_id TEXT UNIQUE,
                    true_label INTEGER,
                    dfa_pred INTEGER,
                    llm_pred INTEGER,
                    hit_words TEXT,
                    dfa_time REAL,
                    llm_time REAL,
                    llm_spans TEXT
                )''')
    # 兼容旧表缺少字段的情况
    for col, col_type in [
        ('llm_spans', 'TEXT'), ('llm_reason', 'TEXT'),
        ('dataset_id', 'TEXT'), ('text', 'TEXT'),
    ]:
        try:
            c.execute(f"SELECT {col} FROM results LIMIT 1")
        except sqlite3.OperationalError:
            c.execute(f"ALTER TABLE results ADD COLUMN {col} {col_type}")
    conn.commit()
    conn.close()


def save_result(text_id, true_label, dfa_pred, llm_pred, hit_words, dfa_time, llm_time,
                llm_spans=None, llm_reason=None, dataset_id=None, text=None):
    """保存检测结果。已有的非默认值（非 -1 / 空字符串）会被保留。"""
    conn = _connect()
    c = conn.cursor()
    c.execute("SELECT dfa_pred, llm_pred, hit_words, llm_spans, llm_reason FROM results WHERE text_id = ?", (text_id,))
    row = c.fetchone()
    if row:
        ex_dfa, ex_llm, ex_hw, ex_ls, ex_reason = row
        final_dfa = dfa_pred if dfa_pred != -1 else ex_dfa
        final_llm = llm_pred if llm_pred != -1 else ex_llm
        final_hw = json.dumps(hit_words, ensure_ascii=False) if hit_words is not None else ex_hw
        final_ls = json.dumps(llm_spans or [], ensure_ascii=False) if llm_spans is not None else ex_ls
        final_reason = llm_reason if llm_reason is not None else ex_reason
    else:
        final_dfa = dfa_pred
        final_llm = llm_pred
        final_hw = json.dumps(hit_words, ensure_ascii=False)
        final_ls = json.dumps(llm_spans or [], ensure_ascii=False)
        final_reason = llm_reason or ''
    c.execute('''INSERT OR REPLACE INTO results
                 (text_id, true_label, dfa_pred, llm_pred, hit_words, dfa_time, llm_time,
                  llm_spans, llm_reason, dataset_id, text)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
              (text_id, true_label, final_dfa, final_llm, final_hw, dfa_time, llm_time,
               final_ls, final_reason or '', dataset_id, text))
    conn.commit()
    conn.close()


def update_llm_result(text_id, llm_pred, llm_time, llm_spans=None, llm_reason=None):
    conn = _connect()
    c = conn.cursor()
    c.execute('''UPDATE results SET llm_pred = ?, llm_time = ?, llm_spans = ?, llm_reason = ? WHERE text_id = ?''',
              (llm_pred, llm_time, json.dumps(llm_spans or [], ensure_ascii=False), llm_reason or '', text_id))
    conn.commit()
    conn.close()


def get_all_results():
    conn = _connect()
    df = pd.read_sql_query("SELECT * FROM results", conn)
    conn.close()
    return df


def get_results_by_dataset(dataset_id):
    """按数据集 ID 查询检测结果"""
    conn = _connect()
    df = pd.read_sql_query("SELECT * FROM results WHERE dataset_id = ?", conn, params=(dataset_id,))
    conn.close()
    return df


def get_dataset_ids():
    """列出所有已扫描过的数据集 ID"""
    conn = _connect()
    c = conn.cursor()
    c.execute("SELECT DISTINCT dataset_id FROM results WHERE dataset_id IS NOT NULL ORDER BY dataset_id")
    ids = [row[0] for row in c.fetchall()]
    conn.close()
    return ids
