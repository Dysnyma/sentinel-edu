"""Tab 4: 自学习优化 — LLM 检出 → 候选词提取 → DFA 词库扩充"""

import streamlit as st
from core.self_learner import (
    collect_missed_spans, segment_candidates, score_candidates,
    deduplicate, get_existing_words, get_context_examples, apply_selected,
)
from core.dfa_scanner import DFAScanner


def render_tab4():
    st.header("自学习优化 — DFA 词库扩充")

    st.markdown("""
    从 LLM（二防）检出但 DFA（一防）漏掉的记录中，自动提取候选敏感词，
    经人工审核后追加到 `sensitive_words.txt`，提升一防覆盖率。
    """)

    # Step 1: 收集漏报数据
    st.subheader("步骤1：收集 LLM 检出但 DFA 漏报的记录")
    if st.button("📊 查询漏报数据"):
        spans, texts, count = collect_missed_spans()
        if count == 0:
            st.warning("没有找到 LLM 检出但 DFA 漏掉的记录。请先运行双重检测。")
            return
        st.session_state['_learn_spans'] = spans
        st.session_state['_learn_texts'] = texts
        st.session_state['_learn_count'] = count
        st.success(f"找到 {count} 条 DFA 漏报记录，共 {len(spans)} 个检出片段")

    if '_learn_spans' not in st.session_state:
        st.info("👆 请先点击上方按钮查询漏报数据")
        return

    spans = st.session_state['_learn_spans']
    texts = st.session_state['_learn_texts']
    count = st.session_state['_learn_count']
    st.caption(f"已加载 {count} 条漏报记录，{len(spans)} 个检出片段")

    # Step 2: 分析候选词
    st.markdown("---")
    st.subheader("步骤2：提取候选敏感词")
    if st.button("🔬 分析候选词"):
        existing = get_existing_words()
        candidates = segment_candidates(spans, existing)
        if not candidates:
            st.warning("未提取到有效候选词（所有片段已被现有词库覆盖或为无效词）")
            return
        scored = score_candidates(candidates, texts)
        deduped = deduplicate(scored)
        st.session_state['_learn_candidates'] = deduped
        st.success(f"提取到 {len(deduped)} 个候选词（已去重排序）")

    if '_learn_candidates' not in st.session_state:
        st.info("👆 请点击上方按钮分析候选词")
        return

    candidates = st.session_state['_learn_candidates']
    if not candidates:
        return

    # Step 3: 人工审核
    st.markdown("---")
    st.subheader("步骤3：审核并追加到敏感词库")
    st.caption(f"共 {len(candidates)} 个候选词，按 TF-IDF 辨别力降序排列。勾选要加入词库的词。")

    # 展示候选词表格
    rows = []
    for c in candidates[:50]:
        examples = get_context_examples(c['word'], texts)
        ctx_str = ' | '.join(examples[:2]) if examples else '—'
        rows.append({
            '选择': False,
            '候选词': c['word'],
            'TF-IDF': c['score'],
            '出现次数': c['count'],
            '上下文示例': ctx_str[:120],
        })

    edited = st.data_editor(
        rows,
        column_config={
            '选择': st.column_config.CheckboxColumn(default=False),
            'TF-IDF': st.column_config.NumberColumn(format="%.1f"),
            '上下文示例': st.column_config.TextColumn(width='large'),
        },
        hide_index=True,
        height=400,
        key='candidate_editor',
    )

    selected = [r['候选词'] for r in edited if r['选择']]

    if selected:
        st.info(f"已勾选 {len(selected)} 个候选词")

        if st.button("➕ 追加到敏感词库", type="primary"):
            added_count, new_words = apply_selected(selected)
            if added_count > 0:
                st.success(f"已添加 {added_count} 个新词到 sensitive_words.txt")
                with st.expander("查看新增词汇"):
                    st.write(new_words)
                # 清理 session 状态以便重新分析
                for k in ['_learn_spans', '_learn_texts', '_learn_count', '_learn_candidates']:
                    st.session_state.pop(k, None)
            else:
                st.info("所选词汇已全部存在于词库中，无需添加")
    else:
        st.caption("👆 请勾选上方候选词，然后点击追加按钮")
