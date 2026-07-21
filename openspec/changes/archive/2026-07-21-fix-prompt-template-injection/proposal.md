## Why

当前 `core/llm_scanner.py`、`core/poison_generator.py`、`core/text_correction.py` 三个文件中的 LLM 提示词模板使用多次链式 `str.replace()` 替换变量。若输入文本本身包含 `{dfa_hint}`、`{text}` 等模板占位符字符串，会触发二次替换，破坏提示词结构，存在安全注入绕过风险。

## What Changes

1. **`core/llm_scanner.py` — `llm_scan()` 函数**：将 `_get_scan_prompt()` 的链式 `.replace('{dfa_hint}', ...).replace('{text}', ...)` 改为 `str.format()` 一次性渲染。
2. **`core/poison_generator.py` — `generate_poison()` 函数**：将 `_get_poison_prompt()` 的 `.replace('{text}', ...)` 改为 `str.format()` 一次性渲染。
3. **`core/text_correction.py` — `correct_text()` 函数**：将 `_get_correct_prompt()` 的 `.replace('{text}', ...)` 改为 `str.format()` 一次性渲染。

以上修改均**不涉及**提示词模板原文内容的改动（`{{`/`}}` 转义已在模板中正确存在），**不增加**新依赖，**不改变**函数签名、输出格式或现有行为。

## Capabilities

### New Capabilities

（无新增能力——本次变更为纯安全修复，不引入新功能。）

### Modified Capabilities

（无需修改已有 spec——本次不涉及需求层的行为变更，仅为实现层面的字符串渲染逻辑优化。）

## Impact

- **代码**：仅修改 3 个文件各 1 行，其他代码完全不变
- **API**：无变化（函数签名、返回值均保持不变）
- **依赖**：无新增依赖
- **测试**：现有单元测试应全部通过；建议增加注入用例（输入含 `{text}` 或 `{dfa_hint}` 的文本）验证修复效果
- **风险**：极低——`str.format()` 为 Python 内置安全字符串插值，单次替换的特性从根源阻断二次注入
