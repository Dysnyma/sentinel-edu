# 可视化分析控制器

## ADDED Requirements

### Requirement: 数据预处理
系统 SHALL 提供一个函数，对原始检测结果 DataFrame 执行标准化预处理。

- 输入：DataFrame、筛选条件（dataset_id/current_ids）
- 输出：预处理后的 DataFrame（含 final_pred 列、数值类型已转换）
- 将 `dfa_pred`、`llm_pred`、`true_label` 强制转为 int（-1 表示未检测）
- 计算 `final_pred = (dfa_pred == 1 OR llm_pred == 1)`
- 加载策略映射 `text_id → attack_strategy`

#### Scenario: 含未检测样本
- **WHEN** DataFrame 中包含 `dfa_pred = -1` 的行
- **THEN** 这些行被纳入总样本但排除在"已扫描"范围外
- **THEN** `final_pred` 按联合判定规则计算

### Requirement: 混淆矩阵指标
系统 SHALL 提供一个函数，从已扫描样本计算混淆矩阵核心指标。

- 输入：已扫描样本的 DataFrame
- 输出：包含 tp/tn/fp/fn、accuracy、recall、precision、f1、fnr、fpr、avg_dfa_time、avg_llm_time、total_time 的 dict

#### Scenario: 全部正确
- **WHEN** 所有已扫描样本预测值与真实标签一致
- **THEN** fp=0, fn=0, accuracy=1.0, recall=1.0

#### Scenario: 部分错误
- **WHEN** 存在误报和漏报
- **THEN** accuracy < 1.0, 各项指标正确反映分类质量

### Requirement: 双防独立指标
系统 SHALL 提供一个函数，分别计算 DFA 和 LLM 的独立指标。

- 输入：已扫描样本的 DataFrame
- 输出：包含 dfa_acc/dfa_rec/dfa_prec/dfa_f1 和 llm_acc/llm_rec/llm_prec/llm_f1 的 dict
- 排除各自未检测的行

### Requirement: 策略维度分析
系统 SHALL 提供一个函数，按攻击策略分组统计拦截效果。

- 输入：已扫描样本的 DataFrame
- 输出：包含攻击策略、有毒样本数、正确拦截、漏报、召回率的 DataFrame
- 仅在数据中包含 `attack_strategy` 列时执行
