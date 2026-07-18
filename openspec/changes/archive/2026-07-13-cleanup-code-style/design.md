## Context

代码体检报告中的 flake8 告警全部是格式/冗余类问题，不影响功能。分四类处理：

1. **F401 未使用的导入** — 直接删除 import 行（views/__init__.py 除外，其聚合导出是设计意图）
2. **F841 赋值未使用** — 删除赋值语句，如果变量后续仅在计算中使用且结果被丢弃则整行删
3. **E741 歧义变量名** — `l` → `span`（语义清晰）
4. **格式类** — 空格、空行、缩进、逗号，逐处微调

## Goals / Non-Goals

**Goals:**
- flake8 告警数归零
- 只改语法层面的事，不动语义

**Non-Goals:**
- 不引入 `black` 或 `ruff` 等格式化工具（用户未要求，且引入工具意味着全量格式化，变更范围过大）
- 不修改 views/__init__.py
- 不重构代码结构

## Decisions

### 方案：逐文件手动清理 vs 自动格式化工具

手动清理更可控，能确保每处改动只解决对应告警、不引入新问题。自动格式化工具（如 black）会全量重排所有文件，与"不修改业务逻辑、不改变执行流程"的约束不兼容。

### 各问题处理明细

| 文件 | 告警 | 处理方式 |
|------|------|----------|
| `app.py:5` | F401 `Path` | 删除 `from pathlib import Path` |
| `core/asr.py:4,6` | F401 `tempfile`, `shutil` | 删除两行 import |
| `core/text_correction.py:2` | F401 `re` | 删除 `import re` |
| `views/helpers.py:103` | F401 `pd` | 删除 `import pandas as pd` |
| `views/tab2_detect.py:5` | F401 `pd` | 删除 `import pandas as pd` |
| `views/tab2_detect.py:10` | F401 `get_results_by_dataset` | 删除该 import |
| `views/tab2_detect.py:347` | F841 `llm_time` | 删除 `llm_time = ...` 行 |
| `views/tab2_detect.py:311` | E741 `l` | `l` → `span` |
| `views/tab1_build.py:68,130` | E306 | 嵌套 def 前加空行 |
| `views/tab1_build.py:69,131,193,307` | E226 | 运算符两边加空格 |
| `views/tab2_detect.py:55` | E226 | `(i + 1) / total` 已有空格，检查实际行 |
| `views/tab2_detect.py:481` | E128 | 缩进对齐 |
| `views/tab2_detect.py:515` | E231 | 逗号后加空格 |
| `views/tab3_analysis.py:7,10` | F401 `make_subplots`, `json` | 删除导入 |
| `views/tab3_analysis.py:275` | E231 | 逗号后加空格 |

### 注意点：f-string 内的 E226

`views/tab1_build.py:69` 中 `f"... {pct*100:.0f}%"` 的 `*` 缺少空格。在 f-string 内改为 `pct * 100` 语法是正确的，Python 完全支持。

## Risks / Trade-offs

- **[极低] 删除无用导入可能导致首次启动加载略快**，但差异可忽略
- **[极低] E741 修改变量名 `l`→`span` 不影响任何外部引用**，因为变量作用域仅限生成器表达式内部
