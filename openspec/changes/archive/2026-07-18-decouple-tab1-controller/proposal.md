## Why

`views/tab1_build.py` 当前是 319 行的"上帝文件"，将 Streamlit UI 渲染、session_state 管理、音视频文件处理、外部工具调度（BBDown/FFmpeg）、并发任务分发、JSONL 数据集操作全部混在一起。每次修改 UI 都需要触碰到底层逻辑，每次修改底层逻辑又担心破坏 UI。视图层与控制层严重耦合，使得维护、测试、复用都变得困难。

## What Changes

1. **新建 `core/build_controller.py`**：提取 tab1_build.py 中所有的非 UI 业务逻辑，封装为独立的函数。
2. **精简 `views/tab1_build.py`**：仅保留 Streamlit 组件渲染（`st.radio`、`st.button`、`st.text_area`）和 session_state 读写，所有底层操作委托给 `build_controller`。
3. **保持行为等价**：不改动用户可见的任何行为。

## Capabilities

### New Capabilities
- `build-controller`: 测试集构建控制层，提供一组与 UI 无关的纯业务函数（文件处理、并发调度、错误收集、数据集保存）

### Modified Capabilities
无。行为不变，纯内部重构。

## Impact

- `core/build_controller.py`：新增文件，约 150-200 行
- `views/tab1_build.py`：从 319 行缩减至约 120 行（仅 UI 组件）
- `core/utils.py`、`views/helpers.py`：无变动（部分函数调用方从 tab1_build 变为 build_controller）
- 无外部依赖变更
