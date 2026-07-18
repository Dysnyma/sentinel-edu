## Why

`views/tab2_detect.py`（518 行）是当前代码库中最长的文件之一。它混合了 Streamlit UI 渲染、DFA 扫描调度、LLM 并发请求、数据库读写、以及复杂的过滤/搜索/高亮逻辑。与 tab1 重构前类似，视图层与控制层高度耦合，使得修改 UI 容易误伤业务逻辑，也无法独立测试检测流水线。

本次重构沿袭 tab1 的模式，将 DFA/LLM 扫描调度和数据库操作抽取到 `core/detect_controller.py`，让 `tab2_detect.py` 只负责 UI 组件渲染和数据展示。

## What Changes

1. **新增 `core/detect_controller.py`**：提取 tab2_detect.py 中所有的非 UI 业务逻辑，封装为独立函数。
2. **精简 `views/tab2_detect.py`**：仅保留 Streamlit 组件渲染、session_state 读写、和结果展示，所有检测和数据库操作委托给 `detect_controller`。
3. **保持行为等价**：不改变任何用户可见的行为。

## Capabilities

### New Capabilities
- `detect-controller`: 安全检测控制层，提供与 UI 无关的纯业务函数（DFA 扫描、LLM 并发扫描、数据库初始化/写入、进度回调）

### Modified Capabilities
无。行为不变，纯内部重构。

## Impact

- `core/detect_controller.py`：新增文件，约 150-180 行
- `views/tab2_detect.py`：从 518 行缩减至约 250 行（仅 UI 组件和展示逻辑）
- `core/database.py`、`core/dfa_scanner.py`、`core/llm_scanner.py`：无变动
- 无外部依赖变更
