import json
import os
import uuid
import random
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed


def texts_to_jsonl(texts: list, output_path: str):
    """将文本列表写入 JSONL，每条记录包含 id, text, is_toxic=False"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for text in texts:
            rec = {
                "id": str(uuid.uuid4())[:8],
                "text": text.strip(),
                "is_toxic": False,
                "toxic_spans": [],
                "original_text": "",
                "attack_strategy": ""
            }
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')


def merge_jsonl(clean_path, poisoned_path, output_path):
    """合并两个 JSONL 文件并打乱顺序"""
    records = []
    for path in [clean_path, poisoned_path]:
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
    random.shuffle(records)
    with open(output_path, 'w', encoding='utf-8') as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
    return output_path


def load_jsonl(path):
    data = []
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))
    return data


def save_dataset(jsonl_path, title, api_key=None, base_url=None, model=None):
    """将 JSONL 数据集保存到 data/datasets/ 目录，带时间戳和标题。
    如果提供 API 参数，则用 LLM 自动生成标题。否则使用给定标题。
    返回 (保存路径, 标题)"""
    import datetime
    import shutil

    datasets_dir = os.path.join('data', 'datasets')
    os.makedirs(datasets_dir, exist_ok=True)

    # 如果提供了 API，自动生成标题
    if api_key and base_url and model and title is None:
        try:
            title = _generate_dataset_title(jsonl_path, api_key, base_url, model)
        except Exception as e:
            print(f"[WARN] AI 标题生成失败: {e}")
    if not title:
        title = '测试集'

    # 生成带时间戳的文件名
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    safe_title = title.replace('/', '_').replace('\\', '_')[:50]
    basename = f'{ts}_{safe_title}'
    dest_jsonl = os.path.join(datasets_dir, f'{basename}.jsonl')
    dest_meta = os.path.join(datasets_dir, f'{basename}.meta.json')

    # 拷贝 JSONL
    shutil.copy2(jsonl_path, dest_jsonl)

    # 写元数据
    data = load_jsonl(jsonl_path)
    total = len(data)
    toxic_count = sum(1 for r in data if r.get('is_toxic'))
    meta = {
        'title': title,
        'created': ts,
        'total': total,
        'toxic_count': toxic_count,
        'clean_count': total - toxic_count,
        'source': jsonl_path,
    }
    with open(dest_meta, 'w', encoding='utf-8') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return dest_jsonl, title


def _generate_dataset_title(jsonl_path, api_key, base_url, model):
    """调用 LLM 为数据集生成简短标题"""
    from core.llm_client import BaseLLMClient
    data = load_jsonl(jsonl_path)
    # 采样前几条文本作为提示
    samples = [r.get('text', '')[:100] for r in data[:5] if r.get('text')]
    sample_text = '\n'.join(samples[:3])

    client = BaseLLMClient(api_key, base_url, model)
    title = client.call(
        messages=[{
            "role": "user",
            "content": (
                f"以下是一个教学文本安全测试数据集的样本：\n{sample_text}\n\n"
                f"数据集共 {len(data)} 条。请为这个数据集生成一个简短的中文标题（10字以内），"
                f"用于文件命名。只输出标题，不要其他内容。"
            )
        }],
        max_tokens=20,
        temperature=0.3,
    )
    if title:
        return title.strip().strip('"').strip("'")
    return '测试集'


def delete_dataset(dataset_path):
    """删除指定的数据集（JSONL + meta.json）"""
    p = Path(dataset_path)
    meta = p.with_suffix('.meta.json')
    for f in (p, meta):
        if f.exists():
            f.unlink()


def list_datasets():
    """列出 data/datasets/ 下所有已保存的数据集"""
    datasets_dir = os.path.join('data', 'datasets')
    if not os.path.isdir(datasets_dir):
        return []
    datasets = []
    for f in sorted(Path(datasets_dir).glob('*.jsonl'), reverse=True):
        meta_path = f.with_suffix('.meta.json')
        meta = {}
        if meta_path.exists():
            try:
                with open(meta_path, 'r', encoding='utf-8') as mf:
                    meta = json.load(mf)
            except Exception as e:
                print(f"[WARN] 元数据文件解析失败 {meta_path}: {e}")
        datasets.append({
            'path': str(f),
            'name': f.stem,
            'title': meta.get('title', f.stem),
            'created': meta.get('created', ''),
            'total': meta.get('total', '?'),
            'toxic_count': meta.get('toxic_count', '?'),
            'clean_count': meta.get('clean_count', '?'),
        })
    return datasets


# ---------------------------------------------------------------------------
#  并发工具（与 UI 无关，仅接受回调）
# ---------------------------------------------------------------------------

def run_concurrently(tasks, max_workers=6, progress_callback=None):
    """并发执行任务列表，按输入顺序返回结果。

    Parameters
    ----------
    tasks : list[tuple]
        每个元素为 (func, args)，args 可为 tuple（位置参数）或 dict（关键字参数）。
    max_workers : int
        最大并发线程数。
    progress_callback : callable, optional
        每完成一个任务时回调 ``progress_callback(completed, total)``。

    Returns
    -------
    list
        与输入等长的结果列表。异常时对应位置为 ``Exception`` 实例。
    """
    results = [None] * len(tasks)
    total = len(tasks)
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
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            try:
                results[idx] = future.result()
            except Exception as e:
                results[idx] = e
            completed += 1
            if progress_callback:
                progress_callback(completed, total)
    return results
