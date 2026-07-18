"""Tab 1: 测试集构建 — 仅负责 Streamlit UI 组件渲染与 session_state 读写。"""

import streamlit as st
import os
import time

from core.asr import is_whisper_model_downloaded
from core.build_controller import (
    process_uploaded_file,
    process_bilibili_url,
    run_text_correction,
    run_poison_generation,
    transcribe_and_save_dataset,
    save_corrected_dataset,
)
from core.utils import texts_to_jsonl, save_dataset, load_jsonl
from views.helpers import highlight_toxic


def render_tab1(api_ready, api_key, base_url, llm_model, concurrency,
                use_local_whisper, local_whisper_model):
    st.header("步骤1：获取原始文本")
    input_method = st.radio(
        "选择输入方式", ["📁 上传音视频文件", "🔗 B站视频链接", "✏️ 直接输入文本"], horizontal=True)
    raw_texts = []

    prompt_text = "这是一堂关于马克思主义基本原理、毛泽东思想、邓小平理论、唯物辩证法、社会主义核心价值观的大学思政课。"

    # ── 检测模型切换 ──────────────────────────────────────────────
    if use_local_whisper and st.session_state.get('_last_model') != local_whisper_model:
        st.session_state.pop('_last_file_id', None)
        st.session_state.pop('asr_transcript', None)
        st.session_state['_last_model'] = local_whisper_model

    # ═══════════════════════════════════════════════════════════════
    #  输入方式 1：上传音视频文件
    # ═══════════════════════════════════════════════════════════════
    if input_method == "📁 上传音视频文件":
        uploaded_file = st.file_uploader(
            "上传音频或视频", type=["wav", "mp3", "m4a", "mp4", "flv", "mkv"])
        if uploaded_file:
            file_id = f"{uploaded_file.name}_{uploaded_file.size}"
            if st.session_state.get('_last_file_id') != file_id:
                st.session_state['_last_file_id'] = file_id
                file_bytes = uploaded_file.read()
                is_video = uploaded_file.name.split('.')[-1].lower() in \
                    ['mp4', 'flv', 'mkv', 'avi', 'mov', 'webm']
                with st.spinner("正在提取音频..." if is_video else "正在读取文件..."):
                    try:
                        if use_local_whisper and not is_whisper_model_downloaded(local_whisper_model):
                            st.info(f"📥 首次使用需下载 Whisper {local_whisper_model} 模型（约500MB），请耐心等待...")
                        progress_bar = st.progress(0, text="正在语音转写... 0%")

                        def _update(pct):
                            progress_bar.progress(pct, text=f"正在语音转写... {pct * 100:.0f}%")

                        transcript = process_uploaded_file(
                            file_bytes, uploaded_file.name,
                            use_local=use_local_whisper,
                            local_model=local_whisper_model,
                            ffmpeg_path=st.session_state.ffmpeg_path,
                            api_key=api_key,
                            base_url=base_url,
                            initial_prompt=prompt_text,
                            progress_callback=_update if use_local_whisper else None,
                        )
                        progress_bar.progress(1.0, text="转写完成")
                        st.success("转写完成")
                        st.session_state['asr_transcript'] = transcript
                    except Exception as e:
                        st.error(f"处理文件失败：{e}")
                        st.session_state.pop('_last_file_id', None)

            default_transcript = st.session_state.get('asr_transcript', '')
            edited = st.text_area(
                "转写结果（可手动编辑）", default_transcript, height=200, key="transcript_editor")
            raw_texts = [s for s in edited.split('。') if s.strip()]

    # ═══════════════════════════════════════════════════════════════
    #  输入方式 2：B站视频链接
    # ═══════════════════════════════════════════════════════════════
    elif input_method == "🔗 B站视频链接":
        bili_url = st.text_input("B站视频地址")
        if bili_url and st.button("开始解析并下载"):
            if not shutil_available():
                st.error("BBDown 不可用，请检查安装")
            else:
                with st.spinner("使用 BBDown 下载中..."):
                    try:
                        if use_local_whisper and not is_whisper_model_downloaded(local_whisper_model):
                            st.info(f"📥 首次使用需下载 Whisper {local_whisper_model} 模型（约500MB），请耐心等待...")
                        progress_bar = st.progress(0, text="处理中... 0%")

                        def _update2(pct):
                            progress_bar.progress(pct, text=f"处理中... {pct * 100:.0f}%")

                        transcript = process_bilibili_url(
                            bili_url,
                            bbdown_path=st.session_state.bbdown_path,
                            ffmpeg_path=st.session_state.ffmpeg_path,
                            use_local=use_local_whisper,
                            local_model=local_whisper_model,
                            api_key=api_key,
                            base_url=base_url,
                            initial_prompt=prompt_text,
                            progress_callback=_update2 if use_local_whisper else None,
                        )
                        progress_bar.progress(1.0, text="完成")
                        st.success("处理完成")
                        st.session_state['bili_transcript'] = transcript
                    except Exception as e:
                        st.error(f"处理失败：{e}")
        if st.session_state.get('bili_transcript'):
            edited = st.text_area("字幕/转写内容", st.session_state['bili_transcript'],
                                  height=150, key="bili_transcript_editor")
            if not raw_texts:
                raw_texts = [s for s in edited.split('。') if s.strip()]

    # ═══════════════════════════════════════════════════════════════
    #  输入方式 3：直接输入文本
    # ═══════════════════════════════════════════════════════════════
    elif input_method == "✏️ 直接输入文本":
        manual_text = st.text_area("请输入课堂文本", height=200)
        if manual_text:
            raw_texts = [s for s in manual_text.split('。') if s.strip()]

    info_placeholder = st.empty()
    if raw_texts:
        st.session_state['raw_texts'] = raw_texts
        info_placeholder.info(f"已获取 {len(raw_texts)} 条文本片段")

    # ── ASR 完成后自动保存原始数据集 ──────────────────────────────
    if st.session_state.get('asr_transcript') and not st.session_state.get('_raw_dataset_saved'):
        try:
            transcribe_and_save_dataset(
                st.session_state['asr_transcript'],
                api_key=api_key if api_ready else "",
                base_url=base_url if api_ready else "",
                model=llm_model if api_ready else "",
            )
        except Exception:
            pass
        st.session_state['_raw_dataset_saved'] = True

    # ═══════════════════════════════════════════════════════════════
    #  步骤2：文本纠错
    # ═══════════════════════════════════════════════════════════════
    st.markdown("---")
    st.header("步骤2：文本纠错（可选）")
    has_raw = bool(st.session_state.get('raw_texts'))
    if st.button("✨ 开始大模型纠错", disabled=not has_raw,
                 help=None if has_raw else "请先在步骤1获取原始文本"):
        if not api_ready:
            st.error("缺少 API 配置")
        else:
            progress_bar = st.progress(0, text="文本纠错中... 0/0")
            t_start = time.time()
            total = len(st.session_state.raw_texts)

            def _corr_update(done, total_):
                elapsed = time.time() - t_start
                eta = (elapsed / done) * (total_ - done) if done > 0 else 0
                progress_bar.progress(
                    done / total_,
                    text=f"文本纠错中... {done}/{total_} | 耗时 {elapsed:.0f}s | 预计剩余 {eta:.0f}s"
                )

            corrected, errors = run_text_correction(
                st.session_state.raw_texts, api_key, base_url, llm_model,
                progress_callback=_corr_update,
            )
            st.session_state['corrected_texts'] = corrected
            st.success(f"纠错完成，共 {total} 条，耗时 {time.time() - t_start:.0f}s")
            for idx, msg in errors:
                st.warning(f"第{idx}条纠错失败，保留原句：{msg}")

    final_texts = st.session_state.get('corrected_texts', st.session_state.get('raw_texts', []))

    # ═══════════════════════════════════════════════════════════════
    #  步骤3：生成无毒 JSONL
    # ═══════════════════════════════════════════════════════════════
    st.markdown("---")
    st.header("步骤3：生成无毒文本集（JSONL）")
    has_final = bool(final_texts)
    if st.button("📝 生成无毒 JSONL", disabled=not has_final,
                 help=None if has_final else "等待文本就绪"):
        texts_to_jsonl(final_texts, 'data/clean_corpus.jsonl')
        st.session_state['clean_jsonl'] = 'data/clean_corpus.jsonl'
        st.success(f"无毒文本已保存至 data/clean_corpus.jsonl，共 {len(final_texts)} 条")
        # 自动保存纠错后数据集
        try:
            save_corrected_dataset(
                final_texts,
                api_key=api_key if api_ready else "",
                base_url=base_url if api_ready else "",
                model=llm_model if api_ready else "",
            )
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════════════
    #  步骤4：投毒生成
    # ═══════════════════════════════════════════════════════════════
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
            progress_bar = st.progress(0, text="投毒生成中...")
            t_start = time.time()

            def _poison_update(done, total_):
                elapsed = time.time() - t_start
                eta = (elapsed / done) * (total_ - done) if done > 0 else 0
                progress_bar.progress(
                    done / total_,
                    text=f"投毒生成中 {done}/{total_} | 耗时 {elapsed:.0f}s | 预计剩余 {eta:.0f}s"
                )

            result = run_poison_generation(
                clean_path,
                poison_ratio=poison_ratio,
                api_key=api_key,
                base_url=base_url,
                model=llm_model,
                concurrency=concurrency,
                progress_callback=_poison_update,
            )
            progress_bar.progress(1.0, text="投毒完成")

            for idx, msg in result['errors']:
                st.warning(f"第{idx}条投毒失败")
                with st.expander("查看错误"):
                    st.text(msg)

            st.session_state['final_test'] = result['mixed_path']
            st.session_state['_poison_generated'] = True

            # AI 生成标题
            from core.utils import _generate_dataset_title
            ai_title = None
            if api_key and base_url and llm_model:
                try:
                    ai_title = _generate_dataset_title(
                        result['mixed_path'], api_key, base_url, llm_model)
                except Exception:
                    st.warning("AI 标题建议失败，将使用默认名称")
            st.session_state['_ai_suggested_title'] = ai_title or '测试集'

            st.success(
                f"投毒完成！共生成 {len(result['poisoned_records'])} 条有毒文本，"
                f"最终混合集：{result['mixed_path']}")

    # ── 投毒后：保存 + 有毒样本对比 ─────────────────────────────
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
            st.write("")
            if st.button("💾 确认保存", type="primary", use_container_width=True):
                saved_path, saved_title = save_dataset(
                    'data/final_test_mixed.jsonl', final_title)
                st.session_state['last_dataset_title'] = saved_title
                st.session_state['_poison_generated'] = False
                st.success(f"已保存至：`{saved_path}`")
                st.rerun()

        # 有毒样本对比（上下布局）
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
                    st.caption("原文")
                    st.write(original)
                    st.caption("有毒文本（毒点高亮）")
                    st.markdown(highlight_toxic(toxic_text, spans), unsafe_allow_html=True)
                    st.markdown("---")


def shutil_available():
    import shutil
    return shutil.which(st.session_state.bbdown_path) is not None
