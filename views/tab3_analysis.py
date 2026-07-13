"""Tab 3: 可视化分析 — 混淆矩阵指标 + 详细图表"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io
import os

from core.database import get_all_results, get_results_by_dataset, get_dataset_ids
from core.utils import load_jsonl


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
    df = get_all_results()
    if df.empty:
        st.warning("暂无检测数据，请先运行检测")
        return

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
    df['dfa_time'] = pd.to_numeric(df['dfa_time'], errors='coerce').fillna(0)
    df['llm_time'] = pd.to_numeric(df['llm_time'], errors='coerce').fillna(0)

    df['final_pred'] = ((df['dfa_pred'] == 1) | (df['llm_pred'] == 1)).astype(int)

    # 加载策略映射
    strategy_map = _load_strategy_map(dataset_id) if dataset_id else {}
    if strategy_map:
        df['attack_strategy'] = df['text_id'].map(strategy_map).fillna('未知')

    # 区分已扫描和未扫描样本
    scanned = df[(df['dfa_pred'] != -1) | (df['llm_pred'] != -1)]
    unscanned = len(df) - len(scanned)
    total = len(df)

    # ========== 核心指标 ==========
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

        # 时间统计
        dfa_scanned = scanned[scanned['dfa_pred'] != -1]
        llm_scanned = scanned[scanned['llm_pred'] != -1]
        avg_dfa_time = dfa_scanned['dfa_time'].mean() if len(dfa_scanned) > 0 else 0
        avg_llm_time = llm_scanned['llm_time'].mean() if len(llm_scanned) > 0 else 0
        total_time = scanned['dfa_time'].sum() + scanned['llm_time'].sum()

        st.subheader("核心指标")
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

        # 耗时指标
        st.subheader("检测耗时")
        tc1, tc2, tc3, tc4 = st.columns(4)
        tc1.metric("DFA 平均耗时", f"{avg_dfa_time:.3f}s")
        tc2.metric("LLM 平均耗时", f"{avg_llm_time:.1f}s")
        tc3.metric("总耗时", f"{total_time:.1f}s")
        tc4.metric("已检测", f"{len(scanned)} 条")

        # ========== 混淆矩阵热力图 ==========
        st.markdown("---")
        st.subheader("混淆矩阵")
        cm = [[tn, fp], [fn, tp]]
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

        def calc_metrics(true_labels, preds):
            """计算准确率、召回率、精确率、F1"""
            _tp = sum(1 for t, p in zip(true_labels, preds) if t == 1 and p == 1)
            _tn = sum(1 for t, p in zip(true_labels, preds) if t == 0 and p == 0)
            _fp = sum(1 for t, p in zip(true_labels, preds) if t == 0 and p == 1)
            _fn = sum(1 for t, p in zip(true_labels, preds) if t == 1 and p == 0)
            _acc = (_tp + _tn) / len(true_labels) if true_labels else 0
            _rec = _tp / (_tp + _fn) if (_tp + _fn) > 0 else 0
            _prec = _tp / (_tp + _fp) if (_tp + _fp) > 0 else 0
            _f1 = 2 * _prec * _rec / (_prec + _rec) if (_prec + _rec) > 0 else 0
            return _acc, _rec, _prec, _f1

        dfa_valid = scanned[scanned['dfa_pred'] != -1]
        llm_valid = scanned[scanned['llm_pred'] != -1]

        dfa_acc, dfa_rec, dfa_prec, dfa_f1 = calc_metrics(
            dfa_valid['true_label'].tolist(), dfa_valid['dfa_pred'].tolist()) if len(dfa_valid) > 0 else (0, 0, 0, 0)
        llm_acc, llm_rec, llm_prec, llm_f1 = calc_metrics(
            llm_valid['true_label'].tolist(), llm_valid['llm_pred'].tolist()) if len(llm_valid) > 0 else (0, 0, 0, 0)

        fig_comp = go.Figure(data=[
            go.Bar(name='一防 DFA', x=['准确率', '召回率', '精确率', 'F1'],
                   y=[dfa_acc, dfa_rec, dfa_prec, dfa_f1],
                   text=[f'{v:.1%}' for v in [dfa_acc, dfa_rec, dfa_prec, dfa_f1]],
                   textposition='outside'),
            go.Bar(name='二防 LLM', x=['准确率', '召回率', '精确率', 'F1'],
                   y=[llm_acc, llm_rec, llm_prec, llm_f1],
                   text=[f'{v:.1%}' for v in [llm_acc, llm_rec, llm_prec, llm_f1]],
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
        cm1.metric("DFA 准确率", f"{dfa_acc:.1%}")
        cm2.metric("DFA 召回率", f"{dfa_rec:.1%}")
        cm3.metric("LLM 准确率", f"{llm_acc:.1%}")
        cm4.metric("LLM 召回率", f"{llm_rec:.1%}")

        # ========== 攻击策略维度分析 ==========
        if strategy_map:
            st.markdown("---")
            st.subheader("攻击策略维度分析")
            toxic_df = scanned[scanned['true_label'] == 1].copy()
            if not toxic_df.empty and 'attack_strategy' in toxic_df.columns:
                strategies = toxic_df['attack_strategy'].unique()
                strat_records = []
                for s in strategies:
                    subset = toxic_df[toxic_df['attack_strategy'] == s]
                    s_tp = len(subset[subset['final_pred'] == 1])
                    s_fn = len(subset[subset['final_pred'] == 0])
                    s_total = len(subset)
                    s_recall = s_tp / s_total if s_total > 0 else 0
                    s_miss = s_fn / s_total if s_total > 0 else 0
                    strat_records.append({
                        '攻击策略': s if s else '无毒',
                        '有毒样本数': s_total,
                        '正确拦截': s_tp,
                        '漏报': s_fn,
                        '召回率': f'{s_recall:.1%}',
                        '漏报率': f'{s_miss:.1%}',
                    })
                strat_df = pd.DataFrame(strat_records)
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
        dfa_hit = int((scanned['dfa_pred'] == 1).sum())
        llm_hit = int((scanned['llm_pred'] == 1).sum())
        final_hit = int((scanned['final_pred'] == 1).sum())

        funnel_fig = go.Figure(go.Funnel(
            y=['总样本', 'DFA 命中', 'LLM 命中', '最终拦截'],
            x=[total, dfa_hit, llm_hit, final_hit],
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
                y=[dfa_hit, llm_hit, final_hit],
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
