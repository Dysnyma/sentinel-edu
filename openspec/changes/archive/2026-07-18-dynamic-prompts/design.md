## Context

三个提示词当前定义在各自的业务模块顶部作为模块级常量。每次更新提示词需要：修改 Python 文件 → 保存 → Streamlit 自动重载页面（或手动刷新）。对于需要反复调优的用户来说，这个流程效率低。且切换模型时理想的提示词不同，硬编码无法支持按模型保存多套提示词。

## Goals / Non-Goals

**Goals:**
- 提示词从代码中分离，持久化到 `data/prompts.json`
- 支持运行时编辑和即时生效（热重载）
- 提供默认值兜底：prompts.json 不存在时自动用代码中的默认值创建

**Non-Goals:**
- 不改变提示词本身的语义或行为
- 不做多模型提示词切换（仅提供编辑能力，用户手动切换）
- 不改动系统已有 API/ASR/DB 等配置

## Decisions

### 1. 存储格式

`data/prompts.json` 使用简单的 JSON 对象结构：

```json
{
  "scan_prompt": "...",
  "poison_prompt": "...",
  "correct_prompt": "..."
}
```

三个字段分别对应三个业务模块的提示词。每次用户保存时整个文件被覆写。

### 2. 加载策略

- `core/config.py` 新增 `load_prompts()`：读取 `data/prompts.json`，若文件不存在或字段缺失则返回内置默认值。
- `core/config.py` 新增 `save_prompts(scan, poison, correct)`：将三个提示词写入文件。
- 默认值直接从原有的三个常量中复制，确保行为等价。

### 3. 业务模块改造

每个业务文件的常量定义改为函数调用：

```python
# 之前（硬编码）
SCAN_PROMPT = """你是一个严格的教学内容安全审核专家..."""

# 之后（动态加载）
from core.config import load_prompts
# 在函数内部调用 load_prompts() 获取最新提示词
# 仍然保留一个模块级默认值作为兜底
```

关键是 `load_prompts()` 在每次使用时重新读取文件——这意味着用户修改 prompts.json 后无需重启即可生效（Streamlit rerun 时会重新执行模块级代码）。

另一种方案是只在启动时加载一次并缓存到 session_state。用户编辑后通过 "保存并应用" 按钮写入文件并更新 session_state。

**选择**：采用 session_state 缓存方案。用户在 UI 中编辑后点击"保存"按钮→写入文件→更新 session_state→触发 UI 重新渲染。

### 4. UI 位置

在 `app.py` 侧边栏现有的"高级工具配置"展开区下方，新增一个"🤖 提示词编辑"展开区。每个提示词使用 `st.text_area` 组件（高度 200px），栏位清晰标注用途。底部有"恢复默认"和"保存"按钮。

### 5. 向后兼容

- 旧版本代码没有 `data/prompts.json`：首次调用 `load_prompts()` 时自动创建并用默认值填充。
- 旧版本代码升级后：三个模块的函数自动使用默认值，行为完全等价。

## Risks / Trade-offs

- 【风险】大段文本在 st.text_area 中可能影响侧边栏布局 → 使用展开区折叠，默认收起；每条提示词使用单独区域
- 【风险】用户修改了无效提示词导致 API 调用失败 → "恢复默认"按钮一键还原；保存时不做语义校验（由用户自行在对话中测试）
