"""可视化分析控制器 — 封装 tab3_analysis.py 中的 Pandas 数据处理与指标计算。"""

import pandas as pd


def load_and_prepare_data(
    df: pd.DataFrame,
    dataset_id: str | None = None,
    current_ids: set | None = None,
    strategy_map: dict | None = None,
) -> pd.DataFrame:
    """加载并预处理检测结果 DataFrame。

    步骤：
    1. 按 current_ids 或 dataset_id 筛选
    2. 强制数值类型转换
    3. 计算 ``final_pred`` 列（双防联合判定）
    4. 加载攻击策略映射
    """
    if current_ids is not None:
        df = df[df['text_id'].isin(current_ids)].copy()
    elif dataset_id is not None:
        df = df[df['dataset_id'] == dataset_id].copy()

    if df.empty:
        return df

    # 强制数值类型
    df['dfa_pred'] = pd.to_numeric(df['dfa_pred'], errors='coerce').fillna(-1).astype(int)
    df['llm_pred'] = pd.to_numeric(df['llm_pred'], errors='coerce').fillna(-1).astype(int)
    df['true_label'] = pd.to_numeric(df['true_label'], errors='coerce').fillna(0).astype(int)
    df['dfa_time'] = pd.to_numeric(df['dfa_time'], errors='coerce').fillna(0)
    df['llm_time'] = pd.to_numeric(df['llm_time'], errors='coerce').fillna(0)

    # 联合判定
    df['final_pred'] = ((df['dfa_pred'] == 1) | (df['llm_pred'] == 1)).astype(int)

    # 策略映射
    if strategy_map:
        df['attack_strategy'] = df['text_id'].map(strategy_map).fillna('未知')

    return df


def compute_confusion_metrics(scanned: pd.DataFrame) -> dict:
    """从已扫描样本计算混淆矩阵核心指标。

    返回::
        {
            "tp": int, "tn": int, "fp": int, "fn": int,
            "accuracy": float, "recall": float, "precision": float,
            "f1": float, "fnr": float, "fpr": float,
            "scanned_count": int,
            "avg_dfa_time": float, "avg_llm_time": float, "total_time": float,
        }
    """
    if scanned.empty:
        return {
            "tp": 0, "tn": 0, "fp": 0, "fn": 0,
            "accuracy": 0.0, "recall": 0.0, "precision": 0.0,
            "f1": 0.0, "fnr": 0.0, "fpr": 0.0,
            "scanned_count": 0,
            "avg_dfa_time": 0.0, "avg_llm_time": 0.0, "total_time": 0.0,
        }

    tp = int(((scanned['true_label'] == 1) & (scanned['final_pred'] == 1)).sum())
    tn = int(((scanned['true_label'] == 0) & (scanned['final_pred'] == 0)).sum())
    fp = int(((scanned['true_label'] == 0) & (scanned['final_pred'] == 1)).sum())
    fn = int(((scanned['true_label'] == 1) & (scanned['final_pred'] == 0)).sum())
    n = len(scanned)

    accuracy = (tp + tn) / n
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    fnr = fn / (tp + fn) if (tp + fn) > 0 else 0.0
    fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    dfa_valid = scanned[scanned['dfa_pred'] != -1]
    llm_valid = scanned[scanned['llm_pred'] != -1]
    avg_dfa_time = float(dfa_valid['dfa_time'].mean()) if len(dfa_valid) > 0 else 0.0
    avg_llm_time = float(llm_valid['llm_time'].mean()) if len(llm_valid) > 0 else 0.0
    total_time = float(scanned['dfa_time'].sum() + scanned['llm_time'].sum())

    return {
        "tp": tp, "tn": tn, "fp": fp, "fn": fn,
        "accuracy": accuracy, "recall": recall, "precision": precision,
        "f1": f1, "fnr": fnr, "fpr": fpr,
        "scanned_count": n,
        "avg_dfa_time": avg_dfa_time, "avg_llm_time": avg_llm_time,
        "total_time": total_time,
    }


def _calc_metrics_pair(true_labels: list, preds: list) -> tuple:
    """计算单组指标：准确率、召回率、精确率、F1。"""
    tp = sum(1 for t, p in zip(true_labels, preds) if t == 1 and p == 1)
    tn = sum(1 for t, p in zip(true_labels, preds) if t == 0 and p == 0)
    fp = sum(1 for t, p in zip(true_labels, preds) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(true_labels, preds) if t == 1 and p == 0)
    n = len(true_labels)
    acc = (tp + tn) / n if n > 0 else 0.0
    rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
    return acc, rec, prec, f1


def compute_independent_metrics(scanned: pd.DataFrame) -> dict:
    """分别计算 DFA 和 LLM 的独立指标。

    返回::
        {
            "dfa_acc": float, "dfa_rec": float, "dfa_prec": float, "dfa_f1": float,
            "llm_acc": float, "llm_rec": float, "llm_prec": float, "llm_f1": float,
        }
    """
    result = {}
    for prefix, col in [('dfa', 'dfa_pred'), ('llm', 'llm_pred')]:
        valid = scanned[scanned[col] != -1]
        if not valid.empty:
            acc, rec, prec, f1 = _calc_metrics_pair(
                valid['true_label'].tolist(), valid[col].tolist())
        else:
            acc = rec = prec = f1 = 0.0
        result.update({
            f'{prefix}_acc': acc,
            f'{prefix}_rec': rec,
            f'{prefix}_prec': prec,
            f'{prefix}_f1': f1,
        })
    return result


def compute_strategy_analysis(scanned: pd.DataFrame) -> pd.DataFrame:
    """按攻击策略分组统计拦截效果。"""
    if 'attack_strategy' not in scanned.columns:
        return pd.DataFrame()

    toxic_df = scanned[scanned['true_label'] == 1].copy()
    if toxic_df.empty:
        return pd.DataFrame()

    strategies = toxic_df['attack_strategy'].unique()
    records = []
    for s in strategies:
        subset = toxic_df[toxic_df['attack_strategy'] == s]
        s_tp = int((subset['final_pred'] == 1).sum())
        s_fn = int((subset['final_pred'] == 0).sum())
        s_total = len(subset)
        s_recall = s_tp / s_total if s_total > 0 else 0.0
        s_miss = s_fn / s_total if s_total > 0 else 0.0
        records.append({
            '攻击策略': s if s else '无毒',
            '有毒样本数': s_total,
            '正确拦截': s_tp,
            '漏报': s_fn,
            '召回率': f'{s_recall:.1%}',
            '漏报率': f'{s_miss:.1%}',
        })
    return pd.DataFrame(records)


def compute_funnel_data(scanned: pd.DataFrame, total: int) -> dict:
    """计算双防拦截漏斗数据。

    返回::
        {"total": int, "dfa_hit": int, "llm_hit": int, "final_hit": int}
    """
    return {
        "total": total,
        "dfa_hit": int((scanned['dfa_pred'] == 1).sum()),
        "llm_hit": int((scanned['llm_pred'] == 1).sum()),
        "final_hit": int((scanned['final_pred'] == 1).sum()),
    }
