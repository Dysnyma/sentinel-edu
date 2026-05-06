import json
import uuid
import random
from pathlib import Path


def texts_to_jsonl(texts: list, output_path: str):
    """将文本列表写入 JSONL，每条记录包含 id, text, is_toxic=False"""
    with open(output_path, 'w', encoding='utf-8') as f:
        for text in texts:
            rec = {
                "id": str(uuid.uuid4())[:8],
                "text": text.strip(),
                "is_toxic": False,
                "toxic_spans": []
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
