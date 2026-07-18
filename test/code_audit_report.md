# Sentinel-Edu 代码体检报告

> 自动生成时间：2026-07-12 19:07:17
> 扫描范围：core/、views/、app.py、全部依赖

---

## 一、语法与规范检查（flake8）

### 扫描命令
```bash
flake8 core/ views/ app.py --max-line-length=120 --ignore=E501,W503
```

### 问题清单
```
app.py:5:1: F401 'pathlib.Path' imported but unused
core/asr.py:4:1: F401 'tempfile' imported but unused
core/asr.py:6:1: F401 'shutil' imported but unused
core/text_correction.py:2:1: F401 're' imported but unused
views/__init__.py:2:1: F401 'views.helpers.highlight_toxic' imported but unused
views/__init__.py:2:1: F401 'views.helpers.context_snippet' imported but unused
views/__init__.py:2:1: F401 'views.helpers.strategy_to_color' imported but unused
views/__init__.py:2:1: F401 'views.helpers.safe_json_loads' imported but unused
views/__init__.py:2:1: F401 'views.helpers.to_native' imported but unused
views/__init__.py:2:1: F401 'views.helpers.check_api_connection' imported but unused
views/__init__.py:2:1: F401 'views.helpers.run_concurrently' imported but unused
views/__init__.py:6:1: F401 'views.tab1_build.render_tab1' imported but unused
views/__init__.py:7:1: F401 'views.tab2_detect.render_tab2' imported but unused
views/__init__.py:8:1: F401 'views.tab3_analysis.render_tab3' imported but unused
views/helpers.py:103:5: F401 'pandas as pd' imported but unused
views/tab1_build.py:68:25: E306 expected 1 blank line before a nested definition, found 0
views/tab1_build.py:69:77: E226 missing whitespace around arithmetic operator
views/tab1_build.py:130:33: E306 expected 1 blank line before a nested definition, found 0
views/tab1_build.py:131:85: E226 missing whitespace around arithmetic operator
views/tab1_build.py:193:39: E226 missing whitespace around arithmetic operator
views/tab1_build.py:307:46: E226 missing whitespace around arithmetic operator
views/tab2_detect.py:5:1: F401 'pandas as pd' imported but unused
views/tab2_detect.py:10:1: F401 'core.database.get_results_by_dataset' imported but unused
views/tab2_detect.py:55:40: E226 missing whitespace around arithmetic operator
views/tab2_detect.py:311:39: E741 ambiguous variable name 'l'
views/tab2_detect.py:311:73: E741 ambiguous variable name 'l'
views/tab2_detect.py:347:21: F841 local variable 'llm_time' is assigned to but never used
views/tab2_detect.py:481:24: E128 continuation line under-indented for visual indent
views/tab2_detect.py:515:68: E231 missing whitespace after ','
views/tab3_analysis.py:7:1: F401 'plotly.subplots.make_subplots' imported but unused
views/tab3_analysis.py:10:1: F401 'json' imported but unused
views/tab3_analysis.py:275:64: E231 missing whitespace after ','
```

**问题总数：32 个**

> ⚠️ 存在代码规范/潜在语法问题，建议逐条查看

---

## 二、安全风险检查（bandit）

### 扫描命令
```bash
bandit -r core/ views/ app.py
```

### 问题清单
```
[main]	INFO	profile include tests: None
[main]	INFO	profile exclude tests: None
[main]	INFO	cli include tests: None
[main]	INFO	cli exclude tests: None
[main]	INFO	running on Python 3.12.3
[manager]	WARNING	Test in comment: url is not a test name or id, ignoring
[manager]	WARNING	Test in comment: col is not a test name or id, ignoring
Run started:2026-07-12 11:07:18.568532+00:00

Test results:
>> Issue: [B404:blacklist] Consider possible security implications associated with the subprocess module.
   Severity: Low   Confidence: High
   CWE: CWE-78 (https://cwe.mitre.org/data/definitions/78.html)
   More Info: https://bandit.readthedocs.io/en/1.9.4/blacklists/blacklist_imports.html#b404-import-subprocess
   Location: core/asr.py:3:0
2	import whisper
3	import subprocess
4	import tempfile

--------------------------------------------------
>> Issue: [B603:subprocess_without_shell_equals_true] subprocess call - check for execution of untrusted input.
   Severity: Low   Confidence: High
   CWE: CWE-78 (https://cwe.mitre.org/data/definitions/78.html)
   More Info: https://bandit.readthedocs.io/en/1.9.4/plugins/b603_subprocess_without_shell_equals_true.html
   Location: core/asr.py:141:13
140	           'pcm_s16le', '-ar', '16000', '-ac', '1', audio_path, '-y']
141	    result = subprocess.run(cmd, capture_output=True, text=True)
142	    if result.returncode != 0:

--------------------------------------------------
>> Issue: [B311:blacklist] Standard pseudo-random generators are not suitable for security/cryptographic purposes.
   Severity: Low   Confidence: High
   CWE: CWE-330 (https://cwe.mitre.org/data/definitions/330.html)
   More Info: https://bandit.readthedocs.io/en/1.9.4/blacklists/blacklist_calls.html#b311-random
   Location: views/tab1_build.py:225:23
224	            poison_count = max(1, int(total * poison_ratio))
225	            selected = random.sample(clean_data, poison_count)
226	

--------------------------------------------------

Code scanned:
	Total lines of code: 2191
	Total lines skipped (#nosec): 2
	Total potential issues skipped due to specifically being disabled (e.g., #nosec BXXX): 0

Run metrics:
	Total issues (by severity):
		Undefined: 0
		Low: 3
		Medium: 0
		High: 0
	Total issues (by confidence):
		Undefined: 0
		Low: 0
		Medium: 0
		High: 3
Files skipped (0):
```

---

## 三、第三方依赖漏洞（pip-audit）

### 扫描命令
```bash
pip-audit
```

### 漏洞清单
```
Found 1 known vulnerability in 1 package
Name  Version ID            Fix Versions
----- ------- ------------- ------------
torch 2.11.0  CVE-2025-3000
```

---

## 四、说明

1. **flake8**：检查语法错误、未使用变量、导入冗余、代码风格等显性问题
2. **bandit**：检查安全漏洞，如明文密钥、命令注入、危险函数调用等
3. **pip-audit**：检查第三方依赖库的已知安全漏洞

### 修复建议优先级
- 🔴 **High / 高危**：立即修复
- 🟡 **Medium / 中危**：建议修复
- 🟢 **Low / 低危**：按需修复
- ⚪ 格式规范类：不影响运行，可统一整理时修复

