## Context

`views/tab1_build.py`（319 行）是一个典型的 Streamlit "上帝组件"——UI 渲染、session 状态、文件 I/O、外部进程调度、并发控制全部写在一个函数 `render_tab1()` 中。具体来说：

| 职责 | 散落位置 |
|---|---|
| 音视频临时文件创建/清理 | `with tempfile.NamedTemporaryFile` 内联 |
| BBDown 下载 + FFmpeg 音频提取 | 内联，调用 core/asr.py |
| 文本纠错迭代执行 | 内联 for 循环 |
| 投毒并发分发 | 组装 `tasks` 列表后调用 `run_concurrently` |
| JSONL 读取/保存/合并 | 调用 core/utils.py，但调用逻辑写在 tab1 中 |

重构目标：将这些职责集中到 `core/build_controller.py`，使 `tab1_build.py` 只做 UI 渲染。

## Goals / Non-Goals

**Goals:**
- `tab1_build.py` 中不再包含任何文件 I/O、外部进程调用、循环/并发控制逻辑
- 所有业务函数以"接受数据 → 返回数据"的形式暴露，不依赖 `st.*` 或 `st.session_state`
- 每个函数职责单一、可独立测试

**Non-Goals:**
- 不改动 core/asr.py、core/text_correction.py、core/poison_generator.py、core/utils.py 中的现有函数
- 不改动 UI 布局或用户交互流程

## Decisions

### 1. 提取的函数

```
build_controller.py
├── process_uploaded_file(file_bytes, file_name, use_local, ...) -> str
│     临时文件创建 → 音频提取 → ASR 转写 → 返回文本
│
├── download_bilibili(url, bbdown_path, ffmpeg_path, use_local, ...) -> str
│     BBDown 下载 → 字幕提取或 FFmpeg 提取 → ASR 转写 → 返回文本
│
├── run_text_correction(texts, api_key, base_url, model, progress_cb) -> list[str]
│     逐条调用 correct_text，收集结果与异常
│
├── run_poison_generation(clean_path, poison_ratio, api_key, ...) -> dict
│     加载 JSONL → 随机采样 → 并发投毒 → 收集结果 → 合并 JSONL → 返回路径
│
├── transcribe_and_save_dataset(...) -> str
│     ASR 完成后自动保存原始数据集
│
└── save_corrected_dataset(...) -> str
      纠错完成后自动保存无毒数据集
```

### 2. 进度回调模式

涉及耗时的操作（纠错、投毒）通过可选的 `progress_callback` 参数报告进度，而非使用 Streamlit 的 `st.progress`：

```python
def run_text_correction(texts, ..., progress_callback=None) -> list[str]:
    for i, text in enumerate(texts):
        ...
        if progress_callback:
            progress_callback(i + 1, total)
```

tab1_build.py 在调用时传入 lambda 更新 `st.progress`。

### 3. 异常处理策略

- 可恢复异常（单条纠错/投毒失败）：在 controller 内部捕获，记录错误信息，继续处理下一条。返回结构包含 `errors: list[tuple[int, str]]`。
- 不可恢复异常（文件不存在、API 配置缺失）：让异常向上传播到 UI 层，由 `st.error()` 展示。

### 4. 文件路径管理

- controller 的函数不写死路径，通过参数传入输入/输出路径。
- tab1_build.py 决定路径并传入（因为路径可能来自 session_state）。

## Risks / Trade-offs

- 【风险】进度回调参数增加了函数签名复杂度 → 使用默认值 `None`，调用方可以不传
- 【风险】controller 函数返回结构变更需要同步更新 tab1_build.py 的调用方 → 这是一个一次性迁移，完成后收益大于成本
