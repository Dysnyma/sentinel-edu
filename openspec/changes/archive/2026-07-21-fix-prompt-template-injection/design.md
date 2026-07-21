## Context

当前 `core/llm_scanner.py`、`core/poison_generator.py`、`core/text_correction.py` 三个文件中的 LLM 提示词模板使用多次链式 `str.replace()` 替换变量。例如 `llm_scanner.py:46`：

```python
_get_scan_prompt().replace('{dfa_hint}', dfa_hint).replace('{text}', text)
```

当 `dfa_hint` 或 `text`（均为用户输入或用户衍生文本）包含 `{text}` 或 `{dfa_hint}` 时，`replace()` 会依次扫描整个字符串，将已经替换或尚未替换的占位符再次替换，导致提示词结构损坏、语义偏移，甚至可能被用于绕过安全审核。

## Goals / Non-Goals

**Goals：**
- 消除三处 LLM 提示词模板的二次替换注入风险
- 修改后提示词渲染结果与修改前在正常输入下完全一致
- 零新增依赖，零 API 变更

**Non-Goals：**
- 不修改提示词原文内容或语义
- 不改变函数签名、返回值类型或行为
- 不引入新的配置机制或模板引擎
- 不重构其他无关代码

## Decisions

### 决策：使用 `str.format()` 替代链式 `str.replace()`

| 方案 | 评价 |
|---|---|
| **`str.format()`（选定）** | Python 内置机制，单次扫描替换全部占位符。`{placeholder}` 在输入值中出现时被视为普通文本，不触发二次替换。已在 `poison_generator.py` 的 `{{`/`}}` JSON 转义中隐含使用（`format()` 的逃逸语法与现有转义完全兼容） |
| `string.Template` | 需要额外 import，且安全特性与 `format()` 等价，无收益 |
| f-string | 模板定义时就需要变量值，无法延迟到调用时替换，不适合"先定义模板→后取值"的模式 |
| 正则替换 | 多步骤处理链，复杂度远超需求，且需处理捕获组转义 |
| 保持 `replace()` 加转义 | 需手动对输入内容中的 `{` 做 `{{` 转义，易遗漏，属于修补而非根治 |

**结论：** `str.format()` 是标准库中最简单、最安全的单次插值方案。

### 关于 `poison_generator.py` 的 `{{`/`}}` 兼容性

`_DEFAULT_POISON_PROMPT` 中已存在 `{{` / `}}`（为向 LLM 展示 JSON 输出格式示例），在 `str.replace()` 模式下这些双大括号**按字面原样传递**。切换到 `str.format()` 后，`{{` 自然地转义为单 `{`，`}}` 转义为单 `}`，输出与修改前完全一致，无需任何额外处理。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|---|---|
| 若配置中的自定义提示词模板包含未转义的 `{` 或 `}`，`format()` 会抛出 `KeyError` 或 `ValueError` | 原 `replace()` 模式下同样会错误替换；`format()` 只是更早暴露问题。且现有配置模板与内置模板结构相同，不会出现此情况 |
| 团队后续在提示词中新增 `{new_var}` 时需同步更新 `format()` 参数列表 | 这是更安全的默认行为——显式参数可防止遗漏新变量被意外当做普通文本。通过代码审查保障 |
| 模板占位符与 `format()` 参数数量/名称不匹配导致运行时错误 | 修改时严格一对一对齐，单元测试覆盖正常路径即可验证 |
