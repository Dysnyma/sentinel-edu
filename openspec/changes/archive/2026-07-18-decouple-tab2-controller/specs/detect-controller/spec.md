# 安全检测控制器

## ADDED Requirements

### Requirement: DB 记录初始化
系统 SHALL 提供一个函数，为新加载的数据集样本批量创建初始数据库记录，避免覆盖已有检测结果。

- 输入：样本列表（list[dict]）、数据集 ID
- 输出：新增的记录条数（int）
- 内部自动跳过已存在于数据库的 text_id

#### Scenario: 首次加载数据集
- **WHEN** 传入新数据集的 20 条样本
- **THEN** 在数据库中为每条样本创建初始记录（dfa_pred=-1, llm_pred=-1）
- **THEN** 返回 20

#### Scenario: 部分样本已存在
- **WHEN** 传入含 5 条已有记录的 20 条样本
- **THEN** 仅创建 15 条新记录
- **THEN** 返回 15

### Requirement: DFA 全量扫描
系统 SHALL 提供一个函数，对数据集逐条执行 DFA 扫描并将结果写入数据库。

- 输入：样本列表、数据集 ID、可选的进度回调
- 输出：dict[text_id, (dfa_hit, dfa_words)]
- 内部逐条调用 DFAScanner，同步写库

#### Scenario: DFA 扫描 20 条
- **WHEN** 传入 20 条样本
- **THEN** 逐条执行 DFA 扫描，进度回调触发 20 次
- **THEN** 返回包含 20 个 text_id 的 dict

### Requirement: LLM 并发扫描
系统 SHALL 提供一个函数，对一批候选文本并发执行 LLM 扫描并将结果写入数据库。

- 输入：候选列表（(rec, dfa_words) 元组）、API 参数、并发数、数据集 ID、进度回调
- 输出：每条 LLM 响应的结果列表
- 底层使用 `core/utils.py` 中与 UI 无关的通用并发调度函数

#### Scenario: 并发 LLM 扫描
- **WHEN** 传入 20 条候选文本，并发数 6
- **THEN** 使用 ThreadPoolExecutor 并发执行，每条结果写入数据库

### Requirement: 单文本检测
系统 SHALL 提供一个函数，对单条文本执行 DFA + LLM 扫描，返回统一的结果字典。

- 输入：文本内容、API 参数
- 输出：包含 dfa_hit、dfa_words、llm_pred、llm_spans、llm_reason 的 dict
- DFA 扫描始终执行，LLM 仅在 API 可用时执行

#### Scenario: 直接输入文本检测
- **WHEN** 调用单文本检测，API 可用
- **THEN** 先执行 DFA 扫描，再执行 LLM 扫描（携带 DFA 命中词作为线索）
- **THEN** 返回包含双防结果的 dict
