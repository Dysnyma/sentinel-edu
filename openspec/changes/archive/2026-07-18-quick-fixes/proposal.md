## Why

代码库中存在三个明确的代码质量问题：异常被静默吞没（`except: pass`）、手动管理全局单例（应使用框架机制）、以及 API 返回值缺少防御性校验。这些问题虽不直接影响功能可用性，但会掩盖错误、增加维护成本、并在 API 异常时提供无上下文信息的错误消息。本次集中修复，一次性清扫。

## What Changes

1. **修复异常吞没**（`core/config.py`）：将 `load_config_from_file` 和 `save_session_state` 中的 `except OSError: pass` 替换为使用 `logging.warning()` 输出日志，不再静默吞没文件读写异常。
2. **优化单例管理**（`core/asr.py`）：移除自定义全局变量 `_local_model` / `_local_model_name` 及对应的 hand-rolled 懒加载逻辑，改为直接使用 Streamlit 内置的 `@st.cache_resource` 装饰器管理 Whisper 模型单例。
3. **增强 API 容错**（`core/llm_scanner.py`）：在解析 API 响应时，显式校验响应对象是否包含 `choices` 属性，若缺失则抛出携带上下文信息的 `ValueError`，方便定位问题。

## Capabilities

### New Capabilities

无。本次变更是纯代码质量改进（internal refactoring），不引入新的能力。

### Modified Capabilities

无。三个变更均不涉及需求层面的行为变化，仅影响内部实现。

## Impact

- `core/config.py`：新增 `import logging`，增加两条日志调用（文件读/写异常时输出 warning）。
- `core/asr.py`：删除全局变量 `_local_model` 与 `_local_model_name`；`get_local_whisper_model` 函数签名保持不变但实现改为 `@st.cache_resource` 装饰。
- `core/llm_scanner.py`：增加一段对 `resp.choices` 的防御性检查，失败时抛出更有信息量的 `ValueError`。
- 无外部依赖变更，无数据库 schema 变更。
