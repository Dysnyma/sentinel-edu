"""Tab 2: 安全检测 — 文件测试集 或 直接输入文本 → DFA → LLM"""

import streamlit as st
import os
from pathlib import Path

from core.dfa_scanner import DFAScanner
from core.llm_scanner import llm_scan
from core.database import init_db, save_result, get_all_results, update_llm_result
from core.config import save_session_state
from core.utils import load_jsonl, list_datasets, delete_dataset
from views.helpers import (
    context_snippet, strategy_to_color, safe_json_loads, to_native, run_concurrently
)


def _init_db_records(all_data, dataset_id):
    """为新样本插入初始记录（避免覆盖已有检测结果）"""
    init_db()
    existing_all = get_all_results()
    already_in_db = set(existing_all['text_id']) if not existing_all.empty else set()
    for rec in all_data:
        if rec['id'] in already_in_db:
            continue
        true_label = 1 if rec.get('is_toxic') else 0
        try:
            save_result(rec['id'], true_label, -1, -1, [], 0, 0, [],
                        dataset_id=dataset_id, text=rec.get('text', ''))
        except Exception:
            st.warning(f"样本 {rec['id']} 初始记录写入失败")


def _dfa_scan_all(all_data, dataset_id, progress_placeholder=None):
    """DFA 全量扫描，返回 {text_id: (dfa_hit, dfa_words)} 并写库"""
    import time
    scanner = DFAScanner('sensitive_words.txt')
    results = {}
    total = len(all_data)
    t_start = time.time()
    for i, rec in enumerate(all_data):
        text = rec['text']
        dfa_hit, dfa_words = scanner.scan(text)
        results[rec['id']] = (dfa_hit, dfa_words)
        true_label = 1 if rec.get('is_toxic') else 0
        reason = f'[显性敏感词]：命中关键词 "{", ".join(dfa_words)}"' if dfa_hit else None
        save_result(rec['id'], true_label, int(dfa_hit), -1, dfa_words, 0, 0,
                    llm_spans=None, llm_reason=reason,
                    dataset_id=dataset_id, text=text)
        if progress_placeholder is not None:
            elapsed = time.time() - t_start
            eta = (elapsed / (i + 1)) * (total - i - 1) if i > 0 else 0
            progress_placeholder.progress(
                (i + 1) / total,
                text=f"一防 DFA 扫描中... {i + 1}/{total} | 耗时 {elapsed:.0f}s | 预计剩余 {eta:.0f}s"
            )
    return results


def _llm_scan_candidates(candidates, api_key, base_url, llm_model, concurrency, dataset_id):
    """对候选文本并发执行 LLM 扫描并写库"""
    progress_bar = st.progress(0, text="二防 LLM 扫描中...")
    tasks = [(llm_scan, (rec['text'], api_key, base_url, llm_model, dfa_words))
             for rec, dfa_words in candidates]
    llm_results = run_concurrently(
        tasks, max_workers=concurrency,
        progress_placeholder=progress_bar, progress_text="二防 LLM 扫描中"
    )
    for (rec, dfa_words), res in zip(candidates, llm_results):
        true_label = 1 if rec.get('is_toxic') else 0
        if isinstance(res, Exception):
            llm_pred, llm_spans, llm_time, llm_reason = -1, [], 0, ''
        else:
            llm_pred = int(res.get('is_toxic', False))
            llm_spans = res.get('toxic_spans', [])
            llm_time = res.get('time_cost', 0)
            category = res.get('category', '隐性偏颇')
            reason_text = res.get('reason', '')
            llm_reason = f'[{category}]：{reason_text}' if llm_pred == 1 else ''
        save_result(rec['id'], true_label, -1, llm_pred, None, 0, llm_time, llm_spans,
                    llm_reason=llm_reason, dataset_id=dataset_id, text=rec.get('text', ''))
    progress_bar.empty()


def _render_status_table(df_all, current_ids):
    """样本检测状态总览"""
    st.markdown("---")
    st.subheader("样本检测状态")
    if df_all.empty:
        return df_all
    df_all = df_all[df_all['text_id'].isin(current_ids)].copy()
    if df_all.empty:
        st.info('暂未检测，请点击上方批量检测按钮')
        return df_all

    def status(dfa, llm):
        dfa_str = "✔️" if dfa == 1 else ("✖️" if dfa == 0 else "⬜")
        llm_str = "✔️" if llm == 1 else ("✖️" if llm == 0 else "⬜")
        return f"{dfa_str} / {llm_str}"
    df_all['status'] = df_all.apply(lambda r: status(r['dfa_pred'], r['llm_pred']), axis=1)
    st.dataframe(df_all[['text_id', 'true_label', 'status']], width='stretch')
    st.caption(
        '📖 **列说明**  |  '
        '`text_id`=样本ID  |  '
        '`true_label`=真实标签（`1`=🦠有毒, `0`=✅无毒）  |  '
        '`status`=检测状态（左 **DFA** / 右 **LLM**）  \n'
        '符号含义：`✔️`=命中拦截  |  `✖️`=安全通过  |  `⬜`=未检测'
    )
    return df_all


def _render_batch_highlight(df_all, all_data):
    """批量高亮对比"""
    st.markdown("---")
    st.subheader("🔦 批量高亮对比")
    if df_all.empty:
        return
    with st.expander('展开查看所有样本的双防检测高亮', expanded=False):
        batch_limit = min(len(df_all), 50)
        for idx in range(batch_limit):
            row = df_all.iloc[idx]
            rec = next((r for r in all_data if r['id'] == row['text_id']), None)
            if rec is None:
                continue
            text = rec.get('text', '')
            dfa_words = safe_json_loads(row['hit_words'])
            llm_spans = safe_json_loads(row['llm_spans'])
            dfa_hl, _ = context_snippet(text, dfa_words, color='#ff4d4d')
            llm_hl, _ = context_snippet(text, llm_spans, color='#ffc107')
            llm_hl = llm_hl.replace('color:white', 'color:black')
            label_icon = '🦠有毒' if row['true_label'] == 1 else '✅无毒'
            llm_reason_val = row.get('llm_reason', '')
            st.markdown(f'**ID: `{row["text_id"]}`**  |  真实标签: {label_icon}')
            if llm_reason_val and str(llm_reason_val) != 'nan' and str(llm_reason_val) != 'None':
                st.caption(f'📝 {llm_reason_val}')
            col1, col2 = st.columns(2)
            with col1:
                st.caption('🔴 一防 DFA (显性敏感词)')
                st.markdown(dfa_hl or '(未检测或无命中)', unsafe_allow_html=True)
            with col2:
                st.caption('🟡 二防 LLM (隐性偏颇)')
                st.markdown(llm_hl or '(未检测或无命中)', unsafe_allow_html=True)
            if idx < batch_limit - 1:
                st.markdown('---')
        if len(df_all) > 50:
            st.info(f'仅展示前 50 条，共 {len(df_all)} 条')


def _render_detail_view(df_all, all_data):
    """样本深度对比（筛选 + 三栏高亮 + 命中分析）"""
    st.markdown("---")
    st.subheader("🔍 样本深度对比")
    if df_all.empty:
        return

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        filter_toxic = st.selectbox("真实标签", ["全部", "有毒", "无毒"])
    with col_f2:
        filter_dfa = st.selectbox("DFA 结果", ["全部", "命中", "安全", "未检测"])
    with col_f3:
        filter_llm = st.selectbox("LLM 结果", ["全部", "命中", "安全", "未检测"])
    with col_f4:
        search_text = st.text_input("🔍 文本搜索", placeholder="输入关键词...")

    filtered_df = df_all.copy()
    if filter_toxic == "有毒":
        filtered_df = filtered_df[filtered_df['true_label'] == 1]
    elif filter_toxic == "无毒":
        filtered_df = filtered_df[filtered_df['true_label'] == 0]
    if filter_dfa == "命中":
        filtered_df = filtered_df[filtered_df['dfa_pred'] == 1]
    elif filter_dfa == "安全":
        filtered_df = filtered_df[filtered_df['dfa_pred'] == 0]
    elif filter_dfa == "未检测":
        filtered_df = filtered_df[filtered_df['dfa_pred'] == -1]
    if filter_llm == "命中":
        filtered_df = filtered_df[filtered_df['llm_pred'] == 1]
    elif filter_llm == "安全":
        filtered_df = filtered_df[filtered_df['llm_pred'] == 0]
    elif filter_llm == "未检测":
        filtered_df = filtered_df[filtered_df['llm_pred'] == -1]
    if search_text:
        matched_ids = {r['id'] for r in all_data if search_text.lower() in r.get('text', '').lower()}
        filtered_df = filtered_df[filtered_df['text_id'].isin(matched_ids)]

    sample_ids = filtered_df['text_id'].tolist()
    st.caption(f'共 {len(filtered_df)} 条匹配结果')

    if not sample_ids:
        st.info('没有符合筛选条件的样本')
        return

    selected_id = st.selectbox("选择样本", sample_ids)
    if not selected_id:
        return

    rec = next((r for r in all_data if r['id'] == selected_id), None)
    if rec is None:
        st.warning(f'数据 ID「{selected_id}」在当前选中的 JSONL 文件中未找到。')
        db_row = df_all[df_all['text_id'] == selected_id].iloc[0]
        st.markdown("**📊 数据库已有检测记录（仅展示，无原文）**")
        st.json({
            "text_id": to_native(selected_id),
            "真实标签": "有毒" if to_native(db_row['true_label']) == 1 else "无毒",
            "DFA 预测": to_native(db_row['dfa_pred']),
            "LLM 预测": to_native(db_row['llm_pred']),
            "DFA 命中词": safe_json_loads(db_row['hit_words']),
            "LLM 检出片段": safe_json_loads(db_row['llm_spans']),
            "判定理由": str(db_row.get('llm_reason', '')) if str(db_row.get('llm_reason', '')) not in ('nan', 'None', '') else '无',
        })
        return

    db_row = df_all[df_all['text_id'] == selected_id].iloc[0]
    is_toxic = rec.get('is_toxic', False)
    original = rec.get('original_text') or (rec.get('text') if not is_toxic else '（无原文）')
    toxic_text = rec.get('text', '')
    true_spans = rec.get('toxic_spans', [])
    strategy = rec.get('attack_strategy', '—')
    dfa_pred = db_row['dfa_pred']
    llm_pred = db_row['llm_pred']
    dfa_words = safe_json_loads(db_row['hit_words'])
    llm_spans = safe_json_loads(db_row['llm_spans'])

    # 原文
    st.markdown("**📄 原始文本（毒点上下文）**")
    true_spans_for_ctx = true_spans if is_toxic else []
    original_ctx, orig_trunc = context_snippet(original, true_spans_for_ctx)
    st.markdown(original_ctx, unsafe_allow_html=True)
    if orig_trunc:
        with st.expander('查看完整原文'):
            st.info(original)

    # 三栏高亮对比
    st.markdown("---")
    st.markdown("**🛡️ 三栏高亮对比（上下文）**")
    col_a, col_b, col_c = st.columns(3)
    true_color = strategy_to_color(strategy) if is_toxic else '#ff4d4d'
    with col_a:
        if is_toxic:
            gradient_label = {'显性': '🔴 显性敏感词', '隐性': '🟡 隐性偏颇', '比喻': '🟠 不当比喻'}.get(
                strategy[:2] if strategy else '', '🎯 预设毒点')
            st.caption(gradient_label)
            true_hl, _ = context_snippet(toxic_text, true_spans, color=true_color)
            if '#ffc107' in true_color:
                true_hl = true_hl.replace('color:white', 'color:black')
            st.markdown(true_hl or '(无)', unsafe_allow_html=True)
            st.caption(f'策略: {strategy}')
        else:
            st.caption('✅ 无毒样本')
            st.write(toxic_text[:200] + ('...' if len(toxic_text) > 200 else ''))
    with col_b:
        st.caption('🔴 一防 DFA (显性敏感词)')
        if dfa_pred == -1:
            st.info('未检测')
        elif dfa_pred == 1:
            st.error(f'命中: {dfa_words}')
        else:
            st.success('安全')
        dfa_hl, _ = context_snippet(toxic_text, dfa_words, color='#ff4d4d')
        st.markdown(dfa_hl or '(无命中)', unsafe_allow_html=True)
    with col_c:
        st.caption('🟡 二防 LLM (隐性偏颇)')
        if llm_pred == -1:
            st.info('未检测')
        elif llm_pred == 1:
            st.error(f'命中: {llm_spans}')
        else:
            st.success('安全')
        llm_hl, _ = context_snippet(toxic_text, llm_spans, color='#ffc107')
        llm_hl = llm_hl.replace('color:white', 'color:black')
        st.markdown(llm_hl or '(无命中)', unsafe_allow_html=True)

    # 判定理由
    llm_reason_val = db_row.get('llm_reason', '')
    if llm_reason_val and str(llm_reason_val) not in ('nan', 'None', ''):
        st.markdown("---")
        st.markdown(f"📝 **判定理由**：{llm_reason_val}")

    # 命中分析
    if is_toxic:
        st.markdown("---")
        st.subheader("📊 检测效果分析（命中 vs 预设毒点）")
        true_set = set(true_spans)
        col_a1, col_a2 = st.columns(2)
        with col_a1:
            st.markdown("**🔴 DFA 检测分析**")
            if dfa_pred == -1:
                st.caption('未运行 DFA 检测')
            else:
                dfa_set = set(dfa_words)
                dfa_hits = {t for t in true_set if t in dfa_words}
                remaining_dfa = true_set - dfa_hits
                for t in remaining_dfa:
                    if any(t in d for d in dfa_words) or any(d in t for d in dfa_words):
                        dfa_hits.add(t)
                dfa_miss = true_set - dfa_hits
                dfa_extra = dfa_set - true_set
                st.write(f"✅ 命中：{list(dfa_hits) if dfa_hits else '无'}")
                st.write(f"❌ 漏报：{list(dfa_miss) if dfa_miss else '无'}")
                st.write(f"⚠️ 额外检出：{list(dfa_extra) if dfa_extra else '无'}")
        with col_a2:
            st.markdown("**🟡 LLM 检测分析**")
            if llm_pred == -1:
                st.caption('未运行 LLM 检测')
            else:
                llm_set = set(llm_spans)
                llm_hits = {t for t in true_set if t in llm_spans}
                remaining_llm = true_set - llm_hits
                for t in remaining_llm:
                    if any(t in span for span in llm_spans) or any(span in t for span in llm_spans):
                        llm_hits.add(t)
                llm_miss = true_set - llm_hits
                llm_extra = llm_set - true_set
                st.write(f"✅ 命中：{list(llm_hits) if llm_hits else '无'}")
                st.write(f"❌ 漏报：{list(llm_miss) if llm_miss else '无'}")
                st.write(f"⚠️ 额外检出：{list(llm_extra) if llm_extra else '无'}")
    else:
        st.caption("无毒样本无需进行命中分析。")


def _render_inline_detect(api_ready, api_key, base_url, llm_model):
    """直接输入文本并检测（不依赖 JSONL 文件）"""
    st.markdown("---")
    st.subheader("✏️ 输入待检测文本")
    inline_text = st.text_area("请输入课堂文本内容", height=150, placeholder="在此粘贴或输入文本...")

    if not inline_text.strip():
        st.caption("请输入文本后点击检测")
        return

    if st.button("🔍 开始检测", type="primary", disabled=not api_ready):
        scanner = DFAScanner('sensitive_words.txt')

        # DFA
        with st.spinner("一防 DFA 扫描中..."):
            dfa_hit, dfa_words = scanner.scan(inline_text)

        # LLM 全量扫描（DFA 命中≠有毒，由 LLM 结合上下文做最终判定）
        llm_pred, llm_spans, llm_reason = -1, [], ''
        if api_ready:
            with st.spinner("二防 LLM 语义分析中..."):
                try:
                    result = llm_scan(inline_text, api_key, base_url, llm_model, dfa_words)
                    llm_pred = int(result.get('is_toxic', False))
                    llm_spans = result.get('toxic_spans', [])
                    if llm_pred == 1:
                        category = result.get('category', '隐性偏颇')
                        llm_reason = f"[{category}]：{result.get('reason', '')}"
                except Exception as e:
                    st.warning(f"LLM 扫描失败：{e}")

        # 展示结果
        st.markdown("---")
        st.subheader("📊 检测结果")
        overall_toxic = llm_pred == 1
        if overall_toxic:
            st.error("⚠️ 该文本被判定为**有毒**")
            if llm_reason:
                st.markdown(f"📝 **判定理由**：{llm_reason}")
        else:
            st.success("✅ 该文本判定为**安全**")

        col_r1, col_r2 = st.columns(2)
        with col_r1:
            st.markdown("**🔴 一防 DFA（关键词线索）**")
            if dfa_hit:
                st.warning(f"发现关键词：{dfa_words}（供 LLM 参考）")
                dfa_display, _ = context_snippet(inline_text, dfa_words, color='#ff4d4d')
            else:
                st.success("未发现敏感词")
                dfa_display = inline_text[:300]
            st.markdown(dfa_display, unsafe_allow_html=True)

        with col_r2:
            st.markdown("**🟡 二防 LLM**")
            if llm_pred == 1:
                st.error(f"检出片段：{llm_spans}")
                llm_display, _ = context_snippet(inline_text, llm_spans, color='#ffc107')
                llm_display = llm_display.replace('color:white', 'color:black')
            elif llm_pred == 0:
                st.success("安全通过")
                llm_display = inline_text[:300]
            else:
                st.info("未检测（DFA 已拦截）")
                llm_display = '(跳过)'
            st.markdown(llm_display, unsafe_allow_html=True)


def render_tab2(api_ready, api_key, base_url, llm_model, concurrency):
    st.header("双重安全检测")

    detect_mode = st.radio(
        "选择检测模式", ["📂 选择测试集文件", "✏️ 直接输入文本"], horizontal=True)

    if detect_mode == "✏️ 直接输入文本":
        _render_inline_detect(api_ready, api_key, base_url, llm_model)
        return

    # --- 文件模式 ---
    file_category = st.radio(
        "文件来源", ["📂 中间产物（临时文件）", "💾 已保存数据集"], horizontal=True)

    if file_category == "📂 中间产物（临时文件）":
        temp_files = {f.name: os.path.join("data", f.name)
                      for f in sorted(Path("data").glob('*.jsonl'))}
        if not temp_files:
            st.info("暂无临时文件，请先在「测试集构建」中生成")
            st.stop()
        selected_label = st.selectbox("选择临时文件", options=list(temp_files.keys()))
        if not selected_label:
            st.stop()
        test_file_path = temp_files[selected_label]
    else:
        saved = list_datasets()
        if not saved:
            st.info("暂无已保存的数据集，请在「测试集构建」中生成并保存")
            st.stop()
        options = {f"💾 {ds['title']} ({ds['created']}, {ds['total']}条)": ds
                   for ds in saved}
        selected_label = st.selectbox("选择已保存的数据集", options=list(options.keys()))
        if not selected_label:
            st.stop()
        selected_ds = options[selected_label]
        test_file_path = selected_ds['path']

        # 删除按钮
        col_info, col_del = st.columns([3, 1])
        with col_del:
            with st.popover("🗑️ 删除此数据集"):
                st.warning(f"确定要删除「{selected_ds['title']}」吗？")
                st.caption(f"文件：{selected_ds['path']}")
                if st.button("确认删除", type="primary"):
                    delete_dataset(selected_ds['path'])
                    st.success("已删除")
                    st.rerun()
    all_data = load_jsonl(test_file_path)
    dataset_id = os.path.basename(test_file_path)
    st.session_state['_current_dataset_id'] = dataset_id
    st.success(f"已加载 {len(all_data)} 条样本，其中 {sum(1 for r in all_data if r.get('is_toxic'))} 条有毒")

    _init_db_records(all_data, dataset_id)
    current_ids = {r['id'] for r in all_data}
    st.session_state['_tab2_current_ids'] = current_ids
    save_session_state()

    # ----- 功能按钮区 -----
    st.subheader("批量检测")
    col_main, col_debug1, col_debug2 = st.columns([2, 1, 1])

    with col_main:
        if st.button("🚀 自动检测 (DFA → LLM)", type="primary", disabled=not api_ready, width='stretch'):
            # — 阶段1：DFA 全量扫描（收集线索）—
            progress = st.progress(0, text="一防 DFA 扫描中...")
            dfa_results = _dfa_scan_all(all_data, dataset_id, progress_placeholder=progress)
            progress.empty()
            dfa_hit_count = sum(1 for hit, _ in dfa_results.values() if hit)

            # — 阶段2：LLM 全量扫描（DFA 命中≠有毒，LLM 结合上下文做最终判决）—
            # 所有文本都送 LLM，DFA 命中词作为线索（LLM 会甄别否定句/引述等正当语境）
            all_candidates = [(rec, dfa_results[rec['id']][1]) for rec in all_data]
            _llm_scan_candidates(all_candidates, api_key, base_url, llm_model, concurrency, dataset_id)

            st.success(
                f"检测完成！DFA 发现 {dfa_hit_count} 个关键词线索，"
                f"全部 {len(all_data)} 条已由 LLM 结合上下文做最终判定"
            )

    with col_debug1:
        if st.button("🔰 仅 DFA 扫描", width='stretch'):
            progress = st.progress(0, text="DFA 扫描中...")
            _dfa_scan_all(all_data, dataset_id, progress_placeholder=progress)
            progress.empty()
            st.success("DFA 扫描完成")

    with col_debug2:
        if st.button("🤖 仅 LLM 扫描", disabled=not api_ready, width='stretch'):
            df = get_all_results()
            pre_scan = {row['text_id']: safe_json_loads(row['hit_words'])
                        for _, row in df[df['text_id'].isin(current_ids)].iterrows()}
            progress_bar = st.progress(0)
            tasks = [(llm_scan, (rec['text'], api_key, base_url, llm_model, pre_scan.get(rec['id'])))
                     for rec in all_data]
            llm_results = run_concurrently(
                tasks, max_workers=concurrency,
                progress_placeholder=progress_bar, progress_text="LLM 扫描中"
            )
            for i, (rec, res) in enumerate(zip(all_data, llm_results)):
                true_label = 1 if rec.get('is_toxic') else 0
                if isinstance(res, Exception):
                    update_llm_result(rec['id'], -1, 0, [], '')
                else:
                    llm_pred = int(res.get('is_toxic', False))
                    llm_time = res.get('time_cost', 0)
                    llm_spans = res.get('toxic_spans', [])
                    category = res.get('category', '隐性偏颇')
                    reason_text = res.get('reason', '')
                    llm_reason = f'[{category}]：{reason_text}' if llm_pred == 1 else ''
                    existing_row = df[df['text_id'] == rec['id']]
                    dfa_pred = existing_row['dfa_pred'].values[0] if not existing_row.empty else -1
                    dfa_hit_words = safe_json_loads(existing_row['hit_words'].values[0]) if not existing_row.empty else []
                    save_result(rec['id'], true_label, dfa_pred, llm_pred, dfa_hit_words, 0, llm_time, llm_spans,
                                llm_reason=llm_reason, dataset_id=dataset_id, text=rec.get('text', ''))
            st.success("LLM 扫描完成")

    # ----- 结果展示 -----
    df_all = get_all_results()
    df_all = _render_status_table(df_all, current_ids)

    # CSV 导出按钮
    if not df_all.empty:
        csv = df_all.to_csv(index=False)
        st.download_button("📥 导出 CSV", data=csv,
                           file_name=f"{dataset_id.replace('.jsonl', '')}_results.csv",
                           mime="text/csv")

    _render_batch_highlight(df_all, all_data)
    _render_detail_view(df_all, all_data)
