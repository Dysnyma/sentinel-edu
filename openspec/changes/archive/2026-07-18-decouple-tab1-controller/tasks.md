## 1. 创建 core/build_controller.py

- [x] 1.1 实现 `process_uploaded_file(file_bytes, file_name, use_local, local_model, ffmpeg_path, api_key, base_url, initial_prompt, progress_cb) -> str`：临时文件创建 → 音频提取 → ASR → 清理
- [x] 1.2 实现 `process_bilibili_url(url, bbdown_path, ffmpeg_path, use_local, local_model, api_key, base_url, initial_prompt, progress_cb) -> str`：BBDown → 字幕/ASR
- [x] 1.3 实现 `run_text_correction(texts, api_key, base_url, model, progress_cb) -> tuple[list[str], list[tuple[int,str]]]`：逐条纠错，返回 (结果列表, 错误列表)
- [x] 1.4 实现 `run_poison_generation(clean_path, poison_ratio, api_key, base_url, model, concurrency, progress_cb) -> dict`：采样 → 并发投毒 → 合并 JSONL
- [x] 1.5 实现 `transcribe_and_save_dataset(transcript, api_key, base_url, model) -> str`：ASR 后自动保存原始数据集
- [x] 1.6 实现 `save_corrected_dataset(texts, api_key, base_url, model) -> str`：纠错后自动保存无毒数据集

## 2. 精简 views/tab1_build.py

- [x] 2.1 将文件上传区（音视频）的处理逻辑替换为 `process_uploaded_file()` 调用
- [x] 2.2 将 B站下载区的处理逻辑替换为 `process_bilibili_url()` 调用
- [x] 2.3 将文本纠错循环替换为 `run_text_correction()` 调用
- [x] 2.4 将投毒生成逻辑替换为 `run_poison_generation()` 调用
- [x] 2.5 将数据集保存替换为 `transcribe_and_save_dataset()` / `save_corrected_dataset()` 调用
- [x] 2.6 删除所有不再需要的 import（`tempfile`, `uuid`, `shutil`, `random` 等）

## 3. 验证

- [x] 3.1 运行 `python3 -m py_compile core/build_controller.py views/tab1_build.py` 确认语法正确
- [x] 3.2 确认 tab1_build.py 已完全剥离业务逻辑（从 318 行混合代码变为 299 行纯 UI + 273 行 build_controller.py 纯业务）
