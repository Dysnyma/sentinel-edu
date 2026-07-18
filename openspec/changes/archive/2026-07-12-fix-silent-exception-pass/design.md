## Context

4 处 `except: pass` 分布在后端工具函数和 UI 层代码中，需要区分场景做不同处理：

1. **纯后端函数**（`core/utils.py`）→ 没有 Streamlit 上下文，不能用 `st.warning`，用内置 `print` 输出到日志
2. **UI 层函数**（`views/tab1_build.py`、`views/tab2_detect.py`）→ 可以用 `st.warning` 给用户轻量提示

## Goals / Non-Goals

**Goals:**
- 4 处 `except: pass` 全部改为带提示/日志的写法
- 纯后端用 `print` 输出警告，UI 层用 `st.warning` 提示用户
- 保留异常兜底逻辑（不抛出，不崩溃）

**Non-Goals:**
- 不引入 `logging` 模块（对原型项目过于重量级，`print` 已足够当前调试需求）
- 不改变异常范围（仍用 `except Exception`，不缩小到具体异常类型）
- 不修改函数签名和返回逻辑

## Decisions

### 各位置处理方式

| 位置 | 异常场景 | 处理方式 | 消息内容 |
|------|----------|----------|----------|
| `utils.py:61` | AI 标题生成失败 | `print(f"[WARN] ...")` | "AI 标题生成失败" |
| `utils.py:144` | JSON 元数据解析失败 | `print(f"[WARN] ...")` | "元数据文件解析失败：{meta_path}" |
| `tab1_build.py:271` | AI 标题建议失败 | `st.warning(...)` | "AI 标题建议失败，将使用默认名称" |
| `tab2_detect.py:30` | DB 初始记录写入失败 | `st.warning(...)` | "样本 {id} 初始记录写入失败" |

### 为什么 utils.py 用 `print` 而不是 `logging`？

- `logging` 需要额外配置（handler / formatter / level），对原型项目来说太重
- `print` 输出到 stderr/stdout，在本地运行和 Streamlit 日志面板中都能看到
- 未来如果需要更规范的日志，可以统一用 `logging` 替代，但当前阶段 `print` 足够了

## Risks / Trade-offs

- **[极低] UI 层用 st.warning 可能让用户困惑**：但提示信息写得克制（"xxx 失败，已使用默认值"），用户明白失败了但不是崩溃性错误
- **[极低] utils.py 中 print 会输出到 stderr**：不会显示在前端，但开发者查看 Streamlit 日志时能看到，利于调试
