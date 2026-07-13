"""Tab 1: 测试集构建 — 输入 → ASR → 纠错 → 投毒 → JSONL"""

import streamlit as st
import os
import tempfile
import json
import uuid
import random
import shutil
from pathlib import Path

from core.asr import extract_audio_from_video, transcribe_audio_api, transcribe_audio_local, download_bilibili_video, is_whisper_model_downloaded, get_local_whisper_model
from core.text_correction import correct_text
from core.poison_generator import generate_poison
from core.utils import texts_to_jsonl, merge_jsonl, load_jsonl, save_dataset
from views.helpers import highlight_toxic, run_concurrently


def _split_sentences(text: str) -> list:
    """将文本按中英文标点分割为句子片段"""
    import re
    # 按中英文句号、问号、感叹号、分号、换行分割
    parts = re.split(r'[。！？；\.\?!;\n]+', text)
    return [s.strip() for s in parts if s.strip()]


def render_tab1(api_ready, api_key, base_url, llm_model, concurrency,
                use_local_whisper, local_whisper_model):
    st.header("步骤1：获取原始文本")
    input_method = st.radio(
        "选择输入方式", ["📁 上传音视频文件", "🔗 B站视频链接", "✏️ 直接输入文本"], horizontal=True)
    raw_texts = []

    prompt_text = "这是一堂关于马克思主义基本原理、毛泽东思想、邓小平理论、唯物辩证法、社会主义核心价值观的大学思政课。"

    if input_method == "📁 上传音视频文件":
        uploaded_file = st.file_uploader(
            "上传音频或视频", type=["wav", "mp3", "m4a", "mp4", "flv", "mkv"])
        if uploaded_file:
            file_id = f"{uploaded_file.name}_{uploaded_file.size}"
            # Only process if the file changed (avoid re-running on every widget interaction)
            if st.session_state.get('_last_file_id') != file_id:
                st.session_state['_last_file_id'] = file_id
                suffix = Path(uploaded_file.name).suffix
                tmp_path = None
                audio_path = None
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(uploaded_file.read())
                        tmp_path = tmp.name

                    is_video = suffix.lower() in ['.mp4', '.flv', '.mkv', '.avi', '.mov', '.webm']
                    with st.spinner("正在提取音频..." if is_video else "正在读取文件..."):
                        if is_video:
                            audio_path = extract_audio_from_video(
                                tmp_path, st.session_state.ffmpeg_path)
                        else:
                            audio_path = tmp_path
                    if is_video:
                        st.success("音频提取成功")

                    if use_local_whisper:
                        if not is_whisper_model_downloaded(local_whisper_model):
                            st.info(f"📥 首次使用需下载 Whisper {local_whisper_model} 模型（约500MB），请耐心等待...")
                        with st.spinner(f"正在加载 Whisper {local_whisper_model} 模型到内存..."):
                            get_local_whisper_model(local_whisper_model)
                        progress_bar = st.progress(0, text="正在语音转写... 0%")

                        def _update(pct):
                            progress_bar.progress(pct, text=f"正在语音转写... {pct * 100:.0f}%")
                        transcript = transcribe_audio_local(
                            audio_path, model_name=local_whisper_model, initial_prompt=prompt_text,
                            progress_callback=_update)
                        progress_bar.progress(1.0, text="转写完成")
                        st.success("转写完成")
                    else:
                        if not api_ready:
                            st.error("未配置大模型 API 密钥，无法使用云端 ASR。请启用本地 Whisper。")
                            st.stop()
                        with st.spinner("云端 Whisper 转写中，请耐心等待..."):
                            transcript = transcribe_audio_api(
                                audio_path, api_key, base_url, prompt_text)
                        st.success("转写完成")

                    st.session_state['asr_transcript'] = transcript
                except Exception as e:
                    st.error(f"处理文件失败：{e}")
                    st.session_state.pop('_last_file_id', None)
                finally:
                    for p in {tmp_path, audio_path}:
                        if p and os.path.exists(p):
                            try:
                                os.unlink(p)
                            except OSError:
                                pass

            # Show editable transcript (persists across re-runs)
            default_transcript = st.session_state.get('asr_transcript', '')
            edited = st.text_area(
                "转写结果（可手动编辑）", default_transcript, height=200,
                key="transcript_editor")
            raw_texts = [s for s in _split_sentences(edited)]

    elif input_method == "🔗 B站视频链接":
        bili_url = st.text_input("B站视频地址")
        if bili_url and st.button("开始解析并下载"):
            if not shutil.which(st.session_state.bbdown_path):
                st.error("BBDown 不可用，请检查安装")
            else:
                with st.spinner("使用 BBDown 下载中..."):
                    try:
                        info = download_bilibili_video(
                            bili_url, st.session_state.bbdown_path)
                        if info['subtitle']:
                            sub_text = Path(info['subtitle']).read_text(
                                encoding='utf-8')
                            st.success("找到人工字幕，跳过语音转写")
                            st.session_state['bili_transcript'] = sub_text
                            raw_texts = [s for s in _split_sentences(sub_text)]
                        elif info['video']:
                            with st.spinner("无字幕，正在提取音频..."):
                                audio_path = extract_audio_from_video(
                                    info['video'], st.session_state.ffmpeg_path)
                            st.success("音频提取成功")
                            if use_local_whisper:
                                if not is_whisper_model_downloaded(local_whisper_model):
                                    st.info(f"📥 首次使用需下载 Whisper {local_whisper_model} 模型（约500MB），请耐心等待...")
                                with st.spinner(f"正在加载 Whisper {local_whisper_model} 模型到内存..."):
                                    get_local_whisper_model(local_whisper_model)
                                progress_bar = st.progress(0, text="正在语音转写... 0%")

                                def _update2(pct):
                                    progress_bar.progress(pct, text=f"正在语音转写... {pct * 100:.0f}%")
                                transcript = transcribe_audio_local(
                                    audio_path, model_name=local_whisper_model, initial_prompt=prompt_text,
                                    progress_callback=_update2)
                                progress_bar.progress(1.0, text="转写完成")
                                st.success("转写完成")
                            else:
                                if not api_ready:
                                    st.error("未配置 API 密钥，无法使用云端 ASR。请启用本地 Whisper。")
                                    st.stop()
                                with st.spinner("云端 Whisper 转写中，请耐心等待..."):
                                    transcript = transcribe_audio_api(
                                        audio_path, api_key, base_url, prompt_text)
                                st.success("转写完成")
                            st.session_state['bili_transcript'] = transcript
                            raw_texts = [s for s in _split_sentences(transcript)]
                        else:
                            st.error("BBDown 未找到视频或字幕文件，请检查链接是否有效")
                    except Exception as e:
                        st.error(f"处理失败：{e}")
        # Show cached results outside the button block
        if st.session_state.get('bili_transcript'):
            edited = st.text_area("字幕/转写内容", st.session_state['bili_transcript'], height=150,
                                  key="bili_transcript_editor")
            if not raw_texts:
                raw_texts = [s for s in _split_sentences(edited)]

    elif input_method == "✏️ 直接输入文本":
        manual_text = st.text_area("请输入课堂文本", height=200)
        if manual_text:
            raw_texts = [s for s in _split_sentences(manual_text)]

    info_placeholder = st.empty()
    if raw_texts:
        st.session_state['raw_texts'] = raw_texts
        info_placeholder.info(f"已获取 {len(raw_texts)} 条文本片段")

    # --- 步骤2：文本纠错（可选） ---
    st.markdown("---")
    st.header("步骤2：文本纠错（可选）")
    has_raw = bool(st.session_state.get('raw_texts'))
    if st.button("✨ 开始大模型纠错", disabled=not has_raw,
                 help=None if has_raw else "请先在步骤1获取原始文本"):
        if not api_ready:
            st.error("缺少 API 配置")
        else:
            import time
            corrected = []
            total = len(st.session_state.raw_texts)
            progress_bar = st.progress(0, text=f"文本纠错中... 0/{total}")
            t_start = time.time()
            for i, text in enumerate(st.session_state.raw_texts):
                try:
                    corr = correct_text(text, api_key, base_url, llm_model)
                    corrected.append(corr)
                except Exception as e:
                    st.warning(f"第{i}条纠错失败，保留原句：{e}")
                    corrected.append(text)
                elapsed = time.time() - t_start
                eta = (elapsed / (i + 1)) * (total - i - 1) if i > 0 else 0
                progress_bar.progress(
                    (i + 1) / total,
                    text=f"文本纠错中... {i + 1}/{total} | 耗时 {elapsed:.0f}s | 预计剩余 {eta:.0f}s"
                )
            st.session_state['corrected_texts'] = corrected
            st.success(f"纠错完成，共 {total} 条，耗时 {time.time() - t_start:.0f}s")

    final_texts = st.session_state.get(
        'corrected_texts', st.session_state.get('raw_texts', []))

    # --- 步骤3：生成无毒 JSONL ---
    st.markdown("---")
    st.header("步骤3：生成无毒文本集（JSONL）")
    has_final = bool(final_texts)
    if st.button("📝 生成无毒 JSONL", disabled=not has_final,
                 help=None if has_final else "等待文本就绪"):
        texts_to_jsonl(final_texts, 'data/clean_corpus.jsonl')
        st.session_state['clean_jsonl'] = 'data/clean_corpus.jsonl'
        st.success(f"无毒文本已保存至 data/clean_corpus.jsonl，共 {len(final_texts)} 条")

    # --- 步骤4：投毒生成 ---
    st.markdown("---")
    st.header("步骤4：投毒生成有毒文本（红队测试）")
    clean_path = st.session_state.get('clean_jsonl')
    has_clean = clean_path and os.path.exists(clean_path)
    poison_ratio = st.slider("投毒比例", 0.1, 1.0, 0.3, step=0.1, disabled=not has_clean)
    if st.button("🦠 开始投毒生成", disabled=not has_clean,
                 help=None if has_clean else "请先生成无毒 JSONL"):
        if not api_ready:
            st.error("缺少 API 配置")
        else:
            clean_data = load_jsonl(clean_path)
            total = len(clean_data)
            poison_count = max(1, int(total * poison_ratio))
            selected = random.sample(clean_data, poison_count)

            tasks = [(generate_poison, (rec['text'], api_key,
                      base_url, llm_model)) for rec in selected]
            progress_bar = st.progress(0)
            raw_results = run_concurrently(
                tasks, max_workers=concurrency,
                progress_placeholder=progress_bar, progress_text="投毒生成中"
            )

            poisoned_records = []
            for i, (rec, res) in enumerate(zip(selected, raw_results)):
                if isinstance(res, Exception):
                    st.warning(f"第{i}条投毒失败")
                    with st.expander("查看错误"):
                        st.exception(res)
                    continue
                res['id'] = str(uuid.uuid4())[:8]
                res.setdefault('original_text', rec['text'])
                res.setdefault('attack_strategy', '未知')
                poisoned_records.append(res)

            poison_file = 'data/poisoned_corpus.jsonl'
            with open(poison_file, 'w', encoding='utf-8') as f:
                for rec in poisoned_records:
                    out = {
                        "id": rec['id'],
                        "text": rec.get('text', ''),
                        "original_text": rec.get('original_text', ''),
                        "is_toxic": True,
                        "toxic_spans": rec.get('toxic_spans', []),
                        "attack_strategy": rec.get('attack_strategy', '')
                    }
                    f.write(json.dumps(out, ensure_ascii=False) + '\n')

            merge_jsonl(clean_path, poison_file, 'data/final_test_mixed.jsonl')
            st.session_state['final_test'] = 'data/final_test_mixed.jsonl'
            st.session_state['_poison_generated'] = True

            # 用 AI 自动生成标题建议
            from core.utils import _generate_dataset_title
            ai_title = None
            if api_key and base_url and llm_model:
                try:
                    ai_title = _generate_dataset_title(
                        'data/final_test_mixed.jsonl', api_key, base_url, llm_model)
                except Exception:
                    st.warning("AI 标题建议失败，将使用默认名称")
            st.session_state['_ai_suggested_title'] = ai_title or '测试集'

            st.success(
                f"投毒完成！共生成 {len(poisoned_records)} 条有毒文本，最终混合集：data/final_test_mixed.jsonl")

    # 投毒完成后显示 AI 命名 + 保存按钮（独立于按钮点击，持久显示）
    if st.session_state.get('_poison_generated') and os.path.exists('data/final_test_mixed.jsonl'):
        st.markdown("---")
        st.subheader("💾 保存测试集")
        ai_title = st.session_state.get('_ai_suggested_title', '测试集')
        col_title, col_btn = st.columns([3, 1])
        with col_title:
            final_title = st.text_input(
                "数据集标题", value=ai_title,
                help="可修改 AI 建议的标题", key="dataset_title_input")
        with col_btn:
            st.write("")  # 对齐
            if st.button("💾 确认保存", type="primary", use_container_width=True):
                saved_path, saved_title = save_dataset(
                    'data/final_test_mixed.jsonl', final_title)
                st.session_state['last_dataset_title'] = saved_title
                st.session_state['_poison_generated'] = False
                st.success(f"已保存至：`{saved_path}`")
                st.rerun()

            final_data = load_jsonl('data/final_test_mixed.jsonl')
            toxic_samples = [r for r in final_data if r.get('is_toxic')]
            if toxic_samples:
                with st.expander(f"🔍 有毒样本对比（共 {len(toxic_samples)} 条）"):
                    for i, rec in enumerate(toxic_samples[:10]):
                        original = rec.get('original_text', '（无法获取原文）')
                        toxic_text = rec.get('text', '')
                        spans = rec.get('toxic_spans', [])
                        strategy = rec.get('attack_strategy', '未知')
                        st.markdown(f"**样本 {i + 1}** | 策略：{strategy}")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.caption("原文")
                            st.write(original)
                        with col2:
                            st.caption("有毒文本（毒点高亮）")
                            st.markdown(highlight_toxic(
                                toxic_text, spans), unsafe_allow_html=True)
                        st.markdown("---")
