"""Tab 4: 自学习优化 — 仅负责 Streamlit UI 组件渲染与 session_state 读写。"""

import streamlit as st
from core.learn_controller import (
    fetch_missed_records,
    analyze_candidates,
    build_candidate_display_data,
    commit_selected_words,
)


def render_tab4():
    st.header("自学习优化 — DFA 词库扩充")

    st.markdown("""
    从 LLM（二防）检出但 DFA（一防）漏掉的记录中，自动提取候选敏感词，
    经人工审核后追加到 `sensitive_words.txt`，提升一防覆盖率。
    """)

    # ── Step 1: 收集漏报数据 ──────────────────────────────────────
    st.subheader("步骤1：收集 LLM 检出但 DFA 漏报的记录")
    if st.button("📊 查询漏报数据"):
        result = fetch_missed_records(limit=50)
        if result['count'] == 0:
            st.warning("没有找到 LLM 检出但 DFA 漏掉的记录。请先运行双重检测。")
            return
        st.session_state['_learn_data'] = result
        st.success(f"找到 {result['count']} 条 DFA 漏报记录，共 {len(result['spans'])} 个检出片段")

    if '_learn_data' not in st.session_state:
        st.info("👆 请先点击上方按钮查询漏报数据")
        return

    data = st.session_state['_learn_data']
    st.caption(f"已加载 {data['count']} 条漏报记录，{len(data['spans'])} 个检出片段")

    # ── Step 2: 分析候选词 ────────────────────────────────────────
    st.markdown("---")
    st.subheader("步骤2：提取候选敏感词")
    if st.button("🔬 分析候选词"):
        candidates = analyze_candidates(data['spans'], data['texts'])
        if not candidates:
            st.warning("未提取到有效候选词（所有片段已被现有词库覆盖或为无效词）")
            return
        display_rows = build_candidate_display_data(candidates, data['texts'])
        st.session_state['_learn_candidates'] = candidates
        st.session_state['_learn_display_rows'] = display_rows
        st.success(f"提取到 {len(candidates)} 个候选词（已去重排序）")

    if '_learn_candidates' not in st.session_state:
        st.info("👆 请点击上方按钮分析候选词")
        return

    candidates = st.session_state['_learn_candidates']
    display_rows = st.session_state.get('_learn_display_rows', [])
    if not candidates:
        return

    # ── Step 3: 人工审核 ──────────────────────────────────────────
    st.markdown("---")
    st.subheader("步骤3：审核并追加到敏感词库")
    st.caption(f"共 {len(candidates)} 个候选词，按 TF-IDF 辨别力降序排列。勾选要加入词库的词。")

    edited = st.data_editor(
        display_rows,
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
            result = commit_selected_words(selected)
            if result['added_count'] > 0:
                st.success(
                    f"已添加 {result['added_count']} 个新词到 sensitive_words.txt"
                    f"{'，词库已重载生效' if result['reload_success'] else '，但重载失败'}"
                )
                with st.expander("查看新增词汇"):
                    st.write(result['new_words'])
                for k in ['_learn_data', '_learn_candidates', '_learn_display_rows']:
                    st.session_state.pop(k, None)
            else:
                st.info("所选词汇已全部存在于词库中，无需添加")
    else:
        st.caption("👆 请勾选上方候选词，然后点击追加按钮")
