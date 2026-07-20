# Gemini，请协助 sentinel-edu 项目

你好 Gemini。我们正在共同开发一个课堂思政内容安全分析系统（sentinel-edu），你是协作 AI，我是 Claude。我负责架构设计和核心重构，你负责专项分析和补充测试。

## 项目上下文

这是一个 Streamlit 应用，通过 DFA + LLM 双防线检测教学内容中的安全隐患。当前已完成全站 MVC 解耦（core/ 为纯业务，views/ 为纯 UI），37 个 pytest 测试，代码库约 4000 行。

详细的项目结构、重构历史和 API 备忘录见下方。**请先读完 all_py_code.txt（根目录下的合并文件，含所有 Python 源码）**，再开始工作。

## 任务一：为 core/dfa_scanner.py 编写专项单元测试

### 背景
`core/dfa_scanner.py`（约 210 行）实现了增强型 DFA 扫描器，核心能力：
- AC 自动机关键词匹配
- 拼音归一化（`pypinyin`，将中文转拼音后再匹配，对抗同音字绕过）
- 形近字映射（如「辩→辨」「未→末」等 50+ 组映射）
- 分隔符剥离（对抗「资.本.主.义」类绕过）
- NFKC 归一化 + 零宽字符过滤
- 编辑距离模糊匹配兜底（`rapidfuzz`）
- 误报过滤（如「六四」在数字语境下放行）

### 要求
请为 `core/dfa_scanner.py` 设计 pytest 测试用例，直接输出可用的 Python 代码。

### 覆盖要求（按优先级排列）

1. **基础匹配**：单关键词命中、多关键词命中、大小写不敏感、全角/半角
2. **形近字绕过**：至少覆盖 5 组形近字映射（如「辩→辨」「未→末」「士→土」）
3. **分隔符绕过**：中间插入 `.`、空格、零宽字符等分隔符仍能命中
4. **拼音同音绕过**：用同音字替换关键词中的字（如「资本→滋本」），验证拼音自动机能命中
5. **模糊匹配**：轻微拼写错误（编辑距离 ≤2）时仍能命中
6. **误报过滤**：「六四」在数字序列中不命中，但在政治语境中命中
7. **空词表**：无敏感词时扫描任意文本返回 `(False, [])`
8. **reload()**：动态追加词表后重新扫描
9. **边界**：空文本、纯英文文本、超长文本（5000 字以上）

### 交付物
一个完整的测试文件 `tests/test_dfa_scanner.py`，约 50-80 行，可以直接放到项目中使用。代码风格与现有测试（`tests/test_llm_client.py`）保持一致。

### 注意事项
- 测试文件放在 `tests/` 目录下，命名 `test_dfa_scanner.py`
- 使用 pytest + `unittest.mock` 或 `pytest-mock`
- 不需要 mock `ahocorasick` 或 `pypinyin` 或 `rapidfuzz` 这些第三方库（它们在测试环境中可用）
- 但需要 mock 敏感词文件路径，避免依赖真实 `sensitive_words.txt`
- 每个测试函数用 docstring 说明场景
- 不需要 `DFAScanner` 的真实文件——用 `tmp_path` 创建临时词表即可

---

## 任务二：安全审计（代码审查）

### 背景
review `all_py_code.txt` 中的全部代码，重点检查以下类别的安全隐患。

### 检查项
- **命令注入**：`subprocess.run` 是否有 shell=True 或未转义的用户输入？（`asr.py`、`build_controller.py`）
- **SQL 注入**：`database.py` 中是否有拼接 SQL？（已有一层列名白名单，但检查是否有遗漏）
- **路径遍历**：文件路径是否使用了用户可控的输入而未做校验？
- **敏感信息泄露**：API Key 在日志、错误消息、前端中是否有泄露风险？
- **Prompt 注入**：用户输入的文本直接拼接到 LLM Prompt 中，是否有防御措施？（`llm_scanner.py`、`poison_generator.py`）
- **反序列化**：`json_repair.loads` 是否有安全问题？
- **竞态条件**：`run_concurrently` 中的线程安全问题
- **不安全的临时文件**：`tempfile.NamedTemporaryFile(delete=False)` 使用是否安全？

### 交付物
每个发现用以下格式输出：

```markdown
## [严重性: 高/中/低] 问题描述
- **文件**: `path/to/file.py:行号`
- **风险**: 具体攻击场景
- **建议**: 修复方案或代码片段
```

无发现问题也请明确说明「未发现安全隐患」。

---

## 任务三：对 tab4_learn.py 的解耦做方案设计（不写代码，只出设计）

### 背景
`views/tab4_learn.py`（约 110 行）是最后一个混合 UI 与业务逻辑的视图文件。我需要将它拆分为：
- `core/learn_controller.py`（纯业务函数）
- `views/tab4_learn.py`（仅 Streamlit 渲染）

### 需要你设计的
请阅读 `tab4_learn.py` 的代码（在 `all_py_code.txt` 中），然后给出一个提取方案，包括：

1. **应提取的函数清单**：每个函数的名称、输入参数、返回值类型、职责描述
2. **提取后的 `views/tab4_learn.py` 骨架**：仅 `st.xxx` 调用，数据全部来自 controller
3. **UI 职责与业务职责的明确边界线**

### 交付物
一个 markdown 格式的设计文档（约 200-400 字），不需要完整代码，清晰描述函数边界即可。

---

## 如何交付

每个任务完成后，直接输出到对话中：

1. **任务一**：输出 `tests/test_dfa_scanner.py` 的完整代码
2. **任务二**：输出安全审查报告
3. **任务三**：输出解耦设计方案

如果 Claude 对你的输出有疑问或需要修改，他会通过用户转达。不要生成无法运行的伪代码——如果有不确定的 API，请说明并在代码中标注 `# TODO: verify`。

---

## 项目结构参考（完整源码见 all_py_code.txt）

```
core/
├── analysis_controller.py  # 混淆矩阵/指标计算
├── asr.py                  # Whisper 语音识别
├── build_controller.py     # Tab1 业务逻辑
├── config.py               # 配置 + 提示词管理
├── database.py             # SQLite 操作
├── detect_controller.py    # Tab2 检测业务
├── dfa_scanner.py          # ★ 需要你写测试
├── llm_client.py           # BaseLLMClient
├── llm_scanner.py          # LLM 扫描
├── poison_generator.py     # 投毒生成
├── self_learner.py         # 自学习
├── text_correction.py      # 文本纠错
└── utils.py                # 工具函数
views/
├── tab1_build.py           # Mix of UI + ASR
├── tab2_detect.py          # Detection UI
├── tab3_analysis.py        # Analysis UI
├── tab4_learn.py           # ★ 需要你设计方案
└── helpers.py              # UI helpers
tests/
├── conftest.py             # Shared fixtures
├── test_llm_client.py      # 14 tests
├── test_utils.py           # 6 tests
├── test_views.py           # 7 tests
├── test_build_controller.py# 3 tests
└── test_detect_controller.py# 4 tests
```

---

## Claude 对你的交付物的审阅反馈

你的三个交付物我都仔细看了，整体质量很好。有几个点想跟你确认或补充：

### 关于 DFA 测试

`test_base_matching` 中有一个问题：

```python
def test_base_matching(self, scanner):
    scanner.automaton.add_word("badword", ...)
    scanner._words.append("badword")
    scanner.automaton.make_automaton()
```

这里直接操作了 `scanner` 内部的 automaton 和 `_words`，绕过了正常的 `_load()` 流程。而且这修改的是共享的 fixture 实例——后续测试看到的 automaton 状态会不一致（多了一个 "badword"）。

**建议改成**：把 "badword" 写到临时词表文件里，让 scanner 通过 reload() 正常加载。或者另起一个独立的 fixture 测试全角/半角场景。

你同意这个修改方向吗？还是你觉得当前方式有其他考量？

### 关于 XSS 修复

你建议的 `html.escape(text)` 方案我认可。但你提到 "toxic_spans 也需要 escape 再匹配"——这个细节我想听你展开说说。当前的 `highlight_toxic` 是先在原文中正则匹配 toxic_spans，再给匹配到的片段包 `<mark>` 标签。如果先 escape 再匹配，toxic_spans 也需要同步 escape 才能匹配上。但输入框中的恶意脚本通常不会是 toxic_spans 的一部分（正常使用场景中 toxic_spans 来自系统预设数据，而不是用户直接输入的）。所以这里是否有必要也 escape toxic_spans？

### 关于 tab4 解耦方案

方案整体可以直接落地。两个小建议：

1. **`fetch_missed_records`** 加一个 `limit: int = 50` 参数，控制单次处理的漏报数量上限，防止数据集过大时 UI 卡死。

2. **`commit_selected_words` 的返回值**：当前是 `tuple[int, list[str]]`，改成 dict 更便于后续扩展：
   ```python
   {"added_count": int, "new_words": list[str], "reload_success": bool}
   ```

你觉得这两个改动合理吗？

### 其他

你审阅代码时有没有发现其他值得注意但不属于安全漏洞的问题？比如代码异味（code smell）、可维护性问题、或者 Streamlit 使用上的常见坑？

