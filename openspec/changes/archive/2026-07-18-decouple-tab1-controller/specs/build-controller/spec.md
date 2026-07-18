# 测试集构建控制器

## ADDED Requirements

### Requirement: 音频文件处理
系统 SHALL 提供一个函数处理上传的音视频文件，完成临时文件创建、音频提取、ASR 转写全流程。

- 输入：文件二进制内容（`bytes`）、文件名、是否使用本地 Whisper、模型名称等参数
- 输出：转写后的纯文本字符串
- 内部自动管理临时文件的创建与清理
- 支持进度回调：`progress_callback(current, total)` 用于更新 UI 进度条

#### Scenario: 本地 Whisper 转写音频文件
- **WHEN** 调用处理函数，传入 wav 文件内容和 `use_local=True`
- **THEN** 函数使用本地 Whisper 模型完成转写，返回转写文本
- **THEN** 临时文件在处理完成后被自动删除

#### Scenario: 视频文件先提取音频再转写
- **WHEN** 传入 mp4 文件内容
- **THEN** 先调用 FFmpeg 提取音频到临时 wav 文件，再进行 ASR 转写

### Requirement: BBDown 下载处理
系统 SHALL 提供一个函数封装 BBDown 下载 + B 站视频处理流程。

- 输入：B站 URL、BBDown 路径、FFmpeg 路径等
- 输出：转写文本（优先使用字幕，无字幕则提取音频后 ASR）

#### Scenario: 有字幕的视频
- **WHEN** BBDown 下载的视频包含字幕文件
- **THEN** 直接读取字幕内容返回，跳过 ASR 转写

### Requirement: 文本纠错并发执行
系统 SHALL 提供一个函数，对一批文本逐条调用 LLM 纠错。

- 输入：文本列表、API 参数、可选的进度回调
- 输出：纠错后的文本列表，单条失败时自动保留原句
- 若进度回调不为 None，每条处理完后调用 `progress_callback(completed, total)`

#### Scenario: 全部成功
- **WHEN** 传入 10 条文本，所有纠错成功
- **THEN** 返回 10 条纠错后的文本列表

### Requirement: 投毒生成并发执行
系统 SHALL 提供一个函数，从 JSONL 文件中按比例采样后并发投毒并合并结果。

- 输入：JSONL 路径、投毒比例、API 参数、并发数、进度回调
- 输出：包含 `poison_records`（成功列表）、`errors`（失败记录索引与原因）的字典
- 内部完成随机采样、并发分发、结果收集、JSONL 合并

#### Scenario: 正常投毒
- **WHEN** 传入包含 20 条文本的 JSONL，投毒比例 0.3
- **THEN** 从 20 条中随机采样 6 条，并发调用投毒 API
- **THEN** 将中毒文本与无毒文本合并打乱，写入输出 JSONL
