# 提示词编辑器 UI

## ADDED Requirements

### Requirement: 运行时编辑界面
系统 SHALL 在侧边栏高级配置区域提供可折叠的提示词编辑器。

- 编辑器默认收起，展开后显示三个 `st.text_area` 组件，分别对应扫描、投毒、纠错提示词。
- 每个 text_area 高度为 200px，带清晰的标签说明。
- 底部提供"恢复默认"和"保存并应用"两个按钮。
- 保存后将新提示词持久化到 `data/prompts.json` 并立即生效。

#### Scenario: 用户编辑提示词
- **WHEN** 用户展开"提示词编辑"区域，修改 SCAN_PROMPT 后点击"保存并应用"
- **THEN** 新的提示词被写入 `data/prompts.json`
- **THEN** 下一次 LLM 扫描使用新的提示词

#### Scenario: 恢复默认
- **WHEN** 用户点击"恢复默认"
- **THEN** 三个 text_area 被填充为内置默认值
- **THEN** 默认值被写入文件并生效
