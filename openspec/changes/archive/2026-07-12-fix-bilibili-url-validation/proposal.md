## Why

`core/asr.py:download_bilibili_video()` 直接接收用户输入的 B 站链接并传给 `subprocess.run()`，没有任何 URL 校验。恶意链接可能导致执行意外的命令或下载恶意内容。bandit 安全扫描已标记此处为 **B603（Low 风险）**。加上 URL 白名单校验，从入口阻断注入可能。

## What Changes

- `core/asr.py` `download_bilibili_video()` 函数新增 URL 域名白名单校验
- 只允许 `bilibili.com` 和 `b23.tv` 两个域名的链接通过
- 非法链接抛出 `ValueError`，由上游 UI 层现有的 `try/except` 捕获并显示友好提示
- 不修改 `download_bilibili_video()` 的函数签名和正常执行路径

## Capabilities

### New Capabilities
- `safe-url-input`: 对外部输入的 URL 在执行命令前做域名白名单校验

### Modified Capabilities
<!-- No existing specs to modify -->

## Impact

- **修改范围**：仅 `core/asr.py` 中 `download_bilibili_video()` 函数，增加 URL 校验逻辑
- **对外接口**：函数签名不变。非法 URL 时抛出 `ValueError`，正常路径行为不变
- **依赖**：使用 Python 标准库 `urllib.parse`，零新增依赖
