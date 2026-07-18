## Context

现有代码中积累了三类常见的代码质量问题：

1. **异常吞没**：`core/config.py` 中两个函数（`load_config_from_file`、`save_session_state`）在文件 I/O 异常时直接用 `except OSError: pass` 静默吞掉错误，导致排查问题无从下手。
2. **手动单例**：`core/asr.py` 用全局变量 `_local_model` + 手工懒加载来缓存 Whisper 模型。Streamlit 的 `@st.cache_resource` 是官方推荐的资源缓存方式，且天然支持会话间复用、LRU 淘汰。
3. **API 防御缺失**：`core/llm_scanner.py` 已有部分防御性检查（如检查 `resp` 是否为字符串、是否有 `choices`），但 `choices` 检查仅在判断 `hasattr` 后抛一个泛化的 `ValueError`，未携带调用时的上下文信息（如使用的 API base URL、model 名称），不利于快速定位是哪个接口的问题。

三个修复点各自独立、互不耦合，可以各自单独实施和测试。

## Goals / Non-Goals

**Goals:**
- 消除 `except: pass` 模式，确保每个失败都有日志可查
- 移除手写全局单例，迁移到 Streamlit 官方缓存机制
- 当 API 响应结构异常时，抛出的异常包含足够上下文以便定位

**Non-Goals:**
- 不改变函数签名、返回类型或外部行为
- 不改动现有测试（如果存在）——功能等价，只需重新运行确认
- 不引入新的外部依赖

## Decisions

### 1. 日志方案（异常吞没修复）

- **选择**：标准库 `import logging` + `logging.getLogger(__name__)`，而非 `print()` 或 Streamlit 的 `st.warning()`。
- **理由**：`logging` 是 Python 标准做法，输出到 stderr 可通过 `PYTHONWARNINGS` / 日志配置统一控制；`st.warning()` 需要 Streamlit 运行时环境，在非 Streamlit 上下文中（如单元测试、后台脚本）可能不可用或产生副作用。
- **日志级别**：`warning` 级别——这些异常属于"可恢复但值得关注"的场景，不符合 error 的严重度。

### 2. 缓存方案（单例管理优化）

- **选择**：`@st.cache_resource` 替代全局变量 + 手工懒加载。
- **理由**：
  - `@st.cache_resource` 是 Streamlit 官方为管理"全局唯一资源"（ML 模型、数据库连接）设计的装饰器，自动处理跨 session 复用、重刷、TTL 等。
  - 删除手写的 `global _local_model` / `_local_model_name` 和 null-check 逻辑，减少 ~6 行样板代码。
  - 保留 `model_name` 参数——`@st.cache_resource` 默认以参数为 cache key，传入不同 `model_name` 时自动加载不同模型，比手写版本更健壮。
- **需注意**：`@st.cache_resource` 是 Streamlit 专有 API，如果该函数在 Streamlit 上下文外被调用会报错。但 `get_local_whisper_model` 的现有调用方全部在 Streamlit 的页面渲染流程中（`tab1_build.py` 等），因此安全。

### 3. 异常上下文（API 容错增强）

- **选择**：在缺失 `choices` 时抛出 `ValueError`，异常消息中包含 `model`、`base_url`、`resp` 的类型/结构摘要。
- **理由**：当前异常消息仅说"缺少 choices 字段"，但实际排查需要知道是哪个模型、哪个 base_url、响应体长什么样。增加这些上下文能显著减少调试时间。

## Risks / Trade-offs

- 【风险】`@st.cache_resource` 可能让 `model_name` 变化时旧模型在内存中滞留（直到被 LRU 淘汰）
  → **缓解**：这是预期行为，Streamlit 默认 LRU 容量为 256，对 Whisper 模型（通常同时只 1~2 个）绰绰有余。

- 【风险】`logging.warning()` 默认输出到 stderr，Streamlit 日志若能见度不足可能被忽略
  → **缓解**：不影响 fix 本身，且用户可通过 Streamlit 的 `config.toolbar` 或运行日志定位。

- 【风险】API 容错增强改变了异常抛出位置但没有改变异常类型（仍是 `ValueError`），调用方无需调整 catch 逻辑
  → **缓解**：向后兼容，无需改动上游代码。
