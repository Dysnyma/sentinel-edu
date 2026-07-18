## Context

`download_bilibili_video(url)` 在 `asr.py:150` 处将 `url` 直接传给 `subprocess.run()`：

```python
def download_bilibili_video(url: str, bbdown_path='./BBDown') -> dict:
    downloads_dir = os.path.join(os.getcwd(), "downloads")
    os.makedirs(downloads_dir, exist_ok=True)
    cmd = [bbdown_path, url, '--work-dir', downloads_dir]
    result = subprocess.run(cmd, capture_output=True, text=True)
```

url 来源于用户在 Tab1 页面输入框填入的内容。虽然 BBDown 本身对非 B 站链接会报错退出，但不校验就执行命令本身是不安全的做法。

上游调用方（`views/tab1_build.py`）已有 `try/except Exception` 包裹，校验失败抛 `ValueError` 即可被捕获并显示 `st.error()`。

## Goals / Non-Goals

**Goals:**
- 在命令执行前拦截非法 URL
- 覆盖 `bilibili.com` 和 `b23.tv` 两个域名及其子域名（如 `www.bilibili.com`、`api.bilibili.com`、`b23.tv/xxx`）
- 零新增依赖
- 不改变函数签名

**Non-Goals:**
- 不校验 URL 路径/参数格式（BBDown 自行处理）
- 不校验协议（http/https 都允许，BBDown 兼容）
- 不修改任何其他文件

## Decisions

### 校验方式：`urllib.parse.urlparse` 解析域名

使用标准库 `urllib.parse.urlparse` 提取 `netloc`，与白名单集合比对。

```python
from urllib.parse import urlparse

_ALLOWED_DOMAINS = {'bilibili.com', 'b23.tv'}

parsed = urlparse(url)
domain = parsed.netloc.lower()
# 去掉 www. 前缀，提取主域名
if domain.startswith('www.'):
    domain = domain[4:]
if domain not in _ALLOWED_DOMAINS:
    raise ValueError(f"不支持的链接：{url}。仅支持 bilibili.com 和 b23.tv 的链接。")
```

**为什么不直接用正则？** 标准库的 URL 解析比手写正则更鲁棒，能正确处理带端口、路径参数、query string 的 URL。

**为什么不写在 UI 层？** 验证逻辑应靠近安全边界（函数入口），而不是分散在 UI 中。这样无论以后 `download_bilibili_video` 被谁调用，都能享受到同样的保护。

## Risks / Trade-offs

- **[极低] urlparse 对某些畸形 URL 可能解析不准确**：比如用户输入 `bilibili.com.evil.cn`，`urlparse` 的 `netloc` 是 `bilibili.com.evil.cn`，取主域名后是 `evil.cn`，不会被白名单放过。正确拦截。
- **[极低] IP 地址直连 URL**：比如用户输入 `http://123.123.123.123/somevideo`，不会通过白名单校验，会被拒绝。这是期望行为——B 站视频应通过域名访问。
