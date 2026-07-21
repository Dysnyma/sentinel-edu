## Why

当前 `llm_scan`、`generate_poison`、`correct_text` 等业务函数每次被调用时都新建一个 `BaseLLMClient` 实例，底层对应新建一个 `OpenAI` 客户端。OpenAI 客户端内置 HTTP 连接池（默认 `httpx` 连接池），频繁重建导致 TCP 连接无法复用——并发批量扫描场景下，系统需要反复创建和销毁连接，造成端口占用过高、性能下降。

## What Changes

1. **`core/llm_client.py`**：在 `BaseLLMClient` 上新增：
   - 类级别的 `_instance_cache: dict` 缓存字典
   - `threading.Lock` 保证线程安全
   - `@classmethod get_instance(api_key, base_url, model)` 工厂方法：以 `(api_key, base_url)` 为键，命中返回缓存实例，未命中则新建并缓存
   - 保留 `__init__` 构造方法完全不变，确保现有直接实例化代码不受影响

2. **`core/llm_scanner.py`**：`llm_scan()` 中改由 `BaseLLMClient.get_instance()` 获取客户端实例

3. **`core/poison_generator.py`**：`generate_poison()` 中改由 `BaseLLMClient.get_instance()` 获取客户端实例

4. **`core/text_correction.py`**：`correct_text()` 中改由 `BaseLLMClient.get_instance()` 获取客户端实例

## Capabilities

### New Capabilities

（无新增能力——本次变更为性能优化，不引入新功能。）

### Modified Capabilities

（无需修改已有 spec——本次不涉及需求层行为变更。）

## Impact

- **代码**：修改 4 个文件，`llm_client.py` 新增工厂方法，其余 3 个文件各改 1 行（`BaseLLMClient(...)` → `BaseLLMClient.get_instance(...)`）
- **API**：无变化（外部调用接口不变）
- **依赖**：无新增（`threading` 为内置库）
- **性能**：相同 `(api_key, base_url)` 配置的多次调用共享连接池，批量并发场景 TCP 连接数显著减少
- **风险**：低——仅替换实例化方式，业务逻辑不变；缓存按 `(api_key, base_url)` 隔离，互不污染
