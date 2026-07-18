## Context

Tab1 是测试集构建的主界面，包含 ASR 转写 → 纠错 → 生成无毒 JSONL → 投毒 → 保存的完整流水线。当前代码在多次迭代中累积了一些 UX 问题和功能缺口。

## Goals / Non-Goals

**Goals:**
- 切换 Whisper 模型后不再显示空窗口或旧结果
- 有毒样本对比改为上下布局，充分利用屏幕高度
- 纠错后提供原文/纠错后双栏对比视图
- 三个数据集（原始转录、无毒、有毒）各自有明确的 AI 命名

**Non-Goals:**
- 不改变 ASR 引擎或纠错/投毒的核心算法
- 不改动数据流或文件格式

## Decisions

### 1. 模型切换修复

**问题根因**：`_last_file_id` 缓存阻止了模型切换后的重新转写。Streamlit 重渲染时，`local_whisper_model` 参数变化但 `file_id` 没变，导致处理块被跳过。

**方案**：当 `local_whisper_model` 变化且已有 `asr_transcript` 时，清除 `_last_file_id` 和 `asr_transcript`，触发下次渲染时重新转写。

```python
# 在 render_tab1 顶部添加
if use_local_whisper and st.session_state.get('_last_model') != local_whisper_model:
    st.session_state.pop('_last_file_id', None)
    st.session_state.pop('asr_transcript', None)
    st.session_state['_last_model'] = local_whisper_model
```

### 2. 有毒样本对比布局

**当前**：`st.columns(2)` 左右排列，在窄屏或长文本下可读性差。

**改为**：上下排列，先用 `st.markdown` 显示原文，再用 `st.markdown` + `highlight_toxic` 显示有毒文本，中间用分割线。可用 `st.container` 包裹每个样本卡片。

### 3. 文本纠错对比视图

**方案**：纠错完成后（`corrected_texts` 写入 session_state 后），展示一个可折叠的对比区域。对每对 (原文, 纠错后)，使用双栏 `st.columns(2)` 展示——左侧原文，右侧纠错后文本。

**差异高亮**：使用 Python 标准库 `difflib.HtmlDiff` 或自定义简单的字符级 diff（使用 `difflib.SequenceMatcher` 找出增删位置，包裹 `<span style="background: #ffcccc">` / `<span style="background: #ccffcc">` 标记）。

### 4. AI 自动命名数据集

**当前**：`_generate_dataset_title` 已存在，但仅用于最终混合集，且使用原始 openai 调用。

**改进**：
- 步骤 1（ASR 完成后）：自动调用标题生成，保存为"原始数据集"
- 步骤 3（生成无毒 JSONL）：自动调用标题生成，保存为"纠错后无毒数据集"
- 步骤 4（投毒完成后）：已有逻辑，继续使用
- 将 `_generate_dataset_title` 迁移为使用 `BaseLLMClient.call()`（对齐前面重构引入的基类）

## Risks / Trade-offs

- 【风险】清除 `_last_file_id` 后用户需要重新上传文件 → **接受**，这是模型切换的预期行为
- 【风险】difflib 高亮在处理长文本时可能性能不佳 → 限制每条约 500 字符以内进行 diff
- 【风险】每次 ASR 完成都调用 LLM 命名会增加 API 调用量 → 调用一次仅需 ~100 tokens，成本可忽略
