## 1. Core Fix: Trigger DFA reload after word list update

- [x] 1.1 In `views/tab4_learn.py`, after `apply_selected()` returns `added_count > 0`, create a `DFAScanner` instance and call `reload()` to load the updated word list into memory
- [x] 1.2 Update the success message from "已添加 N 个新词到 sensitive_words.txt" to include "词库已重载生效" confirmation

## 2. Verification

- [x] 2.1 Verify `DFAScanner` is already imported in `tab4_learn.py` (line 8: `from core.dfa_scanner import DFAScanner`) — no new import needed
- [x] 2.2 Verify that when `added_count == 0` (all words already in word list), no reload is triggered
- [x] 2.3 Verify that the existing session state cleanup logic (lines 103-105) is not affected by the change
