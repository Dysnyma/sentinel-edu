## 1. Core Fix: Add URL domain whitelist validation

- [x] 1.1 Add `from urllib.parse import urlparse` to imports in `core/asr.py`
- [x] 1.2 In `download_bilibili_video()`, before the BBDown subprocess call, add URL parsing and domain whitelist check — reject with `ValueError` if domain is not `bilibili.com` or `b23.tv`

## 2. Verification

- [x] 2.1 Run `bandit -r core/asr.py` and confirm the BBDown-related B603 warning is suppressed
- [x] 2.2 Manual test: valid `bilibili.com` URL should pass through normally
- [x] 2.3 Manual test: valid `b23.tv` URL should pass through normally
- [x] 2.4 Manual test: invalid domain (e.g. `example.com`) should raise `ValueError` with friendly message
