# Sentinel-Edu — 课堂思政元素安全性分析原型系统

面向高校思政课堂教学内容的安全检测与红队测试工具。通过 **DFA 关键词扫描 + LLM 语义分析**双重防线，检测文本中是否存在显性敏感词、隐性价值观偏颇及不当比喻。支持音视频转写、测试集自动投毒、可视化分析和自学习词库扩充。

## 系统架构

```
输入（音视频/文本） → ASR转录 → 文本纠错 → 投毒生成 → 双重检测 → 可视化分析
                                              ↓
                                    自学习反馈 → DFA词库扩充
```

### 双重防线

| 防线 | 技术 | 职责 |
|------|------|------|
| 一防 DFA | AC 自动机 + 拼音归一化 + 形近字映射 + 模糊兜底 | 毫秒级拦截显性敏感词 |
| 二防 LLM | 大模型语义分析 | 识别隐性偏颇、不当比喻、历史虚无主义 |

## 快速开始

### 环境要求

- Python 3.10+
- FFmpeg（音视频处理）
- [BBDown](https://github.com/nilaoda/BBDown)（可选，B 站视频下载）

### 安装

```bash
git clone git@github.com:Dysnyma/sentinel-edu.git
cd sentinel-edu
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 启动

```bash
streamlit run app.py
```

浏览器访问 `http://localhost:8501`。

## 功能模块

### 📦 测试集构建（Tab 1）

- 支持上传音视频文件、B 站视频链接、直接输入文本
- 本地 Whisper 语音转写，含百分比进度条
- 可选大模型文本纠错
- 自动投毒生成：显性违规 / 隐性偏颇 / 不当比喻三种策略
- 输出 JSONL 格式测试集

### 🔍 安全检测（Tab 2）

- 加载 JSONL 测试集，自动运行双重检测
- DFA 全量扫描 + LLM 并发检测
- 三级状态标识（命中/安全/未检测）
- 样本深度对比：原文 / DFA / LLM 三栏高亮
- CSV 导出检测结果

### 📊 可视化分析（Tab 3）

- 混淆矩阵指标：准确率、召回率、精确率、F1、漏报率、误报率
- 标签分布饼图 + 拦截数量柱状图
- 多数据集切换分析
- Excel 导出

### 🧠 自学习优化（Tab 4）

- 自动收集 LLM 检出但 DFA 漏报的记录
- jieba 分词 → TF-IDF 评分 → 模糊去重管道
- 人工审核候选词，一键追加到敏感词库

## 项目结构

```
sentinel-edu/
├── app.py                  # Streamlit 主入口
├── requirements.txt        # Python 依赖
├── sensitive_words.txt     # DFA 敏感词库（一行一词）
├── core/
│   ├── asr.py              # Whisper 语音识别（本地 + API）
│   ├── config.py           # 配置管理 + 会话状态持久化
│   ├── database.py         # SQLite 数据层
│   ├── dfa_scanner.py      # DFA 扫描器（AC 自动机 + 反混淆）
│   ├── llm_scanner.py      # LLM 安全扫描器
│   ├── poison_generator.py # 红队投毒生成器
│   ├── self_learner.py     # 自学习模块
│   ├── text_correction.py  # ASR 后文本纠错
│   └── utils.py            # JSONL 工具 + 数据集管理
├── views/
│   ├── helpers.py          # 共享 UI 辅助函数
│   ├── tab1_build.py       # 测试集构建界面
│   ├── tab2_detect.py      # 安全检测界面
│   ├── tab3_analysis.py    # 可视化分析界面
│   └── tab4_learn.py       # 自学习优化界面
├── data/                   # 运行时数据（自动生成）
│   ├── apiconfig.json      # API 配置
│   ├── session_state.json  # 会话状态持久化
│   ├── scan_results.db     # SQLite 检测结果
│   ├── *.jsonl             # 测试集文件
│   └── datasets/           # 已保存的数据集
├── downloads/              # 临时音视频文件
└── 技术方案.md             # 详细技术文档
```

## 技术栈

| 维度 | 技术 |
|------|------|
| 框架 | Streamlit |
| 语音识别 | openai-whisper（本地）+ OpenAI API（云端） |
| 关键词匹配 | pyahocorasick（AC 自动机）+ rapidfuzz（模糊匹配） |
| 中文处理 | pypinyin（拼音归一化）+ jieba（分词） |
| 语义分析 | OpenAI 兼容 API（支持 DeepSeek / Kimi / 硅基流动等） |
| 数据存储 | SQLite + JSONL |
| 可视化 | Plotly + Pandas |
| 数据校验 | Pydantic |
| 导出 | openpyxl（Excel） |

## 许可

MIT License
