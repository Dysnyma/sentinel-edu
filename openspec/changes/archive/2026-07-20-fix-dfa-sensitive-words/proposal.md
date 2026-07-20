## Why

DFAScanner 在初始化时直接 `open(sensitive_words.txt)`，仓库中缺少该文件会导致首次启动或 CI 运行直接崩溃。同时，项目缺少基础的仓库基础设施（`.gitignore`、`requirements.txt`、README 指引），影响新成员上手体验。

## What Changes

1. **`core/dfa_scanner.py`**：在 `_load()` 方法中添加文件存在性 guard——当 `sensitive_words.txt` 不存在时自动创建空文件并记录 `logging.warning`。
2. **`sensitive_words.txt`**：新建模板文件，包含一行注释和示例词。
3. **`.gitignore`**：忽略 `data/*.json`、`data/*.db` 等运行时文件。
4. **`requirements.txt`**：最小 runtime 依赖清单。
5. **`README.md`**：补充 Quick Start 指引、Python 版本要求、运行/测试命令、API Key 安全提示。

## Capabilities

### New Capabilities
- `dfa-fallback-init`: 敏感词文件缺失时自动创建模板而非崩溃

### Modified Capabilities
无。

## Impact

- `core/dfa_scanner.py`：+8 行（import + guard）
- `sensitive_words.txt`：新增（模板，不含真实敏感词）
- `.gitignore`：追加两行
- `requirements.txt`：新增
- `README.md`：补充段落
- 不修改任何测试文件
