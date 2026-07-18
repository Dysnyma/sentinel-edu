## 1. Remove Unused Imports (F401)

- [x] 1.1 `app.py:5` — delete `from pathlib import Path`
- [x] 1.2 `core/asr.py:4,6` — delete `import tempfile` and `import shutil`
- [x] 1.3 `core/text_correction.py:2` — delete `import re`
- [x] 1.4 `views/helpers.py:103` — delete `import pandas as pd`
- [x] 1.5 `views/tab2_detect.py:5,10` — delete `import pandas as pd` and `get_results_by_dataset` import
- [x] 1.6 `views/tab3_analysis.py:7,10` — delete `make_subplots` import and `import json`

## 2. Remove Unused Variable (F841)

- [x] 2.1 `views/tab2_detect.py:347` — delete `llm_time = result.get('time_cost', 0)`
- [x] 2.2 `views/tab2_detect.py:339` — remove `llm_time` from tuple unpacking (second occurrence)

## 3. Fix Ambiguous Variable Name (E741)

- [x] 3.1 `views/tab2_detect.py:311` — rename `l` to `span` in the generator expression

## 4. Fix Whitespace and Formatting

- [x] 4.1 `views/tab1_build.py:68,130` — add blank line before nested `def`
- [x] 4.2 `views/tab1_build.py:69,131,193,307` — add spaces around `*` and `+` operators
- [x] 4.3 `views/tab2_detect.py:55` — add space around `+` operator
- [x] 4.4 `views/tab2_detect.py:481` — fix E128/E127 continuation line indentation
- [x] 4.5 `views/tab2_detect.py:515` and `views/tab3_analysis.py:275` — add space after `','`

## 5. Verification

- [x] 5.1 Run `flake8 --max-line-length=120 --ignore=E501,W503` on all changed files and confirm zero issues
- [x] 5.2 Run `git diff --stat` to review the scope of changes
