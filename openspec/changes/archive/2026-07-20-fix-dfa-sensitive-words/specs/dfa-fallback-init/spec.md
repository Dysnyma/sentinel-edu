# 敏感词文件缺失自动降级

## ADDED Requirements

### Requirement: 文件缺失时自动创建模板
当 `sensitive_words.txt` 不存在时，系统 SHALL 自动创建一个空模板文件并记录日志，而非抛出异常。

- 检测文件是否存在使用 `os.path.exists()`。
- 文件缺失时：确保父目录存在 → 创建空文件 → `logging.warning()` 输出提示。
- 创建后继续以空词表初始化 DFA 扫描器（不加载任何敏感词）。

#### Scenario: 首次运行
- **WHEN** 仓库中没有 `sensitive_words.txt`
- **THEN** `DFAScanner('sensitive_words.txt')` 正常初始化，不抛出异常
- **THEN** `sensitive_words.txt` 被创建（空文件）
- **THEN** `scan()` 对任何文本返回 `(False, [])`

### Requirement: 文件正常时行为不变
当 `sensitive_words.txt` 存在时，DFAScanner 的初始化行为与之前完全一致。

#### Scenario: 正常启动
- **WHEN** `sensitive_words.txt` 存在且包含关键词
- **THEN** DFAScanner 正常加载词表，`scan()` 正常匹配
