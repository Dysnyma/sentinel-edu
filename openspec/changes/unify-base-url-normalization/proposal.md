## Why

当前 Base URL 补全 `/v1` 后缀的标准化逻辑在三处独立重复实现：

1. `app.py:289-291` — 主流程从 session_state 读取配置时
2. `core/llm_client.py:23-25` — `BaseLLMClient.__init__` 构造方法
3. `views/helpers.py:78-80` — `check_api_connection` 测试连接函数

三处代码逻辑相同（`strip().rstrip('/')` + 判断 `endswith('/v1')` 补全），但各自独立维护。一旦某处修改规则（如增加端口校验、协议检查等），会出现「测试连接成功但实际调用失败」的不一致问题，属于隐性故障源。

## What Changes

1. **`core/config.py`**：新增 `normalize_base_url(url: str) -> str` 工具函数，作为全局唯一标准实现
2. **`app.py`**：移除第 289-291 行的内联标准化，调用 `normalize_base_url`
3. **`core/llm_client.py`**：`__init__` 中的标准化逻辑改为调用 `normalize_base_url`
4. **`views/helpers.py`**：`check_api_connection` 中的标准化逻辑改为调用 `normalize_base_url`

## Capabilities

### New Capabilities

（无新增能力——本次变更为代码重构，不引入新功能。）

### Modified Capabilities

（无需修改已有 spec——本次不涉及需求层行为变更。）

## Impact

- **代码**：修改 4 个文件，`core/config.py` 新增 1 个纯函数，其余 3 处各改 1 行
- **API**：无变化（`normalize_base_url` 与原有逻辑行为完全等价）
- **依赖**：无新增
- **风险**：极低——纯函数替换，行为不变；`normalize_base_url` 可独立单元测试
