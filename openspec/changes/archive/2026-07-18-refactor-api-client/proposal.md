## Why

`core/llm_scanner.py`、`core/poison_generator.py`、`core/text_correction.py` 三个文件中存在大量重复的 LLM API 调用代码：URL 标准化、OpenAI 客户端初始化、指数退避重试、响应内容提取、Markdown 代码块清理、`json_repair` 解析等逻辑在三个文件中反复出现，每一份都有细微差异（如重试捕获的异常类型不同、错误消息格式不统一、text_correction 甚至没有重试）。这不仅增加了维护成本，也使得新接入一个 LLM 调用场景时必须复制粘贴整套样板代码。

## What Changes

1. **新增 `core/llm_client.py`**：提取一个 `BaseLLMClient` 基类，封装以下通用能力：
   - URL 标准化（`/v1` 补全）
   - OpenAI 客户端初始化与管理
   - 指数退避重试（3 次，可配置）
   - 响应提取（`choices[0].message.content`）
   - Markdown 代码块清理
   - `json_repair` JSON 解析与异常上下文包装
2. **重构三个现有模块**：`llm_scanner.py`、`poison_generator.py`、`text_correction.py` 通过 `BaseLLMClient` 消除重复，各模块仅保留自身独特的 Prompt 逻辑与业务返回值处理。
3. **行为等价**：所有重构不改变外部函数签名、返回值类型或可观测行为，**不是 BREAKING change**。

## Capabilities

### New Capabilities
- `llm-api-client`: 统一的 LLM API 客户端基类，提供标准化的请求、重试、解析能力

### Modified Capabilities

无。本次是纯内部重构，不改变需求层面的行为。

## Impact

- `core/llm_client.py`：新增文件，约 80-100 行
- `core/llm_scanner.py`：删除约 70 行重复代码（API 调用、重试、解析），保留 Prompt 定义与业务逻辑
- `core/poison_generator.py`：删除约 80 行重复代码，保留 Prompt 定义与业务逻辑
- `core/text_correction.py`：删除约 20 行重复代码，获得重试能力（之前没有重试）
- 无新增外部依赖（`openai`、`json_repair` 已是现有依赖）
