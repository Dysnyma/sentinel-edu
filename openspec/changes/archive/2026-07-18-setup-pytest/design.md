## Context

项目当前共约 15 个 Python 模块，经过多次重构后 controller 层已经与 UI 解耦，纯函数数量增多，可测试性大幅提升。主要可测试模块：

| 模块 | 可测试函数 | 难点 |
|---|---|---|
| `core/llm_client.py` | `call()`, `call_and_parse()`, `_call_api()`, `_extract_content()`, `_clean_markdown_json_markers()` | 需要 mock `openai.OpenAI` 的 `chat.completions.create` |
| `core/utils.py` | `run_concurrently()`, `texts_to_jsonl()`, `merge_jsonl()`, `load_jsonl()` | 无（纯文件/数据处理） |
| `core/build_controller.py` | `_split_sentences()`, `run_text_correction()`, `run_poison_generation()` | 需 mock LLM 函数 |
| `core/detect_controller.py` | `init_db_records()`, `inline_detect()` | 需 mock DB 和 DFAScanner |
| `views/helpers.py` (部分) | `_highlight_diff()` → 已移至 tab1_build | 纯字符串处理 |

## Goals / Non-Goals

**Goals:**
- pytest 运行环境就绪，`python -m pytest tests/ -v` 一键运行
- `BaseLLMClient` 核心路径全覆盖（重试、提取、解析、类型检查）
- Controller 层纯函数有基础用例
- 测试不依赖外部 API 或数据库（全部 mock/stub）

**Non-Goals:**
- 不做 UI 组件的测试（Streamlit 渲染逻辑不适合单元测试）
- 不做集成测试（不启动 App）
- 不追求 100% 覆盖率，聚焦核心逻辑和边界情况

## Decisions

### 1. 依赖管理

使用 `requirements-dev.txt` 文件，仅包含开发依赖：

```
pytest>=7.0
pytest-mock>=3.0
```

`requirements-dev.txt` 独立于主 `requirements.txt`，生产环境无需安装测试工具。

### 2. Mock 策略

对 `openai` 客户端使用 `unittest.mock.patch`（pytest-mock 的 `mocker` fixture）：

```python
def test_call_api_retry(mocker):
    mock_create = mocker.patch('openai.OpenAI')
    # 前两次抛出异常，第三次成功
    mock_create.chat.completions.create.side_effect = [
        openai.APITimeoutError("timeout"),
        openai.APIStatusError("error", response=...),
        MockResponse(choices=[...]),
    ]
    client = BaseLLMClient("key", "https://test.com/v1", "model")
    result = client.call([{"role": "user", "content": "hello"}])
    assert mock_create.chat.completions.create.call_count == 3
    assert result == "expected content"
```

### 3. 测试文件结构

```
tests/
├── conftest.py              # 共享 fixture
├── test_llm_client.py       # BaseLLMClient 全部测试
├── test_utils.py            # run_concurrently + JSONL 工具
├── test_build_controller.py # build_controller 纯函数
└── test_detect_controller.py# detect_controller 纯函数
```

### 4. 不测试 Streamlit 相关代码

`views/` 下的文件和 `core/config.py` 中依赖 `st.*` 的部分不做单元测试。这些逻辑适合手动验证或将来用 Playwright/Selenium 做 E2E。

## Risks / Trade-offs

- 【风险】mock `openai.OpenAI` 的复杂度过高 → 使用 `mocker.patch` 配合自定义 `MockResponse` 类简化
- 【风险】部分函数依赖文件系统（`data/prompts.json` 等）→ 使用 `tmp_path` fixture 确保隔离
- 【风险】DFAScanner 依赖 `sensitive_words.txt` 文件 → mock 整个扫描器或用 `tmp_path` 创建临时词表
