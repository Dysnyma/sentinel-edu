## Why

当前 `core/llm_client.py` 中 `_call_api` 方法仅捕获 `openai.APIError` 系列异常进行重试，实际生产环境中常见的网络超时、连接断开、DNS 解析失败等 `httpx` 层异常（如 `ConnectError`、`ReadTimeout`）不属于该子类，不会触发重试，偶发的网络波动直接导致请求失败。同时，所有错误（包括 401 密钥错误、404 模型不存在等本质不可重试的客户端错误）一律重试 3 次，既无谓拉长失败耗时，又掩盖了真正的问题根源。

## What Changes

1. **`core/llm_client.py` — `_call_api()` 方法**：
   - 扩大异常捕获范围：增加对 `httpx.HTTPError`、`TimeoutError`、`ConnectionError` 等网络层异常的捕获，使其纳入重试流程
   - 区分可重试与不可重试错误：
     - **可重试**：5xx 服务端错误、网络异常 (`httpx.HTTPError`)、超时 (`TimeoutError`)、限流 (HTTP 429)
     - **不可重试**：4xx 客户端错误（401/403/404/400 等）直接抛出异常，不做无效重试
   - 异常报错信息保留完整的状态码与响应体摘要，便于排查

2. **不变项**：
   - 外部调用接口（`call()`、`call_and_parse()`）不变
   - 指数退避逻辑不变（`2 ** attempt`）
   - 总重试次数仍为 3 次

## Capabilities

### New Capabilities

（无新增能力——本次变更为修复已有功能中异常覆盖不全的问题。）

### Modified Capabilities

（无需修改已有 spec——本次不涉及需求层的行为变更，仅为实现层面的重试策略优化。）

## Impact

- **代码**：仅修改 `core/llm_client.py` 中 `_call_api()` 方法（约 30 行）
- **API**：无变化（`call()`、`call_and_parse()` 签名与行为不变）
- **依赖**：无新增（`httpx` 已是 `openai` SDK 的传递依赖）
- **测试**：现有单元测试应全部通过；建议新增测试覆盖不同异常类型及状态码的重试行为
- **风险**：低——改动集中在单一方法，已明确定义可重试/不可重试的边界
