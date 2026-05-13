"""共享 UI 辅助函数：高亮、上下文截取、颜色映射、JSON 安全解析等"""

import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed


def highlight_toxic(text, toxic_spans, color='#ff4d4d'):
    """将 toxic_spans 中的内容以指定颜色高亮，返回 HTML 字符串"""
    if not toxic_spans:
        return text
    escaped = [re.escape(span) for span in toxic_spans]
    pattern = re.compile('|'.join(escaped), re.IGNORECASE)
    return pattern.sub(
        lambda m: f'<mark style="background-color:{color}; color:white; padding:0 2px;">{m.group()}</mark>',
        text
    )


def strategy_to_color(strategy: str) -> str:
    """将投毒策略映射为高亮颜色：显性=红, 隐性=黄, 不当比喻=橙"""
    if '显性' in strategy:
        return '#ff4d4d'
    if '隐性' in strategy:
        return '#ffc107'
    if '比喻' in strategy:
        return '#ff8c00'
    return '#ff4d4d'


def context_snippet(text, spans, context_chars=20, color='#ff4d4d'):
    """截取毒点附近上下文，返回 (HTML高亮文本, 是否被截断)"""
    if not spans:
        return text[:150] + ('...' if len(text) > 150 else ''), len(text) > 150
    positions = []
    for span in spans:
        idx = text.find(span)
        if idx >= 0:
            start = max(0, idx - context_chars)
            end = min(len(text), idx + len(span) + context_chars)
            positions.append((start, end))
    if not positions:
        return text[:150] + ('...' if len(text) > 150 else ''), len(text) > 150
    positions.sort()
    merged = []
    for s, e in positions:
        if not merged or s > merged[-1][1]:
            merged.append([s, e])
        else:
            merged[-1][1] = max(merged[-1][1], e)
    sorted_spans = sorted(spans, key=len, reverse=True)
    parts = []
    trunc = False
    for i, (s, e) in enumerate(merged):
        if i == 0 and s > 0:
            parts.append('…')
            trunc = True
        segment = highlight_toxic(text[s:e], sorted_spans, color=color)
        parts.append(segment)
        if i < len(merged) - 1:
            parts.append('…')
        elif e < len(text):
            parts.append('…')
            trunc = True
    return ''.join(parts), trunc


def check_api_connection(api_key, base_url, model):
    """测试大模型 API 连通性，返回 (success, message)"""
    if not api_key or not base_url or not model:
        return False, "请填写 API Key、Base URL 和模型名称。"
    base_url = base_url.strip().rstrip('/')
    if not base_url.endswith('/v1'):
        base_url += '/v1'
    try:
        import openai
        client = openai.OpenAI(api_key=api_key.strip(), base_url=base_url)
        resp = client.chat.completions.create(
            model=model.strip(),
            messages=[{"role": "user", "content": "测试连接"}],
            max_tokens=5,
            timeout=10
        )
        return True, f"✅ 连接成功 (模型响应: {resp.choices[0].message.content})"
    except Exception as e:
        return False, f"❌ 连接失败: {str(e)}"


def to_native(v):
    """将 numpy 类型转为 Python 原生类型，用于 st.json 序列化"""
    import numpy as np
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, np.ndarray):
        return v.tolist()
    return v


def safe_json_loads(value):
    """安全解析 JSON 字符串，处理 pandas NaT/NaN/None 情况"""
    import pandas as pd
    if value is None:
        return []
    if isinstance(value, float):
        return []
    if not isinstance(value, (str, bytes, bytearray)):
        return []
    if not value.strip():
        return []
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return []


def run_concurrently(tasks, max_workers=6, progress_placeholder=None, progress_text=""):
    """并发执行任务列表，返回结果列表（按输入顺序）。自动显示进度和预计剩余时间。"""
    import time
    results = [None] * len(tasks)
    t_start = time.time()
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {}
        for idx, task in enumerate(tasks):
            func, args = task[0], task[1] if len(task) > 1 else ()
            if isinstance(args, dict):
                future = executor.submit(func, **args)
            else:
                future = executor.submit(func, *args)
            future_to_idx[future] = idx

        completed = 0
        total = len(tasks)
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                results[idx] = e
            completed += 1
            if progress_placeholder is not None:
                elapsed = time.time() - t_start
                eta = (elapsed / completed) * (total - completed) if completed > 0 else 0
                progress_placeholder.progress(
                    completed / total,
                    text=f"{progress_text} {completed}/{total} | 耗时 {elapsed:.0f}s | 预计剩余 {eta:.0f}s"
                )
    return results
