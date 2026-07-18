## Why

项目中有 4 处 `try: ... except Exception: pass`，异常被完全静默吞掉。最严重的是 `tab2_detect.py:30`——数据库写入失败时用户完全不知情，检测结果可能丢失但页面仍显示"完成"。其余 3 处虽然影响较小（AI 标题失败、元数据解析失败），但同样会导致排查问题时无从下手。

## What Changes

将 4 处 `except: pass` 改为带有提示或日志的写法：
- **core/utils.py** 的 2 处 → 使用 `print` 或 `logging` 输出警告（纯后端函数，无 UI 上下文）
- **views/tab1_build.py** 的 1 处 → 捕获异常后以 `st.warning` 提示
- **views/tab2_detect.py** 的 1 处 → 捕获异常后以 `st.warning` 提示

## Capabilities

### New Capabilities
- `visible-error-handling`: 异常捕获点不再静默吞错误，改为输出提示或日志

### Modified Capabilities
<!-- No existing specs to modify -->

## Impact

- **修改范围**：3 个文件，4 处 `except: pass`
  - `core/utils.py:61` — `save_dataset()` 中 AI 标题生成失败
  - `core/utils.py:144` — `list_datasets()` 中元数据解析失败
  - `views/tab1_build.py:271` — 投毒后 AI 标题建议失败
  - `views/tab2_detect.py:30` — DB 初始记录写入失败
- **对外接口**：无变化
- **依赖**：无新增（utils.py 纯后端使用 `print`，view 层使用已有的 `st.warning`）
