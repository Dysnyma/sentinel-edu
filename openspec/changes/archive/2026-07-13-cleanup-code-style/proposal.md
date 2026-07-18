## Why

当前代码存在 30+ 个 flake8 告警，分布在多个文件中。虽然每个告警都不影响功能，但累积在一起导致：
- 代码体检报告中有大量"杂音"，掩盖真正的安全风险
- 新接手的人看到导入了一堆没用的包、变量名用 `l` 等，产生困惑
- 格式不统一（空格、缩进）让代码看起来不够专业
- F841 赋值未使用表示有冗余计算

一次全面清理，让告警数归零，后续只关注新增的真正问题。

## What Changes

- 删除 7 处 F401 未使用的导入（保留 `views/__init__.py` 的聚合导出）
- 删除 1 处 F841 赋值但未使用的 `llm_time` 变量
- 修复 1 处 E741 歧义变量名 `l` → `span` 或 `s`
- 修复 E226 运算符空格 5 处、E306 嵌套函数前空行 2 处、E231 逗号后空格 2 处、E128 缩进 1 处

## Capabilities

### New Capabilities
- `code-cleanup`: 全项目代码冗余清理和格式统一

### Modified Capabilities
<!-- No existing specs to modify -->

## Impact

- **修改范围**：6 个文件，约 15 处修改
  - `app.py`：删除 1 个导入
  - `core/asr.py`：删除 2 个导入
  - `core/text_correction.py`：删除 1 个导入
  - `views/helpers.py`：删除 1 个导入
  - `views/tab1_build.py`：E306 ×2 + E226 ×4
  - `views/tab2_detect.py`：删除 F401 ×2 + 删除 F841 + E741 + E226 + E128 + E231
  - `views/tab3_analysis.py`：删除 F401 ×2 + E231
- **对外接口**：无任何变化
- **依赖**：无新增
