## Why

项目经过多轮重构后，核心模块（BaseLLMClient、build_controller、detect_controller、utils）已有清晰的职责边界和纯函数接口，但没有任何自动化测试覆盖。每次修改都需要手动启动 App 验证，效率低且容易遗漏边界情况。引入 pytest 后可以：

- 对 `BaseLLMClient` 的重试机制、响应解析、异常处理做自动化测试（mock 掉网络调用）
- 对 Controller 层的纯函数（`init_db_records`、`run_concurrently`、`_highlight_diff` 等）做独立验证
- 建立 CI 可执行的测试基线，防止重构引入回归

## What Changes

1. **安装 pytest 依赖**：在项目根目录添加 `requirements-dev.txt` 或更新 `pyproject.toml`。
2. **新建 `tests/` 目录**：按模块组织测试文件，每文件对应一个 `core/` 模块。
3. **`tests/test_llm_client.py`**：mock `openai.OpenAI` 的返回值，测试 `BaseLLMClient` 的指数退避重试、响应提取、`json_repair` 修复与类型检查。
4. **`tests/test_utils.py`**：测试 `run_concurrently` 的并发执行、进度回调、异常收集。
5. **`tests/test_build_controller.py`** 和 **`tests/test_detect_controller.py`**：测试纯函数（无需 Streamlit 环境的部分）。
6. **运行验证**：`python -m pytest tests/ -v` 全部通过。

## Capabilities

### New Capabilities
- `unit-testing`: pytest 测试框架及按模块组织的测试用例

### Modified Capabilities
无。

## Impact

- `tests/`：新增目录
- `tests/conftest.py`：共享 fixture（mock 客户端等）
- `tests/test_llm_client.py`：10-15 个测试用例
- `tests/test_utils.py`：5-8 个测试用例
- `tests/test_build_controller.py`：3-5 个测试用例
- `tests/test_detect_controller.py`：3-5 个测试用例
- `requirements-dev.txt` 或 `pyproject.toml`：新增 pytest 依赖
- 无业务代码修改
