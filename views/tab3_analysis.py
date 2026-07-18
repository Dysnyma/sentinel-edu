"""Tab 3: 可视化分析 — 仅负责图表渲染与数据展示。"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import os

from core.database import get_all_results, get_results_by_dataset, get_dataset_ids
from core.utils import load_jsonl
from core.analysis_controller import (
    load_and_prepare_data,
    compute_confusion_metrics,
    compute_independent_metrics,
    compute_strategy_analysis,
    compute_funnel_data,
)


def _load_strategy_map(dataset_id):
    """从 JSONL 文件中加载 text_id -> attack_strategy 映射"""
    candidates = [
        os.path.join('data', 'datasets', dataset_id),
        os.path.join('data', dataset_id),
    ]
    for path in candidates:
        if os.path.exists(path):
            data = load_jsonl(path)
            return {r['id']: r.get('attack_strategy', '无毒') for r in data}
    return {}


def render_tab3():
    st.header("检测结果统计")
    df_raw = get_all_results()
    if df_raw.empty:
        st.warning("暂无检测数据，请先运行检测")
        return

    current_ids = st.session_state.get('_tab2_current_ids', None)
    dataset_id = st.session_state.get('_current_dataset_id', None)

    # 数据集选择（兜底）
    if current_ids is None and dataset_id is None:
        all_ids = get_dataset_ids()
        if all_ids:
            choice = st.selectbox("选择要分析的数据集", all_ids)
            if choice:
                df_raw = get_results_by_dataset(choice)
                dataset_id = choice

    strategy_map = _load_strategy_map(dataset_id) if dataset_id else {}

    df = load_and_prepare_data(df_raw, dataset_id, current_ids, strategy_map)
    if df.empty:
        st.info("暂无当前文件的检测数据，请先运行扫描")
        return

    scanned = df[(df['dfa_pred'] != -1) | (df['llm_pred'] != -1)]
    unscanned = len(df) - len(scanned)
    total = len(df)

    # ========== 核心指标 ==========
    if len(scanned) > 0:
        metrics = compute_confusion_metrics(scanned)
        indep = compute_independent_metrics(scanned)
        funnel = compute_funnel_data(scanned, total)

        st.subheader("核心指标")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("总样本", total, delta=f"{unscanned} 未扫描" if unscanned else None)
        col2.metric("正确拦截 (TP)", metrics['tp'])
        col3.metric("漏报 (FN)", metrics['fn'])
        col4.metric("误报 (FP)", metrics['fp'])

        col5, col6, col7, col8 = st.columns(4)
        col5.metric("准确率 (Accuracy)", f"{metrics['accuracy']:.1%}")
        col6.metric("召回率 (Recall)", f"{metrics['recall']:.1%}")
        col7.metric("精确率 (Precision)", f"{metrics['precision']:.1%}")
        col8.metric("F1 Score", f"{metrics['f1']:.3f}")

        col9, col10, col11, col12 = st.columns(4)
        col9.metric("漏报率 (FNR)", f"{metrics['fnr']:.1%}")
        col10.metric("误报率 (FPR)", f"{metrics['fpr']:.1%}")
        col11.metric("真阴性 (TN)", metrics['tn'])
        col12.metric("已检测样本", metrics['scanned_count'])

        # 耗时指标
        st.subheader("检测耗时")
        tc1, tc2, tc3, tc4 = st.columns(4)
        tc1.metric("DFA 平均耗时", f"{metrics['avg_dfa_time']:.3f}s")
        tc2.metric("LLM 平均耗时", f"{metrics['avg_llm_time']:.1f}s")
        tc3.metric("总耗时", f"{metrics['total_time']:.1f}s")
        tc4.metric("已检测", f"{metrics['scanned_count']} 条")

        # ========== 混淆矩阵热力图 ==========
        st.markdown("---")
        st.subheader("混淆矩阵")
        cm = [[metrics['tn'], metrics['fp']],
              [metrics['fn'], metrics['tp']]]
        fig_cm = px.imshow(
            cm,
            x=['预测安全', '预测有毒'],
            y=['真实安全', '真实有毒'],
            text_auto=True,
            color_continuous_scale='Reds',
            title="双防联合判定混淆矩阵",
            labels=dict(x="预测类别", y="真实类别", color="样本数"),
        )
        st.plotly_chart(fig_cm, width='stretch')

        # ========== 双防独立指标对比 ==========
        st.markdown("---")
        st.subheader("双防独立指标对比")

        fig_comp = go.Figure(data=[
            go.Bar(name='一防 DFA', x=['准确率', '召回率', '精确率', 'F1'],
                   y=[indep['dfa_acc'], indep['dfa_rec'], indep['dfa_prec'], indep['dfa_f1']],
                   text=[f'{v:.1%}' for v in
                         [indep['dfa_acc'], indep['dfa_rec'], indep['dfa_prec'], indep['dfa_f1']]],
                   textposition='outside'),
            go.Bar(name='二防 LLM', x=['准确率', '召回率', '精确率', 'F1'],
                   y=[indep['llm_acc'], indep['llm_rec'], indep['llm_prec'], indep['llm_f1']],
                   text=[f'{v:.1%}' for v in
                         [indep['llm_acc'], indep['llm_rec'], indep['llm_prec'], indep['llm_f1']]],
                   textposition='outside'),
        ])
        fig_comp.update_layout(
            title="DFA vs LLM 独立指标对比",
            yaxis=dict(range=[0, 1.1], tickformat='.0%'),
            barmode='group',
        )
        st.plotly_chart(fig_comp, width='stretch')

        # DFA / LLM 单独指标卡片
        cm1, cm2, cm3, cm4 = st.columns(4)
        cm1.metric("DFA 准确率", f"{indep['dfa_acc']:.1%}")
        cm2.metric("DFA 召回率", f"{indep['dfa_rec']:.1%}")
        cm3.metric("LLM 准确率", f"{indep['llm_acc']:.1%}")
        cm4.metric("LLM 召回率", f"{indep['llm_rec']:.1%}")

        # ========== 攻击策略维度分析 ==========
        if strategy_map:
            st.markdown("---")
            st.subheader("攻击策略维度分析")
            strat_df = compute_strategy_analysis(scanned)
            if not strat_df.empty:
                st.dataframe(strat_df, width='stretch', hide_index=True)
                fig_strat = go.Figure(data=[
                    go.Bar(name='正确拦截', x=strat_df['攻击策略'], y=strat_df['正确拦截'],
                           marker_color='#4caf50'),
                    go.Bar(name='漏报', x=strat_df['攻击策略'], y=strat_df['漏报'],
                           marker_color='#f44336'),
                ])
                fig_strat.update_layout(
                    title="各攻击策略检测效果",
                    barmode='stack',
                    yaxis=dict(title='样本数'),
                )
                st.plotly_chart(fig_strat, width='stretch')

        # ========== 防御管线漏斗图 ==========
        st.markdown("---")
        st.subheader("防御管线流程")
        funnel_fig = go.Figure(go.Funnel(
            y=['总样本', 'DFA 命中', 'LLM 命中', '最终拦截'],
            x=[funnel['total'], funnel['dfa_hit'], funnel['llm_hit'], funnel['final_hit']],
            textinfo="value+percent previous",
        ))
        funnel_fig.update_layout(title="双防拦截漏斗")
        st.plotly_chart(funnel_fig, width='stretch')

        # ========== 标签分布饼图 + 防火墙柱状图 ==========
        st.markdown("---")
        col_pie, col_bar = st.columns(2)
        with col_pie:
            fig1 = px.pie(
                names=['有毒', '无毒'],
                values=[int(df['true_label'].sum()), total - int(df['true_label'].sum())],
                title="测试集真实标签分布"
            )
            st.plotly_chart(fig1, width='stretch')
        with col_bar:
            fig2 = px.bar(
                x=['一防 DFA', '二防 LLM', '联合判定'],
                y=[funnel['dfa_hit'], funnel['llm_hit'], funnel['final_hit']],
                labels={'x': '防火墙', 'y': '命中数'},
                title="防火墙拦截数量对比",
                text_auto=True,
            )
            st.plotly_chart(fig2, width='stretch')

    else:
        st.info(f"共 {total} 条样本，均未检测。请先运行扫描。")

    # ========== Excel 导出 ==========
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='扫描结果')
    st.download_button("📥 导出 Excel", data=buf.getvalue(),
                       file_name=f"{dataset_id.replace('.jsonl', '') if dataset_id else 'scan'}_results.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    with st.expander("查看完整数据库记录"):
        st.dataframe(df)
