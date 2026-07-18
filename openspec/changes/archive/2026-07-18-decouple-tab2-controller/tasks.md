## 0. 迁移 run_concurrently 到 core/utils.py

- [x] 0.1 将 `run_concurrently` 从 `views/helpers.py` 移至 `core/utils.py`，将 `progress_placeholder` 参数替换为 `progress_callback(completed, total)`
- [x] 0.2 在 `views/helpers.py` 中保留一个向后兼容的包装函数（`run_concurrently_ui`），内部调用 `core.utils.run_concurrently` 并更新 Streamlit progress bar
- [x] 0.3 更新 `build_controller.py` 的 import，从 `core.utils` 而非 `views.helpers` 导入 `run_concurrently`

## 1. 创建 core/detect_controller.py

- [x] 1.1 实现 `init_db_records(all_data, dataset_id) -> int`：跳过已存在的 text_id，插入初始记录
- [x] 1.2 实现 `dfa_scan_all(all_data, dataset_id, progress_callback) -> dict`：逐条 DFA 扫描并写库
- [x] 1.3 实现 `llm_scan_candidates(candidates, api_key, base_url, model, concurrency, dataset_id, progress_callback) -> list`：并发 LLM 扫描并写库
- [x] 1.4 实现 `llm_scan_only(all_data, api_key, base_url, model, concurrency, dataset_id, progress_callback) -> list`：从 DB 读取 DFA 结果后仅 LLM 扫描
- [x] 1.5 实现 `inline_detect(text, api_key, base_url, model) -> dict`：单文本 DFA + LLM 扫描

## 2. 精简 views/tab2_detect.py

- [x] 2.1 删除 `_init_db_records` 函数，改为调用 `detect_controller.init_db_records()`
- [x] 2.2 删除 `_dfa_scan_all` 函数，改为调用 `detect_controller.dfa_scan_all()`
- [x] 2.3 删除 `_llm_scan_candidates` 函数，改为调用 `detect_controller.llm_scan_candidates()`
- [x] 2.4 将"仅 LLM 扫描"按钮的内联逻辑替换为 `detect_controller.llm_scan_only()`
- [x] 2.5 将"直接输入文本检测"的内联逻辑替换为 `detect_controller.inline_detect()`
- [x] 2.6 将 import 替换为从 `detect_controller` 导入

## 3. 验证

- [x] 3.1 运行 `python3 -m py_compile core/detect_controller.py views/tab2_detect.py` 确认语法正确
- [x] 3.2 确认 tab2_detect.py 行数从 ~518 减少
