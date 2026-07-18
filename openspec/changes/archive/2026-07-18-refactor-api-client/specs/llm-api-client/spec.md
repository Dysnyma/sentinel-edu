# LLM API 客户端

统一的 LLM API 客户端基类，标准化核心 / 的 LLM 调用流程。

## ADDED Requirements

### Requirement: 客户端封装
系统 SHALL 提供一个 `BaseLLMClient` 类，封装 OpenAI 兼容 API 的通用调用逻辑。

- **初始化**：接收 `api_key`、`base_url`、`model`，自动完成 URL 标准化（补全 `/v1` 路径前缀）并创建 `openai.OpenAI` 客户端实例。
- **call() 方法**：接受 `messages` 列表及可选的 `temperature`、`max_tokens`、`timeout` 参数，返回 API 响应的文本内容（已清理多余空白）。
- **call_and_parse() 方法**：在 `call()` 基础上增加 `json_repair` JSON 解析，返回 Python `dict`。

#### Scenario: URL 标准化
- **WHEN** 用户传入 `base_url = "https://api.example.com"`
- **THEN** 客户端自动拼接为 `"https://api.example.com/v1"`

#### Scenario: call() 正常流程
- **WHEN** 用户调用 `client.call(messages=[...], timeout=30)`
- **THEN** 返回 `choices[0].message.content` 的纯文本（已 strip）

#### Scenario: call_and_parse() 正常流程
- **WHEN** 用户调用 `client.call_and_parse(messages=[...])`
- **THEN** 返回 `json_repair.loads()` 解析后的 Python `dict`

### Requirement: 指数退避重试
系统 SHALL 在 API 调用遇到 `openai.APIError` 异常时自动重试最多 3 次。

- 退避策略：第 N 次重试前等待 `2^(N-1)` 秒（第 1 次重试前 1s，第 2 次 2s）。
- 3 次均失败后抛出 `ValueError`，异常消息包含 `model`、`base_url` 和最后一次异常的详细信息。

#### Scenario: 网络抖动后恢复
- **WHEN** 第 1 次请求因 `APITimeoutError` 失败，第 2 次请求成功
- **THEN** `call()` / `call_and_parse()` 正常返回结果，不抛出异常

#### Scenario: 持续失败
- **WHEN** 连续 3 次请求均因 `APIStatusError` 失败
- **THEN** 抛出 `ValueError`，消息中包含 `model`、`base_url` 和最后一次错误的 HTTP 状态码与响应体

### Requirement: 响应提取防御
系统 SHALL 在提取响应内容时兼容不同版本的 openai 库。

- 优先通过 `resp.choices[0].message.content` 属性访问。
- 若属性访问失败，尝试通过 `resp.model_dump()` 的字典形式提取。
- 若仍失败，抛出含响应对象类型和摘要的 `ValueError`。

#### Scenario: 新版 openai 库
- **WHEN** 响应对象支持属性访问
- **THEN** 通过 `resp.choices[0].message.content` 提取

#### Scenario: 旧版或兼容库
- **WHEN** 响应对象不支持属性访问
- **THEN** 通过 `resp.model_dump()['choices'][0]['message']['content']` 降级提取

#### Scenario: 完全无法提取
- **WHEN** 所有提取方式均失败
- **THEN** 抛出 `ValueError`，包含 `type(resp).__name__` 和 `str(resp)[:500]`
