## Context

`views/tab3_analysis.py`（278 行）是当前代码库中最后一个混合 UI 与业务逻辑的视图文件。与重构前的 tab1/tab2 类似，其职责混合情况如下：

| 职责 | 代码位置 | 目标 |
|---|---|---|
| 从 DB 加载 DataFrame | `render_tab3()` 开头 | → controller |
| 数据类型强制转换 | 内联 | → controller |
| 计算 final_pred | 内联 | → controller |
| 加载策略映射 | `_load_strategy_map()` | → controller |
| TP/TN/FP/FN 计算 | 内联 | → controller |
| 准确率/召回率/精确率/F1 | 内联 | → controller |
| FNR/FPR/时间统计 | 内联 | → controller |
| calc_metrics 嵌套函数 | 内联定义 | → controller |
| DFA/LLM 独立指标聚合 | 内联 | → controller |
| 攻击策略分组分析 | 内联 | → controller |
| 漏斗/条形图数据 | 内联 | → controller |
| 渲染图表 | plotly_chart/st.metric | 保留 |
| Excel 导出 | 内联 | 保留 |

## Goals / Non-Goals

**Goals:**
- `tab3_analysis.py` 中不包含任何 Pandas 指标计算逻辑
- 所有数据计算函数以"接受 DataFrame → 返回 dict/DataFrame"形式暴露
- 与前面三个 controller 一样不依赖 `st.*`

**Non-Goals:**
- 不改动 Plotly 图表配置或展示布局
- 不改动指标计算公式（TP/TN 等语义不变）

## Decisions

### 1. 提取的函数

```
core/analysis_controller.py
├── load_and_prepare_data(df, dataset_id, current_ids) -> DataFrame
│     从 DB 加载 → 筛选 → 类型转换 → final_pred 计算 → 策略映射
│
├── compute_confusion_metrics(scanned) -> dict
│     TP/TN/FP/FN/准确率/召回率/精确率/F1/FNR/FPR/时间统计
│
├── compute_independent_metrics(scanned) -> dict
│     DFA 和 LLM 各自的准确率/召回率/精确率/F1
│
├── compute_strategy_analysis(scanned) -> DataFrame
│     按攻击策略分组统计拦截/漏报
│
└── compute_funnel_data(scanned, total) -> dict
     总样本/DFA 命中/LLM 命中/最终拦截
```

### 2. 返回结构

每个函数返回简单的 dict 或 DataFrame，UI 层直接取值渲染：

```python
metrics = compute_confusion_metrics(scanned)
# {
#   "tp": 10, "tn": 50, "fp": 3, "fn": 2,
#   "accuracy": 0.92, "recall": 0.83, ...
#   "avg_dfa_time": 0.5, "avg_llm_time": 3.2, "total_time": 120
# }
```

### 3. 数据准备分离

数据加载和预处理（筛选、类型转换、final_pred）是独立于指标计算的步骤，单独封装。UI 层只需要调用 `load_and_prepare_data` 拿到干净的 DataFrame，然后依次调用各计算函数即可。

## Risks / Trade-offs

- 【风险】`load_and_prepare_data` 内部依赖 st.session_state → 这个函数必须留在 UI 层，或者在 controller 中通过参数传入 dataset_id/current_ids
  → **决策**：controller 函数通过参数接收所有数据，不接触 session_state
