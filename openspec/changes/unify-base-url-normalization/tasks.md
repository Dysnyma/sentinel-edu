## 1. 新增统一工具函数

- [x] 1.1 在 `core/config.py` 中新增 `normalize_base_url(url: str) -> str` 函数

## 2. 替换三处调用点

- [x] 2.1 `core/llm_client.py`：`__init__` 中改用 `normalize_base_url(base_url)` 覆盖原 `base_url` 参数
- [x] 2.2 `views/helpers.py`：`check_api_connection` 中改用 `normalize_base_url(base_url)` 返回新值
- [x] 2.3 `app.py`：移除内联标准化，改用 `normalize_base_url`

## 3. 验证

- [x] 3.1 运行现有单元测试，确认全部通过
- [x] 3.2 确认三处调用点不再包含内联 `strip().rstrip('/')` + `endswith('/v1')` 模式
