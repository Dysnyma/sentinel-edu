"""测试集构建控制器 — 封装 tab1_build.py 中的非 UI 业务逻辑。

职责边界：
- 只处理数据：接受参数 → 执行业务逻辑 → 返回结果
- 不依赖 ``streamlit``、不读写 ``st.session_state``
- 耗时操通过可选的 ``progress_callback`` 回调报告进度
"""

import os
import re
import json
import uuid
import random
import shutil
import tempfile
import time
from pathlib import Path

from core.asr import (
    extract_audio_from_video,
    transcribe_audio_api,
    transcribe_audio_local,
    download_bilibili_video,
    is_whisper_model_downloaded,
    get_local_whisper_model,
)
from core.text_correction import correct_text
from core.poison_generator import generate_poison
from core.utils import texts_to_jsonl, merge_jsonl, load_jsonl, save_dataset, _generate_dataset_title
from views.helpers import run_concurrently


def _split_sentences(text: str) -> list[str]:
    """将文本按中英文标点分割为句子片段。"""
    parts = re.split(r'[。！？；\.\?!;\n]+', text)
    return [s.strip() for s in parts if s.strip()]


# ---------------------------------------------------------------------------
#  1. 上传文件 → ASR 转写
# ---------------------------------------------------------------------------

def process_uploaded_file(
    file_bytes: bytes,
    file_name: str,
    *,
    use_local: bool = True,
    local_model: str = "base",
    ffmpeg_path: str = "ffmpeg",
    api_key: str = "",
    base_url: str = "",
    initial_prompt: str = "",
    progress_callback=None,
) -> str:
    """处理上传的音视频文件：临时文件 → 音频提取 → ASR → 清理，返回转写文本。"""
    suffix = Path(file_name).suffix
    tmp_path = None
    audio_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        is_video = suffix.lower() in ['.mp4', '.flv', '.mkv', '.avi', '.mov', '.webm']
        if is_video:
            audio_path = extract_audio_from_video(tmp_path, ffmpeg_path)
        else:
            audio_path = tmp_path

        if use_local:
            if not is_whisper_model_downloaded(local_model):
                pass  # 调用方自行展示下载提醒
            get_local_whisper_model(local_model)
            transcript = transcribe_audio_local(
                audio_path,
                model_name=local_model,
                initial_prompt=initial_prompt,
                progress_callback=progress_callback,
            )
        else:
            transcript = transcribe_audio_api(
                audio_path, api_key, base_url, initial_prompt,
            )
        return transcript
    finally:
        for p in {tmp_path, audio_path}:
            if p and os.path.exists(p):
                try:
                    os.unlink(p)
                except OSError:
                    pass


# ---------------------------------------------------------------------------
#  2. B站链接 → 字幕 / ASR 转写
# ---------------------------------------------------------------------------

def process_bilibili_url(
    url: str,
    *,
    bbdown_path: str = "./BBDown",
    ffmpeg_path: str = "ffmpeg",
    use_local: bool = True,
    local_model: str = "base",
    api_key: str = "",
    base_url: str = "",
    initial_prompt: str = "",
    progress_callback=None,
) -> str:
    """处理 B 站视频链接：BBDown → 有字幕读字幕 / 无字幕则 ASR，返回文本。"""
    info = download_bilibili_video(url, bbdown_path)
    if info.get('subtitle'):
        subtitle_text = Path(info['subtitle']).read_text(encoding='utf-8')
        return subtitle_text

    if info.get('video'):
        audio_path = extract_audio_from_video(info['video'], ffmpeg_path)
        try:
            if use_local:
                get_local_whisper_model(local_model)
                return transcribe_audio_local(
                    audio_path,
                    model_name=local_model,
                    initial_prompt=initial_prompt,
                    progress_callback=progress_callback,
                )
            else:
                return transcribe_audio_api(audio_path, api_key, base_url, initial_prompt)
        finally:
            if os.path.exists(audio_path):
                try:
                    os.unlink(audio_path)
                except OSError:
                    pass

    raise ValueError("BBDown 未找到视频或字幕文件，请检查链接是否有效")


# ---------------------------------------------------------------------------
#  3. 文本纠错
# ---------------------------------------------------------------------------

def run_text_correction(
    texts: list[str],
    api_key: str,
    base_url: str,
    model: str,
    progress_callback=None,
) -> tuple[list[str], list[tuple[int, str]]]:
    """逐条调用 LLM 纠错。单条失败时保留原句并记录错误。

    返回 (corrected_list, errors)：
    - corrected_list: 与输入等长的纠错后文本列表
    - errors: [(index, error_message), ...]
    """
    corrected = []
    errors = []
    total = len(texts)
    for i, text in enumerate(texts):
        try:
            corr = correct_text(text, api_key, base_url, model)
            corrected.append(corr)
        except Exception as e:
            corrected.append(text)  # 失败时保留原句
            errors.append((i, str(e)))
        if progress_callback:
            progress_callback(i + 1, total)
    return corrected, errors


# ---------------------------------------------------------------------------
#  4. 投毒生成（并发）
# ---------------------------------------------------------------------------

def run_poison_generation(
    clean_path: str,
    *,
    poison_ratio: float = 0.3,
    api_key: str = "",
    base_url: str = "",
    model: str = "",
    concurrency: int = 6,
    progress_callback=None,
) -> dict:
    """从 JSONL 按比例采样 → 并发投毒 → 合并打乱 → 保存。

    返回 dict:
    {
        "poisoned_records": [...],    # 投毒成功的记录
        "errors": [(idx, msg), ...],  # 失败的记录
        "clean_path": str,           # 输入的无毒 JSONL 路径
        "poison_path": str,          # 输出的有毒 JSONL 路径
        "mixed_path": str,           # 合并后的混合 JSONL 路径
    }
    """
    clean_data = load_jsonl(clean_path)
    total = len(clean_data)
    poison_count = max(1, int(total * poison_ratio))
    selected = random.sample(clean_data, poison_count)

    tasks = [(generate_poison, (rec['text'], api_key, base_url, model)) for rec in selected]
    raw_results = run_concurrently(tasks, max_workers=concurrency, progress_placeholder=None)

    poisoned_records = []
    errors = []
    for i, (rec, res) in enumerate(zip(selected, raw_results)):
        if isinstance(res, Exception):
            errors.append((i, str(res)))
            continue
        res['id'] = str(uuid.uuid4())[:8]
        res.setdefault('original_text', rec['text'])
        res.setdefault('attack_strategy', '未知')
        poisoned_records.append(res)

    # 写有毒 JSONL
    poison_file = 'data/poisoned_corpus.jsonl'
    with open(poison_file, 'w', encoding='utf-8') as f:
        for rec in poisoned_records:
            out = {
                "id": rec['id'],
                "text": rec.get('text', ''),
                "original_text": rec.get('original_text', ''),
                "is_toxic": True,
                "toxic_spans": rec.get('toxic_spans', []),
                "attack_strategy": rec.get('attack_strategy', ''),
            }
            f.write(json.dumps(out, ensure_ascii=False) + '\n')

    # 合并打乱
    mixed_path = 'data/final_test_mixed.jsonl'
    merge_jsonl(clean_path, poison_file, mixed_path)

    if progress_callback:
        progress_callback(total, total)

    return {
        "poisoned_records": poisoned_records,
        "errors": errors,
        "clean_path": clean_path,
        "poison_path": poison_file,
        "mixed_path": mixed_path,
    }


# ---------------------------------------------------------------------------
#  5. 数据集自动保存
# ---------------------------------------------------------------------------

def transcribe_and_save_dataset(
    transcript: str,
    api_key: str = "",
    base_url: str = "",
    model: str = "",
) -> tuple[str, str]:
    """ASR 完成后：分割句子 → 保存数据集 → 返回 (路径, 标题)。"""
    sentences = _split_sentences(transcript)
    if not sentences:
        return "", ""
    jsonl_path = 'data/raw_transcript.jsonl'
    texts_to_jsonl(sentences, jsonl_path)
    return save_dataset(jsonl_path, title=None, api_key=api_key, base_url=base_url, model=model)


def save_corrected_dataset(
    texts: list[str],
    api_key: str = "",
    base_url: str = "",
    model: str = "",
) -> tuple[str, str]:
    """纠错完成后：保存无毒数据集 → 返回 (路径, 标题)。"""
    jsonl_path = 'data/clean_corpus.jsonl'
    texts_to_jsonl(texts, jsonl_path)
    return save_dataset(jsonl_path, title=None, api_key=api_key, base_url=base_url, model=model)
