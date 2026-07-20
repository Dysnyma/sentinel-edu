## Context

`core/dfa_scanner.py` 的 `DFAScanner.__init__` 调用 `_load(words_file)`，后者直接执行 `open(file_path, 'r', encoding='utf-8')`。如果 `sensitive_words.txt` 不存在（新 clone 仓库、CI 环境、用户误删），程序以 `FileNotFoundError` 崩溃，没有任何错误提示。

项目根目录目前缺少 `.gitignore`（导致 `data/` 下的运行时文件可能被误跟踪）、`requirements.txt`（依赖需要手动逐个安装）、以及 README 中的快速启动指引。

## Goals / Non-Goals

**Goals:**
- 缺失 `sensitive_words.txt` 时不崩溃，自动创建模板文件
- 新增最小的仓库基础设施文件
- 不修改现有测试

**Non-Goals:**
- 不改动 DFA 扫描逻辑、AC 自动机构建、或匹配算法
- 不引入新的 runtime 依赖
- 不做 CI/CD 配置

## Decisions

### 1. DFA 文件 guard

在 `_load()` 方法开头增加：

```python
if not os.path.exists(file_path):
    os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)
    open(file_path, 'a', encoding='utf-8').close()
    logging.warning("sensitive words file not found; created template at %s", file_path)
```

- 使用 `open(..., 'a')` 而不是 `'w'` 来创建空文件——如果文件已存在不会截断。
- 使用 `os.makedirs(..., exist_ok=True)` 确保父目录存在。
- `logging.warning` 而非 `print`，因为项目已统一使用 logging。

### 2. 模板文件

`sensitive_words.txt` 只包含一行注释和一个示例词，不含任何真实敏感词。

### 3. requirements.txt

列出最小 runtime 依赖，不做版本锁定（由用户自己 `pip freeze` 或使用 lock 文件）。附加注释说明 whisper 需要系统安装 ffmpeg。

### 4. .gitignore

忽略 `data/` 目录下的 JSON 和 SQLite 数据库文件，这些是运行时生成的用户数据。

## Risks / Trade-offs

- 【风险】`open(file_path, 'a')` 创建空文件后，DFAScanner 继续以空词表运行，不会误拦截任何文本 → 可接受，这是一个安全的降级行为
- 【风险】requirements.txt 没有锁定版本可能导致未来兼容性问题 → 最小项目阶段不建议锁定版本，给用户灵活性
