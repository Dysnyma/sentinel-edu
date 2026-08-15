"""Tab 1: 测试集构建 — 仅负责 Streamlit UI 组件渲染与 session_state 读写。"""

import streamlit as st
import os
import time
import difflib

from core.asr import is_whisper_model_downloaded
from core.build_controller import (
    process_uploaded_file,
    process_bilibili_url,
    run_text_correction,
    run_poison_generation,
)
from core.utils import texts_to_jsonl, save_dataset, load_jsonl
from views.helpers import highlight_toxic

PAGE_SIZE = 10


def _pager_page(key: str, total: int, page_size: int = PAGE_SIZE) -> tuple[int, int]:
    """返回 (当前页索引, 总页数)，页码读自 session_state[key]。"""
    pages = max(1, (total + page_size - 1) // page_size)
    page = st.session_state.get(key, 0)
    page = max(0, min(page, pages - 1))
    return page, pages


def _render_pager(key: str, total: int, page_size: int = PAGE_SIZE):
    """渲染「上一页 / 页码 / 下一页」翻页按钮。"""
    page, pages = _pager_page(key, total, page_size)
    col_prev, col_info, col_next = st.columns([1, 2, 1])
    with col_prev:
        if st.button("◀ 上一页", disabled=page <= 0, key=f"{key}_prev",
                     use_container_width=True):
            st.session_state[key] = page - 1
            st.rerun()
    with col_info:
        st.markdown(f"<div style='text-align:center'>第 {page + 1} / {pages} 页</div>",
                    unsafe_allow_html=True)
    with col_next:
        if st.button("下一页 ▶", disabled=page >= pages - 1, key=f"{key}_next",
                     use_container_width=True):
            st.session_state[key] = page + 1
            st.rerun()


def _render_stage_progress() -> tuple:
    """创建分阶段进度条，返回 ``(stage_cb, update_cb)``。

    - ``stage_cb(text)``：切换阶段时调用，重置进度为 0 并更新阶段文案。
    - ``update_cb(pct)``：进度更新时调用，保留当前阶段文案。
    """
    progress_bar = st.progress(0, text="准备中...")
    current_stage = {"text": "准备中..."}

    def _stage(text):
        current_stage["text"] = text
        progress_bar.progress(0, text=text)

    def _update(pct):
        progress_bar.progress(pct, text=f"{current_stage['text']} {pct * 100:.0f}%")

    return _stage, _update


def _highlight_diff(original: str, corrected: str) -> tuple[str, str]:
    """用 difflib 逐字符对比原文与纠错后文本，返回 (原文字符串HTML, 纠正字符串HTML)。

    删除内容用红色背景（``#ffcccc``），新增内容用绿色背景（``#ccffcc``），替换内容分
    别标注。
    """
    if original == corrected:
        return original, corrected

    orig_html, corr_html = [], []
    matcher = difflib.SequenceMatcher(None, original, corrected)
    for op, i1, i2, j1, j2 in matcher.get_opcodes():
        if op == 'equal':
            seg = original[i1:i2]
            orig_html.append(seg)
            corr_html.append(seg)
        elif op == 'replace':
            orig_html.append(f'<span style="background:#ffcccc">{original[i1:i2]}</span>')
            corr_html.append(f'<span style="background:#ccffcc">{corrected[j1:j2]}</span>')
        elif op == 'delete':
            orig_html.append(f'<span style="background:#ffcccc;text-decoration:line-through">{original[i1:i2]}</span>')
            corr_html.append('<span style="background:#eee"> </span>')
        elif op == 'insert':
            orig_html.append('<span style="background:#eee"> </span>')
            corr_html.append(f'<span style="background:#ccffcc">{corrected[j1:j2]}</span>')
    return ''.join(orig_html), ''.join(corr_html)


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
                if use_local_whisper and not is_whisper_model_downloaded(local_whisper_model):
                    st.info(f"📥 首次使用需下载 Whisper {local_whisper_model} 模型（约500MB），请耐心等待...")
                stage_cb, update_cb = _render_stage_progress()
                try:
                    transcript = process_uploaded_file(
                        file_bytes, uploaded_file.name,
                        use_local=use_local_whisper,
                        local_model=local_whisper_model,
                        ffmpeg_path=st.session_state.ffmpeg_path,
                        api_key=api_key,
                        base_url=base_url,
                        initial_prompt=prompt_text,
                        stage_callback=stage_cb,
                        progress_callback=update_cb if use_local_whisper else None,
                    )
                    update_cb(1.0)
                    st.success("转写完成")
                    st.session_state['asr_transcript'] = transcript
                except Exception as e:
                    st.error(f"处理文件失败：{e}")
                    st.session_state.pop('_last_file_id', None)

            if 'asr_transcript' in st.session_state:
                edited = st.text_area(
                    "转写结果（可手动编辑）", st.session_state['asr_transcript'],
                    height=200, key="transcript_editor")
                raw_texts = [s for s in edited.split('。') if s.strip()]
            else:
                st.info("切换模型后请重新上传文件进行转写")

    # ═══════════════════════════════════════════════════════════════
    #  输入方式 2：B站视频链接
    # ═══════════════════════════════════════════════════════════════
    elif input_method == "🔗 B站视频链接":
        bili_url = st.text_input("B站视频地址")
        if bili_url and st.button("开始解析并下载"):
            if not shutil_available():
                st.error("BBDown 不可用，请检查安装")
            else:
                if use_local_whisper and not is_whisper_model_downloaded(local_whisper_model):
                    st.info(f"📥 首次使用需下载 Whisper {local_whisper_model} 模型（约500MB），请耐心等待...")
                stage_cb, update_cb = _render_stage_progress()
                try:
                    transcript = process_bilibili_url(
                        bili_url,
                        bbdown_path=st.session_state.bbdown_path,
                        ffmpeg_path=st.session_state.ffmpeg_path,
                        use_local=use_local_whisper,
                        local_model=local_whisper_model,
                        api_key=api_key,
                        base_url=base_url,
                        initial_prompt=prompt_text,
                        progress_callback=update_cb if use_local_whisper else None,
                    )
                    update_cb(1.0)
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
            st.session_state['correction_errors'] = dict(errors)
            st.success(f"纠错完成，共 {total} 条，耗时 {time.time() - t_start:.0f}s")
            if errors:
                st.warning(f"⚠️ 有 {len(errors)} 条纠错失败（已保留原句），详见对比区域标注")

    # ── 纠错对比区域 ────────────────────────────────────────────
    corrected = st.session_state.get('corrected_texts')
    raw = st.session_state.get('raw_texts')
    corr_errors = st.session_state.get('correction_errors', {})
    if corrected and raw and len(corrected) == len(raw):
        with st.expander(f"📊 纠错前后对比（共 {len(corrected)} 条）"):
            page, pages = _pager_page("corr_page", len(corrected))
            start = page * PAGE_SIZE
            for i in range(start, min(start + PAGE_SIZE, len(corrected))):
                orig, corr = raw[i], corrected[i]
                orig_html, corr_html = _highlight_diff(orig, corr)
                if i in corr_errors:
                    st.markdown(f"**条目 {i + 1}** ⚠️ 纠错失败，已保留原句（{corr_errors[i]}）")
                    st.caption("原文")
                    st.markdown(orig_html, unsafe_allow_html=True)
                    st.caption("纠错后（已回退为原文）")
                    st.markdown(corr_html, unsafe_allow_html=True)
                else:
                    st.markdown(f"**条目 {i + 1}**" + ("（无改动）" if orig == corr else ""))
                    col_l, col_r = st.columns(2)
                    with col_l:
                        st.caption("原文")
                        st.markdown(orig_html, unsafe_allow_html=True)
                    with col_r:
                        st.caption("纠错后")
                        st.markdown(corr_html, unsafe_allow_html=True)
                st.markdown("---")
            if pages > 1:
                _render_pager("corr_page", len(corrected))

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
        st.session_state['_clean_generated'] = True
        st.success(f"无毒文本已生成：data/clean_corpus.jsonl，共 {len(final_texts)} 条")

    # ── 生成后数据预览（前 5 条） ─────────────────────────────
    if st.session_state.get('_clean_generated') and os.path.exists('data/clean_corpus.jsonl'):
        with st.expander("📋 预览生成的无毒数据（前 5 条）"):
            preview = load_jsonl('data/clean_corpus.jsonl')[:5]
            for rec in preview:
                st.markdown(f"- **id**: `{rec['id']}` | **text**: {rec['text'][:80]}{'…' if len(rec['text']) > 80 else ''}")

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

            if result['errors']:
                st.warning(f"⚠️ 有 {len(result['errors'])} 条投毒失败（已跳过，不影响其他样本）")
                with st.expander("查看失败详情"):
                    for idx, msg in result['errors']:
                        brief = msg if len(msg) <= 120 else msg[:120] + "…"
                        st.markdown(f"**第 {idx + 1} 条失败**：{brief}")

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

    # ── 投毒后：统一保存（无毒 + 有毒） + 有毒样本对比 ─────────
    if st.session_state.get('_poison_generated') and os.path.exists('data/final_test_mixed.jsonl'):
        st.markdown("---")
        st.subheader("💾 保存测试集（无毒 + 有毒）")
        ai_title = st.session_state.get('_ai_suggested_title', '测试集')
        col_title, col_btn = st.columns([3, 1])
        with col_title:
            final_title = st.text_input(
                "数据集标题", value=ai_title,
                help="AI 自动建议，可手动修改；保存后两个数据集使用同一标题",
                key="dataset_title_input")
        with col_btn:
            st.write("")
            if st.button("💾 确认保存", type="primary", use_container_width=True):
                saved_paths = []
                saved_title = final_title
                for src in ['data/clean_corpus.jsonl', 'data/final_test_mixed.jsonl']:
                    if os.path.exists(src):
                        try:
                            saved_path, saved_title = save_dataset(src, final_title)
                            saved_paths.append(saved_path)
                        except Exception as e:
                            st.warning(f"保存 {src} 失败：{e}")
                st.session_state['last_dataset_title'] = saved_title
                st.session_state['_poison_generated'] = False
                if saved_paths:
                    st.success("已保存：\n" + "\n".join(f"- `{p}`" for p in saved_paths))
                st.rerun()

        # 有毒样本对比（上下布局，分页展示）
        final_data = load_jsonl('data/final_test_mixed.jsonl')
        toxic_samples = [r for r in final_data if r.get('is_toxic')]
        if toxic_samples:
            with st.expander(f"🔍 有毒样本对比（共 {len(toxic_samples)} 条）"):
                page, pages = _pager_page("toxic_page", len(toxic_samples))
                start = page * PAGE_SIZE
                for i in range(start, min(start + PAGE_SIZE, len(toxic_samples))):
                    rec = toxic_samples[i]
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
                if pages > 1:
                    _render_pager("toxic_page", len(toxic_samples))


def shutil_available():
    import shutil
    return shutil.which(st.session_state.bbdown_path) is not None
