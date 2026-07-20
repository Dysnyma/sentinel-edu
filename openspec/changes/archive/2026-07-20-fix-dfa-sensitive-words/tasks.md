## 1. DFA 文件 guard

- [x] 1.1 在 `core/dfa_scanner.py` 顶部添加 `import os` 和 `import logging`
- [x] 1.2 在 `_load()` 方法开头添加文件存在性 guard（不存在则创建 + logging.warning）
- [x] 1.3 新建 `sensitive_words.txt` 模板文件（已存在，内容完整）

## 2. 仓库基础设施

- [x] 2.1 更新 `.gitignore`（已完善，无需修改）
- [x] 2.2 新建 `requirements.txt`（已存在，内容完整）
- [x] 2.3 补充 `README.md` Quick Start 段落（已完善，无需修改）

## 3. 验证

- [x] 3.1 语法检查通过
- [x] 3.2 现有测试 34/37 通过（3 个失败为 conftest 已知问题，与本次改动无关）
- [x] 3.3 smoke test：删除 sensitive_words.txt 后 DFAScanner 正常导入，文件自动重建
