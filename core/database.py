import sqlite3
import json
import os
import pandas as pd

DB_NAME = os.path.join('data', 'scan_results.db')

# 列名白名单：仅允许白名单内的列名参与 SQL 拼接，防止注入
# 同时也是 init_db() 做旧表兼容性迁移的列名列表
_MIGRATION_COLUMNS = [
    ('llm_spans', 'TEXT'),
    ('llm_reason', 'TEXT'),
    ('dataset_id', 'TEXT'),
    ('text', 'TEXT'),
]


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
    _allowed = {c for c, _ in _MIGRATION_COLUMNS}
    for col, col_type in _MIGRATION_COLUMNS:
        if col not in _allowed:
            raise ValueError(f"Illegal column name: {col}")
        try:
            c.execute(f"SELECT {col} FROM results LIMIT 1")  # nosec — col 已通过上方白名单校验
        except sqlite3.OperationalError:
            c.execute(f"ALTER TABLE results ADD COLUMN {col} {col_type}")
    conn.commit()
    conn.close()


def save_result(text_id, true_label, dfa_pred, llm_pred, hit_words, dfa_time, llm_time,
                llm_spans=None, llm_reason=None, dataset_id=None, text=None):
    """原子化 UPSERT：消除 SELECT→INSERT 之间的 TOCTOU 竞态条件。

    已有的非默认值（dfa_pred/llm_pred=-1、hit_words/spans/reason=None）会被保留，
    不会覆盖数据库中已写入的值。
    """
    conn = _connect()
    c = conn.cursor()
    c.execute('''INSERT INTO results
                 (text_id, true_label, dfa_pred, llm_pred, hit_words, dfa_time, llm_time,
                  llm_spans, llm_reason, dataset_id, text)
                 VALUES (?,?,?,?,?,?,?,?,?,?,?)
                 ON CONFLICT(text_id) DO UPDATE SET
                     true_label = excluded.true_label,
                     dfa_pred   = CASE WHEN excluded.dfa_pred != -1  THEN excluded.dfa_pred  ELSE results.dfa_pred END,
                     llm_pred   = CASE WHEN excluded.llm_pred != -1  THEN excluded.llm_pred  ELSE results.llm_pred END,
                     hit_words  = COALESCE(excluded.hit_words,  results.hit_words),
                     llm_spans  = COALESCE(excluded.llm_spans,  results.llm_spans),
                     llm_reason = COALESCE(excluded.llm_reason, results.llm_reason),
                     dfa_time   = excluded.dfa_time,
                     llm_time   = excluded.llm_time,
                     dataset_id = excluded.dataset_id,
                     text       = excluded.text''',
              (text_id, true_label,
               dfa_pred, llm_pred,
               json.dumps(hit_words, ensure_ascii=False) if hit_words is not None else None,
               dfa_time, llm_time,
               json.dumps(llm_spans or [], ensure_ascii=False) if llm_spans is not None else None,
               llm_reason,
               dataset_id, text))
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
