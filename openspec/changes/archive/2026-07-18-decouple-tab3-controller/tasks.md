## 1. 创建 core/analysis_controller.py

- [x] 1.1 实现 `load_and_prepare_data()`：筛选、类型转换、final_pred
- [x] 1.2 实现 `compute_confusion_metrics()`：TP/TN/FP/FN 及派生指标
- [x] 1.3 实现 `compute_independent_metrics()`：DFA 和 LLM 各自指标
- [x] 1.4 实现 `compute_strategy_analysis()`：攻击策略分组
- [x] 1.5 实现 `compute_funnel_data()`：双防拦截漏斗数据

## 2. 精简 views/tab3_analysis.py

- [x] 2.1 替换数据预处理逻辑为 `load_and_prepare_data()` 调用
- [x] 2.2 替换混淆矩阵指标计算为 `compute_confusion_metrics()` 调用
- [x] 2.3 替换双防对比指标为 `compute_independent_metrics()` 调用
- [x] 2.4 替换策略分析为 `compute_strategy_analysis()` 调用
- [x] 2.5 替换漏斗数据为 `compute_funnel_data()` 调用
- [x] 2.6 清理不再需要的 import

## 3. 验证

- [x] 3.1 运行语法检查
- [x] 3.2 确认 tab3_analysis.py 行数减少（277 → 206）
