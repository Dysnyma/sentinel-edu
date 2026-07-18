# 单元测试框架

## ADDED Requirements

### Requirement: pytest 环境
系统 SHALL 提供可执行的 pytest 测试环境。

- 通过 `python -m pytest tests/ -v` 一键运行所有测试。
- `requirements-dev.txt` 中包含 `pytest>=7.0` 和 `pytest-mock>=3.0`。
- 测试与生产依赖分离，生产环境无需安装测试工具。

### Requirement: BaseLLMClient 测试
系统 SHALL 提供对 `core/llm_client.BaseLLMClient` 的完整单元测试。

- 使用 mock 替代真实的 OpenAI API 调用。
- 覆盖指数退避重试：连续失败 N 次后第 N+1 次成功。
- 覆盖 3 次均失败时的异常抛出。
- 覆盖 `_extract_content` 的正常提取、model_dump 降级、None 响应。
- 覆盖 `_clean_markdown_json_markers` 的代码块清理。
- 覆盖 `call_and_parse` 的 JSON 解析和类型检查（返回非 dict 时抛异常）。

#### Scenario: 重试第 2 次成功
- **WHEN** mock 的前 2 次调用抛出 `APITimeoutError`，第 3 次返回正常响应
- **THEN** `call()` 正常返回文本，`call_count == 3`

#### Scenario: 3 次全部失败
- **WHEN** mock 的 3 次调用均抛出 API 异常
- **THEN** `call()` 抛出 `ValueError`，消息中包含 model 和 base_url

#### Scenario: call_and_parse 收到字符串型 JSON
- **WHEN** API 返回 `"plain string"`（合法的 JSON 字符串，非对象）
- **THEN** `call_and_parse()` 抛出 `ValueError`，提示"非对象 JSON"

### Requirement: Controller 层测试
系统 SHALL 提供对 controller 层纯函数的基础测试。

- `run_concurrently`：测试正常执行、异常收集、进度回调触发次数。
- `_split_sentences`：测试中文标点分割。
- `_highlight_diff`：测试差异高亮 HTML 输出（无差异、增删改）。
- Controller 函数中依赖 LLM/DB 的部分使用 mock 隔离。

#### Scenario: run_concurrently 正常执行
- **WHEN** 提交 3 个快速返回的任务
- **THEN** 返回 3 个结果，顺序与输入一致

#### Scenario: run_concurrently 收集异常
- **WHEN** 3 个任务中第 2 个抛出异常
- **THEN** 返回列表第 2 个位置为 Exception 实例
