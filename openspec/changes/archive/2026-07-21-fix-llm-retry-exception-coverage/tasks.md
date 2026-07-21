## 1. 重构 `_call_api()` 异常处理与重试逻辑

- [x] 1.1 扩 `except` 子句：在 `openai.APIError` 基础上增加 `httpx.HTTPError`、`TimeoutError`、`ConnectionError`
- [x] 1.2 添加可重试/不可重试判断：`status_code in (None, 429)` 或 `status_code >= 500` 可重试；`400 <= status_code < 500` 不可重试，直接抛出
- [x] 1.3 增强异常信息：在 `ValueError` 中统一输出 `model`、`base_url`、HTTP 状态码、响应体前 500 字符

## 2. 验证

- [x] 2.1 运行现有单元测试，确认全部通过
- [x] 2.2 人工审查确认异常分类逻辑覆盖所有 `openai.APIError` 子类场景
