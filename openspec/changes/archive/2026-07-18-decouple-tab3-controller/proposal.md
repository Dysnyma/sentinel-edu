## Why

经过 BaseLLMClient、build_controller、detect_controller 三轮重构后，core/ 层已覆盖 API 调用和 Tab1/Tab2 的业务逻辑。Tab3（可视化分析）是最后一个混合 UI 与计算逻辑的视图文件。

`views/tab3_analysis.py`（278 行）中，混淆矩阵指标计算、双防独立指标聚合、攻击策略维度分析等 Pandas 数据处理逻辑与 Plotly 图表渲染、Streamlit metric 展示交织在一起。将计算逻辑提取到 controller 后，Tab3 就只剩图表调用和数据展示，完成全站的 MVC 解耦。

## What Changes

1. **新建 `core/analysis_controller.py`**：提取 tab3_analysis.py 中所有 Pandas 数据处理和指标计算逻辑。
2. **精简 `views/tab3_analysis.py`**：仅保留 `st.xxx` 渲染和 `plotly_chart` 调用，所有数据来自 controller。
3. **保持行为等价**：不改变任何图表或指标的展示结果。

## Capabilities

### New Capabilities
- `analysis-controller`: 可视化分析控制层，提供混淆矩阵指标、双防对比、策略维度分析等纯计算函数

### Modified Capabilities
无。

## Impact

- `core/analysis_controller.py`：新增文件，约 100-120 行
- `views/tab3_analysis.py`：从 278 行缩减至约 160 行（仅图表和展示）
- 无外部依赖变更
