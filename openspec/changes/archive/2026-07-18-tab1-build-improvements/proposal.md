## Why

Tab1（测试集构建）存在多个用户体验问题和功能缺口：切换 Whisper 模型后转写结果显示空窗口或旧结果；有毒样本对比使用左右双栏导致可读性差；文本纠错后没有对比视图，用户无法直观看到改了什么；三个核心数据集（原始转写、纠错后无毒、投毒后有毒）缺乏清晰的命名管理。

## What Changes

1. **修复模型切换显示 Bug**：当用户切换本地 Whisper 模型时，清除缓存的 `_last_file_id` 和 `asr_transcript`，强制重新转写并显示新结果。
2. **有毒样本对比改为上下布局**：将 `st.columns(2)` 左右双栏改为上下排列，充分利用垂直空间。
3. **文本纠错对比视图**：纠错完成后显示一个双栏对比区域（原文 vs 纠错后），差异文本高亮。
4. **AI 自动命名三个数据集**：在步骤 1（ASR 转写 → 原始数据集）、步骤 3（生成无毒 JSONL）、步骤 4（投毒完成）三个阶段，分别调用 LLM 为数据集生成标题并持久化保存。

## Capabilities

### New Capabilities
- `asr-model-switch-fix`: 切换 ASR 模型时自动清空缓存并重新转写
- `text-correction-diff`: 纠错前后文本对比视图，差异高亮
- `dataset-auto-naming`: 自动为数据集生成 LLM 标题并分阶段保存

### Modified Capabilities
无。本次不改变已有能力的需求层行为。

## Impact

- `views/tab1_build.py`：主要修改文件，涉及 4 项变更
- `core/utils.py`：可能小幅调整 `_generate_dataset_title` 以支持更多调用方式
- 无外部依赖变更
