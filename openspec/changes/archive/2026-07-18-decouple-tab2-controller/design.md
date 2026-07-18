## Context

`views/tab2_detect.py`（518 行）负责安全检测页面的全部逻辑。与重构前的 `tab1_build.py` 类似，其职责混合情况如下：

| 职责 | 现位置 | 目标 |
|---|---|---|
| DB 初始化和记录插入 | `_init_db_records()` | → controller |
| DFA 全量扫描 + 写库 | `_dfa_scan_all()` | → controller |
| LLM 并发扫描 + 写库 | `_llm_scan_candidates()` | → controller |
| "仅 LLM 扫描"按钮逻辑 | `render_tab2()` 内联 | → controller |
| 并发任务分发 | `views/helpers.run_concurrently()` | → `core/utils.py` |
| 状态表渲染 | `_render_status_table()` | 保留在 tab2 |
| 批量高亮 | `_render_batch_highlight()` | 保留在 tab2 |
| 深度对比（筛选/三栏/命中分析） | `_render_detail_view()` | 保留在 tab2 |
| 直接输入检测 | `_render_inline_detect()` | 保留 UI，扫描逻辑委托 |
| 文件选择/数据集加载 | `render_tab2()` | 保留 UI，加载委托 |

## Goals / Non-Goals

**Goals:**
- `tab2_detect.py` 中不再包含 DFA 扫描、LLM 扫描、DB 读写等非 UI 逻辑
- 所有控制器函数以"接受数据 → 返回数据"形式暴露，不依赖 `st.*` 或 `st.session_state`
- 耗时操作通过可选的 `progress_callback` 报告进度

**Non-Goals:**
- 不改动 DFA 扫描器、LLM 扫描逻辑、数据库 schema
- 不改动 UI 布局或交互流程

## Decisions

### 1. 提取的函数

```
core/utils.py (新增)
└── run_concurrently(tasks, max_workers, progress_cb) -> list
     通用并发任务分发，已脱离 Streamlit 依赖

core/detect_controller.py
├── init_db_records(all_data, dataset_id) -> int
│     为新样本插入初始记录，返回新增条数
│
├── dfa_scan_all(all_data, dataset_id, progress_cb) -> dict
│     DFA 全量扫描并写库，返回 {text_id: (hit, words)}
│
├── llm_scan_candidates(candidates, api_key, base_url, model, concurrency, dataset_id, progress_cb) -> list
│     并发 LLM 扫描并写库，返回每条结果
│
├── llm_scan_only(all_data, api_key, base_url, model, concurrency, dataset_id, progress_cb) -> list
│     仅 LLM 扫描（从 DB 读取已有 DFA 结果），供"仅 LLM"按钮使用
│
└── inline_detect(text, api_key, base_url, model) -> dict
     单文本 DFA + LLM 扫描，返回检测结果字典
```

### 2. 进度回调模式

与 `build_controller.py` 一致，耗时操作通过 `progress_callback(current, total)` 报告进度：

```python
def dfa_scan_all(all_data, dataset_id, progress_callback=None) -> dict:
    for i, rec in enumerate(all_data):
        ...
        if progress_callback:
            progress_callback(i + 1, total)
```

### 3. 返回结构

- `dfa_scan_all` 返回 `dict[text_id, (hit: bool, words: list)]`
- `llm_scan_candidates` 返回 `list[dict]` 即每条 API 响应的原样列表（异常时为 Exception）
- `inline_detect` 返回 `{"dfa_hit": bool, "dfa_words": list, "llm_result": dict|None, "llm_error": str|None}`

### 4. `run_concurrently` 迁移至 `core/utils.py`

原有的 `run_concurrently` 位于 `views/helpers.py` 且签名包含 `progress_placeholder`（Streamlit 组件对象），导致任何需要并发能力的 controller 模块都必须跨层依赖 `views.` 包，违背解耦目标。

**变更方案：**
- 将函数移至 `core/utils.py`，`progress_placeholder` 参数替换为通用的 `progress_callback(completed, total)` 回调
- 签名变更为 `run_concurrently(tasks, max_workers=6, progress_callback=None) -> list`
- `views/helpers.py` 中原位置保留一个薄包装，供现有 UI 代码使用：
  ```python
  # views/helpers.py
  def run_concurrently_ui(tasks, max_workers=6, progress_placeholder=None, progress_text=""):
      ...  # 内部调用 core.utils.run_concurrently + 更新 st.progress
  ```
- `build_controller.py` 和 `detect_controller.py` 都从 `core.utils` 导入

## Risks / Trade-offs

- 【风险】`llm_scan_only` 需要从 DB 读取已有 DFA 结果 → 与 `llm_scan_candidates` 逻辑重叠但入口不同
  → **接受**：两个函数的输入预处理不同（一个从入参数组，一个从 DB 读），合并会引入不必要的复杂度
