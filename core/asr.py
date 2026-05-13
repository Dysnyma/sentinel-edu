import openai
import whisper
import subprocess
import tempfile
import os
import shutil
import warnings
from pathlib import Path

# ----- 本地 Whisper 模型单例 -----
_local_model = None
_local_model_name = "base"


def is_whisper_model_downloaded(model_name="base"):
    """检查 Whisper 模型是否已下载到本地缓存"""
    cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "whisper")
    model_file = os.path.join(cache_dir, f"{model_name}.pt")
    return os.path.exists(model_file)


def get_local_whisper_model(model_name="base"):
    global _local_model, _local_model_name
    if _local_model is None or _local_model_name != model_name:
        _local_model = whisper.load_model(model_name)
        _local_model_name = model_name
    return _local_model


def transcribe_audio_local(audio_path: str, model_name="base", initial_prompt: str = None,
                           progress_callback=None) -> str:
    model = get_local_whisper_model(model_name)

    if progress_callback is None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = model.transcribe(
                audio_path, initial_prompt=initial_prompt, language="zh")
        return result["text"]

    # Progress-enabled path: split audio by clip_timestamps and process each segment
    audio = whisper.load_audio(audio_path)
    duration = len(audio) / whisper.audio.SAMPLE_RATE

    if duration <= 32:
        progress_callback(0.0)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = model.transcribe(
                audio_path, initial_prompt=initial_prompt, language="zh")
        progress_callback(1.0)
        return result["text"]

    # Multi-segment: 30s chunks with 1s overlap to prevent word boundary cuts
    segment_len = 30
    overlap = 1
    segments = []
    pos = 0.0
    while pos < duration:
        end = min(pos + segment_len, duration)
        segments.append((pos, end))
        if end >= duration:
            break
        pos = end - overlap

    progress_callback(0.0)
    texts = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for i, (seg_start, seg_end) in enumerate(segments):
            result = model.transcribe(
                audio_path,
                initial_prompt=initial_prompt,
                language="zh",
                clip_timestamps=[seg_start, seg_end],
                verbose=False,
                fp16=False,
            )
            texts.append(result["text"])
            progress_callback((i + 1) / len(segments))

    # Deduplicate overlap at segment boundaries
    if len(texts) > 1:
        merged = [texts[0]]
        for i in range(1, len(texts)):
            prev = merged[-1]
            curr = texts[i]
            # Trim common prefix shared with previous segment's suffix
            for k in range(min(len(prev), 40), 1, -1):
                if curr.startswith(prev[-k:]):
                    curr = curr[k:]
                    break
            merged.append(curr)
        return "".join(merged)

    return texts[0] if texts else ""


def transcribe_audio_api(audio_path: str, api_key: str, base_url: str, prompt: str = None) -> str:
    client = openai.OpenAI(api_key=api_key, base_url=base_url)
    with open(audio_path, 'rb') as f:
        transcription = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            prompt=prompt
        )
    return transcription.text


def extract_audio_from_video(video_path: str, ffmpeg_path='ffmpeg') -> str:
    downloads_dir = os.path.join(os.getcwd(), "downloads")
    os.makedirs(downloads_dir, exist_ok=True)
    audio_name = Path(video_path).stem + "_extracted.wav"
    audio_path = os.path.join(downloads_dir, audio_name)
    cmd = [ffmpeg_path, '-i', video_path, '-vn', '-acodec',
           'pcm_s16le', '-ar', '16000', '-ac', '1', audio_path, '-y']
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"FFmpeg 音频提取失败：{result.stderr}")
    return audio_path


def download_bilibili_video(url: str, bbdown_path='./BBDown') -> dict:
    downloads_dir = os.path.join(os.getcwd(), "downloads")
    os.makedirs(downloads_dir, exist_ok=True)
    cmd = [bbdown_path, url, '--work-dir', downloads_dir]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"BBDown 下载失败：{result.stderr}")

    video_file = None
    subtitle_file = None
    for f in Path(downloads_dir).rglob('*'):
        if f.suffix in ['.mp4', '.flv', '.mkv'] and video_file is None:
            video_file = str(f)
        elif f.suffix in ['.cc', '.srt', '.ass', '.vtt'] and subtitle_file is None:
            subtitle_file = str(f)

    return {'video': video_file, 'subtitle': subtitle_file}
