## Context

`core/llm_client.py` 的 `_call_api()` 方法是所有 LLM API 调用的底层网络入口，当前重试逻辑存在两个问题：

1. **异常覆盖不足**：仅捕获 `openai.APIError`，但 `openai` SDK 底层使用 `httpx` 发送 HTTP 请求，网络超时、连接断开、DNS 失败时抛出的是 `httpx.ConnectError`、`httpx.ReadTimeout`、`httpx.HTTPError` 等，这些异常不继承 `openai.APIError`，因此不会触发重试。

2. **无差别重试**：所有异常一律重试 3 次，包括 401/403/404/400 等客户端错误，这些错误的根源（密钥无效、模型不存在、参数错误）不会因重试而改变。

## Goals / Non-Goals

**Goals：**
- 将网络层异常（httpx 系列、超时、连接错误）纳入重试范围
- 区分可重试与不可重试的错误，避免对 4xx 客户端错误做无效重试
- 保持指数退避逻辑和总重试次数（3 次）不变
- 异常信息更完整（携带 model、base_url、HTTP 状态码、响应体摘要）
- 对外接口 `call()` / `call_and_parse()` 完全不变

**Non-Goals：**
- 不改变重试次数或退避策略
- 不改变上层业务代码
- 不引入新的重试库（如 `tenacity`）
- 不修改 `call_and_parse` 的 JSON 解析逻辑

## Decisions

### 决策 1：捕获基类 `Exception` + 类型判断  vs  `httpx` 多异常捕获

| 方案 | 评价 |
|---|---|
| **异常元组捕获（选定）**：在 `except` 子句中列出 `(openai.APIError, httpx.HTTPError, TimeoutError, ConnectionError)` | 明确、可维护，易于理解和审查。配合 `openai.APIError` 的子类关系可覆盖所有已知场景 |
| 捕获 `Exception` 再判断 | 过于宽泛，可能吞噬意外错误（如 `KeyboardInterrupt` 虽不继承 `Exception`，但生产环境中的 `SystemExit`、`GeneratorExit` 等需要透传） |

**结论：** 使用异常元组，明确列出全部可重试的异常类型。

### 决策 2：HTTP 状态码分类方式

`openai.APIError` 的 `status_code` 属性标记了 HTTP 状态码。逻辑如下：

- **`status_code is None`** — 表示未到达 HTTP 层（如网络异常、DNS 失败），视为可重试
- **`status_code >= 500`** — 服务端错误，可重试
- **`status_code == 429`** — 限流（Too Many Requests），可重试
- **`400 <= status_code < 500`** — 客户端错误（含 401/403/404/400 等），**不可重试**，立即抛出

对于非 `openai.APIError` 的异常（如纯 `httpx.HTTPError`），没有 `status_code` 属性，统一视为可重试的网络层错误。

### 决策 3：错误信息增强

当前错误信息仅包含 `last_exc` 的字符串表示。修改后在 `ValueError` 中统一附加 `model`、`base_url`、HTTP 状态码、响应体前 500 字符，使错误信息在日志中可直接定位问题。

### 决策 4：`openai.APIError` 子类关系验证

`openai` SDK 的异常继承链（简化）：
```
APIError (has status_code, response, body, request attributes)
├── APIConnectionError       # 网络连接失败（httpx 层）
├── RateLimitError           # 429 限流
├── AuthenticationError      # 401
├── PermissionDeniedError    # 403
├── NotFoundError            # 404
├── BadRequestError          # 400
├── InternalServerError      # 500
└── UnprocessableEntityError # 422
```

注意到 `APIConnectionError`、`RateLimitError`、`InternalServerError` 都是 `APIError` 的子类，已被现有代码捕获。但新增的 `httpx` 层异常（如 `httpx.ConnectError` — 当底层 TCP 连接失败时抛出）不在这个继承树中——这正是本次修复的核心场景之一。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|---|---|
| `httpx` 版本更新引入新的网络异常类型（如 `PoolTimeout`） | 捕获父类 `httpx.HTTPError` 即可覆盖其全部子类 |
| 429 限流重试可能导致并发请求堆积 | 保持指数退避（最大 4s），3 次总等待约 7s，影响可控 |
| 网络异常重试后请求发送至负载均衡的不同节点，最终成功 | 这正是重试的预期效果，无需缓解 |
| 错误信息泄露 API 密钥 | 响应体仅截取前 500 字符且不包含请求头，API key 不会出现在响应体中 |
