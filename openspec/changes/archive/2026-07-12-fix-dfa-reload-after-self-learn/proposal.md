## Why

用户在自学习页面（Tab4）追加候选敏感词到词库后，DFA Scanner 不会自动重载新词——必须重启整个 Streamlit 应用才能让新词在一防扫描中生效。这导致自学习反馈闭环在最后一公里断裂，用户无法立即验证新词的效果。

## What Changes

- `core/self_learner.py`：`apply_selected()` 追加词库后，自动触发 `DFAScanner.reload()`，使新词立即生效
- `views/tab4_learn.py`：追加成功后，向用户展示轻量提示"词库已重载生效"
- 不修改 `DFAScanner` 现有公开接口（`reload()` 方法已存在，无需改动）
- 不新增 UI 元素，不改变现有页面交互流程

## Capabilities

### New Capabilities
- `dfa-reload-on-lexicon-update`: DFA Scanner 在敏感词库文件变更后自动重载，无需重启应用

### Modified Capabilities
<!-- No existing specs to modify -->

## Impact

- `core/self_learner.py` — `apply_selected()` 函数增加重载 DFA Scanner 的逻辑
- `views/tab4_learn.py` — 追加成功后显示重载确认提示
- 不涉及 API 变更、不引入新依赖、不破坏现有文件结构
