"""Tab 3: 可视化分析 — 混淆矩阵指标 + 图表"""

import streamlit as st
import pandas as pd
import plotly.express as px
import io

from core.database import get_all_results, get_results_by_dataset, get_dataset_ids


def render_tab3():
    st.header("检测结果统计")
    df = get_all_results()
    if df.empty:
        st.warning("暂无检测数据，请先运行检测")
        return

    # 过滤逻辑：优先用 Tab2 传入的 current_ids，其次用持久化的 dataset_id
    current_ids = st.session_state.get('_tab2_current_ids', None)
    dataset_id = st.session_state.get('_current_dataset_id', None)

    if current_ids is not None:
        df = df[df['text_id'].isin(current_ids)].copy()
    elif dataset_id is not None:
        df = df[df['dataset_id'] == dataset_id].copy()
        if df.empty:
            df_alt = get_results_by_dataset(dataset_id)
            if not df_alt.empty:
                df = df_alt
    else:
        # 无任何过滤条件：让用户选择数据集
        all_ids = get_dataset_ids()
        if all_ids:
            choice = st.selectbox("选择要分析的数据集", all_ids)
            if choice:
                df = get_results_by_dataset(choice)
                if df.empty:
                    df = get_all_results()
                    df = df[df['dataset_id'] == choice].copy()
        else:
            df = df.copy()

    if df.empty:
        st.info("暂无当前文件的检测数据，请先运行扫描")
        return

    # 强制转为数值类型
    df['dfa_pred'] = pd.to_numeric(df['dfa_pred'], errors='coerce').fillna(-1).astype(int)
    df['llm_pred'] = pd.to_numeric(df['llm_pred'], errors='coerce').fillna(-1).astype(int)
    df['true_label'] = pd.to_numeric(df['true_label'], errors='coerce').fillna(0).astype(int)

    df['final_pred'] = ((df['dfa_pred'] == 1) | (df['llm_pred'] == 1)).astype(int)

    # 区分已扫描和未扫描样本
    scanned = df[(df['dfa_pred'] != -1) | (df['llm_pred'] != -1)]
    unscanned = len(df) - len(scanned)
    total = len(df)

    if len(scanned) > 0:
        tp = len(scanned[(scanned['true_label'] == 1) & (scanned['final_pred'] == 1)])
        tn = len(scanned[(scanned['true_label'] == 0) & (scanned['final_pred'] == 0)])
        fp = len(scanned[(scanned['true_label'] == 0) & (scanned['final_pred'] == 1)])
        fn = len(scanned[(scanned['true_label'] == 1) & (scanned['final_pred'] == 0)])

        accuracy = (tp + tn) / len(scanned) if len(scanned) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        fnr = fn / (tp + fn) if (tp + fn) > 0 else 0
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("总样本", total, delta=f"{unscanned} 未扫描" if unscanned else None)
        col2.metric("正确拦截 (TP)", tp)
        col3.metric("漏报 (FN)", fn)
        col4.metric("误报 (FP)", fp)

        col5, col6, col7, col8 = st.columns(4)
        col5.metric("准确率 (Accuracy)", f"{accuracy:.1%}")
        col6.metric("召回率 (Recall)", f"{recall:.1%}")
        col7.metric("精确率 (Precision)", f"{precision:.1%}")
        col8.metric("F1 Score", f"{f1:.3f}")

        col9, col10, col11, col12 = st.columns(4)
        col9.metric("漏报率 (FNR)", f"{fnr:.1%}")
        col10.metric("误报率 (FPR)", f"{fpr:.1%}")
        col11.metric("真阴性 (TN)", tn)
        col12.metric("已检测样本", len(scanned))
    else:
        st.info(f"共 {total} 条样本，均未检测。请先运行扫描。")

    # Excel 导出按钮
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='扫描结果')
    st.download_button("📥 导出 Excel", data=buf.getvalue(),
                       file_name=f"{dataset_id.replace('.jsonl','') if dataset_id else 'scan'}_results.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    fig1 = px.pie(
        names=['有毒', '无毒'],
        values=[df['true_label'].sum(), total - df['true_label'].sum()],
        title="测试集真实标签分布"
    )
    st.plotly_chart(fig1, width='stretch')

    dfa_hit = int((df['dfa_pred'] == 1).sum())
    llm_hit = int((df['llm_pred'] == 1).sum())
    fig2 = px.bar(
        x=['一防 DFA', '二防 LLM'],
        y=[dfa_hit, llm_hit],
        labels={'x': '防火墙', 'y': '命中数'},
        title="防火墙拦截数量对比"
    )
    st.plotly_chart(fig2, width='stretch')

    with st.expander("查看完整数据库记录"):
        st.dataframe(df)
