# AI 自动命名数据集

## ADDED Requirements

### Requirement: 三阶段自动命名
系统 SHALL 在测试集构建的三个阶段分别调用 LLM 为数据集生成标题并保存。

- **阶段 1（ASR 完成后）**：原始转录文本 → 作为"原始数据集"保存，LLM 根据文本内容生成标题
- **阶段 2（纠错/无毒 JSONL 生成）**：纠错后的无毒文本 → 作为"纠错后数据集"保存，LLM 生成标题
- **阶段 3（投毒完成）**：已有逻辑继续使用

每个数据集保存到 `data/datasets/` 目录，包含 .jsonl 和 .meta.json 元数据文件。

#### Scenario: ASR 完成后自动保存原始数据集
- **WHEN** ASR 转写完成，`asr_transcript` 写入 session_state
- **THEN** 系统调用 LLM 根据转录文本生成标题
- **THEN** 将转录文本按句子分割后保存为 `data/datasets/{timestamp}_{title}.jsonl`
- **THEN** 同步写入 `{same}.meta.json`，包含 `title`、`total`、`toxic_count=0`

#### Scenario: 无毒 JSONL 生成后自动保存
- **WHEN** 用户点击"生成无毒 JSONL"按钮并成功生成
- **THEN** 保存为独立数据集，标题包含"纠错后"或"clean"标识

#### Scenario: 投毒完成后保存
- **WHEN** 投毒完成，混合集 `final_test_mixed.jsonl` 生成
- **THEN** 保存最终混合数据集（已有逻辑，保持不变）
