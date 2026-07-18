## 1. 初始化测试环境

- [x] 1.1 创建 `tests/` 目录和 `tests/__init__.py`
- [x] 1.2 创建 `requirements-dev.txt`（pytest>=7.0, pytest-mock>=3.0）
- [x] 1.3 创建 `tests/conftest.py`：共享 fixture（MockResponse 类等）

## 2. 编写 BaseLLMClient 测试

- [x] 2.1 重试机制测试：第 2 次成功、3 次全失败
- [x] 2.2 响应提取测试：正常提取、model_dump 降级、None 响应
- [x] 2.3 JSON 解析测试：Markdown 清理、修复解析、非 dict 类型检查
- [x] 2.4 URL 标准化测试

## 3. 编写工具函数测试

- [x] 3.1 `run_concurrently` 测试：正常执行、异常收集、进度回调计数
- [x] 3.2 `_split_sentences` 和 `_highlight_diff` 测试（从 tab1_build 导入）

## 4. 编写 Controller 层测试

- [x] 4.1 `build_controller.run_text_correction`：mock correct_text，测试进度回调和错误收集
- [x] 4.2 `detect_controller.inline_detect`：mock DFAScanner 和 llm_scan

## 5. 运行验证

- [x] 5.1 `python -m pytest tests/ -v` 全部通过（37/37）
