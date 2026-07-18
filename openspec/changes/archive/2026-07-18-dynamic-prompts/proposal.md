## Why

三个核心大模型提示词（SCAN_PROMPT、POISON_PROMPT、CORRECT_PROMPT）当前硬编码在 `core/llm_scanner.py`、`core/poison_generator.py` 和 `core/text_correction.py` 中。每次调优提示词都需要修改代码、重启应用，无法快速迭代。对于不同的大模型（如 deepseek、qwen、gpt-4o-mini 等），理想的提示词结构和措辞可能不同，硬编码方式使得多模型适配困难。

## What Changes

1. **新增 `data/prompts.json`**：持久化存储三个核心提示词。
2. **新增 prompts 管理函数**：在 `core/config.py` 中添加 `load_prompts()` 和 `save_prompts()`。
3. **重构三个业务模块**：`llm_scanner.py`、`poison_generator.py`、`text_correction.py` 从 `core/config` 读取提示词而非硬编码常量。
4. **UI 热编辑**：在 `app.py` 侧边栏（高级配置区域）添加 `st.text_area` 组件，允许用户运行时编辑三个提示词并即时生效。

## Capabilities

### New Capabilities
- `prompt-management`: 大模型提示词的持久化存储与动态加载机制
- `prompt-editor-ui`: 运行时提示词编辑与热重载界面

### Modified Capabilities
无。不改变已有能力的需求层行为。

## Impact

- `data/prompts.json`：新增文件（初始时写入默认提示词）
- `core/config.py`：新增 `load_prompts()` 和 `save_prompts()` 函数
- `core/llm_scanner.py`：`SCAN_PROMPT` 改为从配置读取（保留默认值兜底）
- `core/poison_generator.py`：`POISON_PROMPT` 改为从配置读取
- `core/text_correction.py`：`CORRECT_PROMPT` 改为从配置读取
- `app.py`：侧边栏增加提示词编辑器展开区域
