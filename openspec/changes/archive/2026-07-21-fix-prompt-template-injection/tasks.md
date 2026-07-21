## 1. 修改 `core/text_correction.py`

- [x] 1.1 将 `correct_text()` 中的 `.replace('{text}', text)` 改为 `.format(text=text)`（仅修改第 28 行）

## 2. 修改 `core/poison_generator.py`

- [x] 2.1 将 `generate_poison()` 中的 `.replace('{text}', text)` 改为 `.format(text=text)`（仅修改第 38 行）

## 3. 修改 `core/llm_scanner.py`

- [x] 3.1 将 `llm_scan()` 中的链式 `.replace('{dfa_hint}', dfa_hint).replace('{text}', text)` 改为 `.format(dfa_hint=dfa_hint, text=text)`（仅修改第 46 行）

## 4. 验证

- [x] 4.1 运行现有单元测试，确认全部通过
- [x] 4.2 手动确认三个文件中无其他链式 `.replace()` 提示词注入漏洞遗漏
