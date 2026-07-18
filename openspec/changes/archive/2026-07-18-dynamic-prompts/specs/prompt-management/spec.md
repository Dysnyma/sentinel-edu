# 提示词管理

## ADDED Requirements

### Requirement: 持久化存储
系统 SHALL 将三个核心提示词存储在 `data/prompts.json` 文件中。

- 文件格式：JSON 对象，包含 `scan_prompt`、`poison_prompt`、`correct_prompt` 三个字符串字段。
- 文件不存在时，系统 SHALL 自动使用内置默认值创建并写入文件。
- 文件损坏或字段缺失时，系统 SHALL 使用内置默认值兜底。

### Requirement: 动态加载
系统 SHALL 提供 `load_prompts()` 函数，返回包含三个提示词的字典。

- 每次调用都从文件重新读取（不缓存），确保热编辑即时生效。
- 若文件不存在或读取失败，返回内置默认值。
- 三个业务模块通过此函数获取提示词。

#### Scenario: 首次启动
- **WHEN** 系统中不存在 `data/prompts.json`
- **THEN** `load_prompts()` 返回内置默认值
- **THEN** 自动创建 `data/prompts.json` 并写入默认提示词

#### Scenario: 正常读取
- **WHEN** `data/prompts.json` 存在且格式正确
- **THEN** `load_prompts()` 返回文件中的提示词

### Requirement: 保存提示词
系统 SHALL 提供 `save_prompts(scan_prompt, poison_prompt, correct_prompt)` 函数，将三个提示词持久化到文件。

#### Scenario: 保存后立即生效
- **WHEN** 用户通过 UI 修改并保存提示词
- **THEN** `save_prompts()` 写入文件
- **THEN** 下次调用 `load_prompts()` 时返回新值
