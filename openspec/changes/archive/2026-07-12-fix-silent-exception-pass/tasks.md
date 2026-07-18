## 1. Core Fix: Replace silent except:pass with visible warnings

- [x] 1.1 In `core/utils.py:61` — `save_dataset()`: change `except Exception: pass` to `print(f"[WARN] AI 标题生成失败: {e}")`
- [x] 1.2 In `core/utils.py:144` — `list_datasets()`: change `except Exception: pass` to `print(f"[WARN] 元数据文件解析失败 {meta_path}: {e}")`
- [x] 1.3 In `views/tab1_build.py:271` — AI title suggestion: change `except Exception: pass` to `st.warning("AI 标题建议失败，将使用默认名称")`
- [x] 1.4 In `views/tab2_detect.py:30` — DB init record: change `except Exception: pass` to `st.warning(f"样本 {rec['id']} 初始记录写入失败")`

## 2. Verification

- [x] 2.1 Run `flake8 core/utils.py views/tab1_build.py views/tab2_detect.py` to confirm no new lint issues
- [x] 2.2 Run bandit to confirm no B110 issues remain
- [x] 2.3 Manually verify each changed except block still catches and doesn't crash
