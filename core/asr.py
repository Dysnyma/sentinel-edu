import openai
try:
    import whisper
except Exception:
    whisper = None
import subprocess
import os
import warnings
from pathlib import Path
from urllib.parse import urlparse
import streamlit as st


def is_whisper_model_downloaded(model_name="base"):
    """检查 Whisper 模型是否已下载到本地缓存"""
    cache_dir = os.path.join(os.path.expanduser("~"), ".cache", "whisper")
    model_file = os.path.join(cache_dir, f"{model_name}.pt")
    return os.path.exists(model_file)


@st.cache_resource
def get_local_whisper_model(model_name="base"):
    return whisper.load_model(model_name)


def _trim_overlap(prev: str, curr: str, min_match: int = 2, max_window: int = 60) -> str:
    """去除相邻分片重叠导致的重复内容。

    在 prev 末尾与 curr 开头的窗口内，寻找既是 prev 后缀又是 curr 前缀的最长公共子串，
    并从 curr 头部裁掉。用 difflib 而非严格相等，容忍两次转写在重叠区的小差异。
    """
    if not prev or not curr:
        return curr
    from difflib import SequenceMatcher
    prev_tail = prev[-max_window:]
    curr_head = curr[:max_window]
    sm = SequenceMatcher(None, prev_tail, curr_head, autojunk=False)
    best = 0
    for a, b, size in sm.get_matching_blocks():
        # 匹配块必须正好落在 prev_tail 的末尾、curr_head 的开头
        if b == 0 and a + size == len(prev_tail) and size > best:
            best = size
    return curr[best:] if best >= min_match else curr


def transcribe_audio_local(audio_path: str, model_name="base", initial_prompt: str = None,
                           progress_callback=None) -> str:
    model = get_local_whisper_model(model_name)

    # 关键防幻觉参数：关闭“以上文为条件”可避免静音/收尾段陷入重复循环；
    # no_speech_threshold + hallucination_silence_threshold 让静音尾段被快速跳过，
    # 这正是过去“卡在 97%（最后一段不动）”的根因。
    transcribe_kwargs = dict(
        initial_prompt=initial_prompt,
        language="zh",
        condition_on_previous_text=False,
        no_speech_threshold=0.6,
        hallucination_silence_threshold=2.0,
        verbose=False,
        fp16=False,
    )

    if progress_callback is None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = model.transcribe(audio_path, **transcribe_kwargs)
        return result["text"]

    # 进度版：只加载一次音频，再切成 numpy 片段逐段转写。
    # 旧实现每段都传 audio_path + clip_timestamps，导致每段都重新 ffmpeg 解码整段音频
    # 并重建完整 mel —— 越靠后越慢，且尾段静音极易触发幻觉重试循环。
    audio = whisper.load_audio(audio_path)
    sr = whisper.audio.SAMPLE_RATE
    duration = len(audio) / sr

    if duration <= 32:
        progress_callback(0.0)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = model.transcribe(audio, **transcribe_kwargs)
        progress_callback(1.0)
        return result["text"]

    # 30s 分片，1s 重叠防止字符边界被切断
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
            start_sample = int(seg_start * sr)
            end_sample = int(seg_end * sr)
            # 直接传 numpy 切片：whisper.transcribe 接受 ndarray，只对本段建 mel，不重复解码
            chunk = audio[start_sample:end_sample]
            result = model.transcribe(chunk, **transcribe_kwargs)
            texts.append(result["text"].strip())
            progress_callback((i + 1) / len(segments))

    if len(texts) > 1:
        merged = [texts[0]]
        for curr in texts[1:]:
            merged.append(_trim_overlap(merged[-1], curr))
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
    # URL 域名白名单校验：仅允许 bilibili.com 和 b23.tv（含子域名）
    _ALLOWED_DOMAINS = {'bilibili.com', 'b23.tv'}
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    if not domain or not any(domain == d or domain.endswith('.' + d) for d in _ALLOWED_DOMAINS):
        raise ValueError(
            f"不支持的链接：{url}。仅支持 bilibili.com 和 b23.tv 的链接。"
        )

    downloads_dir = os.path.join(os.getcwd(), "downloads")
    os.makedirs(downloads_dir, exist_ok=True)
    cmd = [bbdown_path, url, '--work-dir', downloads_dir]
    result = subprocess.run(cmd, capture_output=True, text=True)  # nosec — url 已通过上方白名单校验
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
