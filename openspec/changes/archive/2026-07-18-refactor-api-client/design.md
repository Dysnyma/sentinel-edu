## Context

当前三个文件各自实现了独立的 LLM API 调用链条。以 `llm_scanner.py` 和 `poison_generator.py` 为例，两者都包含了以下重复代码段：

| 逻辑片段 | llm_scanner | poison_generator | text_correction |
|---|---|---|---|
| URL 标准化（`/v1` 补全） | ✅ | ✅ | ✅ |
| openai.OpenAI 初始化 | ✅ | ✅ | ✅ |
| 指数退避重试 3 次 | ✅ `APIStatusError/APITimeoutError/APIConnectionError` | ✅ `APIError`（基类） | ❌ 无重试 |
| 提取 `choices[0].message.content` | ✅ | ✅（含 fallback） | ✅ |
| Markdown 代码块清理 | ✅ | ✅ | ❌ |
| `json_repair.loads` 解析 | ✅ | ✅ | ❌（返回文本） |
| 异常上下文（model/base_url） | ✅ | ✅ | ❌ |

text_correction 完全没有重试，出错即抛；三个文件的错误消息格式也不一致。这些都在同一个项目、同一个 core/ 包下，高度的代码重复是明显的可重构信号。

### 设计目标

提取一个 `BaseLLMClient` 基类，让三个文件只关注自己独有的东西（Prompt 模板、返回值组合），不再关心网络请求细节。

## Goals / Non-Goals

**Goals:**
- 抽取公用的 LLM 请求流程为 `BaseLLMClient` 基类
- 为三个调用方提供一致的错误处理与上下文信息
- text_correction 获得重试能力（升级为 3 次指数退避）
- 保持所有对外函数签名不变（`llm_scan`、`generate_poison`、`correct_text`）

**Non-Goals:**
- 不改动 Prompt 模板本身
- 不改动任何业务层的返回值结构
- 不引入新的外部依赖
- 不引入异步或并发改动

## Decisions

### 1. 类设计：组合而非继承

- **选择**：`BaseLLMClient` 是一个工具类，三个函数各自实例化使用，而非让业务模块继承它。
- **理由**：三个模块是函数式模块（每个文件就是一组独立函数），改为 class 继承会引入不必要的 OOP 层级。一个轻量的工具类 + 每个函数内实例化使用，改动最小，易于测试。

### 2. API 方法粒度

```
BaseLLMClient.__init__(api_key, base_url, model)
    → 标准化 URL、初始化 openai 客户端

BaseLLMClient.call(messages, *, temperature=0.0, max_tokens=512, timeout=30) -> str
    → 带重试的 API 调用，返回 content 文本（已 strip、已清理 markdown 标记）

BaseLLMClient.call_and_parse(messages, *, temperature=0.0, max_tokens=512, timeout=30) -> dict
    → call() + json_repair.loads()，返回 dict
```

`call()` 用于 `correct_text`（返回纯文本），`call_and_parse()` 用于 `llm_scan` 和 `generate_poison`（返回 JSON）。

### 3. 重试策略

- **选择**：捕获 `openai.APIError`（基类，覆盖所有 API/网络异常），3 次重试，`2 ** attempt` 秒退避。
- **理由**：`poison_generator` 目前捕获 `APIError`（最宽），`llm_scanner` 捕获三个子类但遗漏了 `RateLimitError` 等（`APIStatusError` 不包含限流）。统一用 `APIError` 更安全且更简单。

### 4. 错误消息格式

- 统一格式：`{context}：model={model}, base_url={base_url}, 详情={detail}`
- 所有异常类型保持 `ValueError`（不改变上游 catch）

### 5. response 提取防御

- 当前 `poison_generator` 有 `model_dump()` fallback 逻辑处理不同 openai 库版本。BaseLLMClient 保留这一防御层。

## Risks / Trade-offs

- 【风险】`call_and_parse` 假设返回值是 JSON，如果 `correct_text` 误用会抛解析异常
  → **缓解**：`correct_text` 使用 `call()` 而非 `call_and_parse()`，天然规避。

- 【风险】重试改用 `APIError` 基类后，之前 `llm_scanner` 未捕获的异常类型（如 `RateLimitError` 也是 `APIError` 子类）现在也会被重试，行为变宽容
  → **接受**：这实际上是更合理的做法——所有网络/服务端错误都值得重试，旧行为反而是遗漏。

- 【风险】`_local_model` 移除后使用了 `@st.cache_resource`（上次修改），本次重构不涉及 asr.py，无冲突。
