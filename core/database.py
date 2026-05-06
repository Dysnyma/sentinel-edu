import sqlite3
import json
import os
import pandas as pd

DB_NAME = os.path.join('data', 'scan_results.db')


def init_db():
    os.makedirs('data', exist_ok=True)
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # 创建表（若不存在）
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
    # 兼容旧表没有 llm_spans 字段的情况
    try:
        c.execute("SELECT llm_spans FROM results LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE results ADD COLUMN llm_spans TEXT")
    conn.commit()
    conn.close()


def save_result(text_id, true_label, dfa_pred, llm_pred, hit_words, dfa_time, llm_time, llm_spans=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''INSERT OR REPLACE INTO results 
                 (text_id, true_label, dfa_pred, llm_pred, hit_words, dfa_time, llm_time, llm_spans)
                 VALUES (?,?,?,?,?,?,?,?)''',
              (text_id, true_label, dfa_pred, llm_pred, json.dumps(hit_words, ensure_ascii=False),
               dfa_time, llm_time, json.dumps(llm_spans or [], ensure_ascii=False)))
    conn.commit()
    conn.close()


def update_llm_result(text_id, llm_pred, llm_time, llm_spans=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''UPDATE results SET llm_pred = ?, llm_time = ?, llm_spans = ? WHERE text_id = ?''',
              (llm_pred, llm_time, json.dumps(llm_spans or [], ensure_ascii=False), text_id))
    conn.commit()
    conn.close()


def get_all_results():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM results", conn)
    conn.close()
    return df
