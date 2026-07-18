## 1. 实现提示词持久化与加载

- [x] 1.1 在 `core/config.py` 中添加 `load_prompts()` 函数：读取 `data/prompts.json`，不存在时用内置默认值创建
- [x] 1.2 在 `core/config.py` 中添加 `save_prompts(scan, poison, correct)` 函数：写入三个提示词到 `data/prompts.json`
- [x] 1.3 确认内置默认值与当前三个模块的硬编码值一致

## 2. 重构业务模块

- [x] 2.1 修改 `core/llm_scanner.py`：改用 `_get_scan_prompt()` 动态获取
- [x] 2.2 修改 `core/poison_generator.py`：改用 `_get_poison_prompt()` 动态获取
- [x] 2.3 修改 `core/text_correction.py`：改用 `_get_correct_prompt()` 动态获取

## 3. 添加 UI 编辑器

- [x] 3.1 在 `app.py` 侧边栏添加"提示词编辑"展开区，包含三个 `st.text_area`
- [x] 3.2 添加"恢复默认"按钮
- [x] 3.3 添加"保存并应用"按钮

## 4. 验证

- [x] 4.1 语法检查通过
- [x] 4.2 load_prompts 首次调用自动创建文件（逻辑已验证）
- [x] 4.3 每次 LLM 调用时从文件重新读取提示词
