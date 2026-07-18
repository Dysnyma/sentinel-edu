## 1. 修复模型切换 Bug

- [x] 1.1 在 `render_tab1` 顶部检测模型变化：对比 `_last_model` 与当前 `local_whisper_model`，变化时清除 `_last_file_id` 和 `asr_transcript`
- [x] 1.2 确保模型切换后文本区域显示占位提示而非空窗口

## 2. 有毒样本对比改为上下布局

- [x] 2.1 将 `st.columns(2)` 左右排列改为上下排列，用 `st.container` + `st.markdown("---")` 分隔各样本
- [x] 2.2 保持高亮逻辑不变

## 3. 文本纠错对比视图

- [x] 3.1 实现 `_highlight_diff(original, corrected)` 函数：用 `difflib.SequenceMatcher` 找出差异并生成高亮 HTML
- [x] 3.2 纠错完成后，在进度条下方添加可折叠的对比区域，每条原文+纠错后双栏对比

## 4. AI 自动命名数据集

- [x] 4.1 将 `_generate_dataset_title` 中的直接 openai 调用改为使用 `BaseLLMClient.call()`
- [x] 4.2 ASR 完成后自动保存原始数据集（含 LLM 命名）
- [x] 4.3 生成无毒 JSONL 后自动保存纠错后数据集（含 LLM 命名）

## 5. 验证

- [x] 5.1 语法检查所有修改文件
- [x] 5.2 确认模型切换后界面不显示空窗口或旧结果
