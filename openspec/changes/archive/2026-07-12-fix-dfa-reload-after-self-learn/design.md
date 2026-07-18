## Context

当前自学习流程（Tab4）中，用户审核并追加候选敏感词到 `sensitive_words.txt` 后，DFA Scanner 的内存自动机不会感知到文件变更。虽然 Streamlit 的每次 rerun 都会重建对象（新 DFAScanner 实例会读取最新文件），但为确保确定性行为并在未来可能的 singleton 模式下保持正确性，需要在词库写入后显式触发 `DFAScanner.reload()`。

`DFAScanner.reload()` 方法已存在（`dfa_scanner.py:90-96`），无需修改。

## Goals / Non-Goals

**Goals:**
- 用户点击"追加到敏感词库"后，DFA Scanner 立即加载新词
- 追加成功后展示轻量确认提示"词库已重载生效"
- 零新增依赖，零接口变更

**Non-Goals:**
- 不修改 `dfa_scanner.py` 的任何代码
- 不修改 `self_learner.py` 的函数签名（保持 `apply_selected` 的文件写入语义不变）
- 不增加新的 UI 控件
- 不引入 Scanner 全局单例

## Decisions

### 决策 1：重载触发点放在 view 层（tab4_learn.py）

在 `apply_selected()` 调用后，由 `tab4_learn.py` 创建临时 DFAScanner 实例并调用 `reload()`。

**为什么不是放在 `self_learner.apply_selected()` 内部？**

- `self_learner.py` 的职责是"从 DB 提取 → 分词 → 评分 → 写入文件"，不涉及 Scanner 生命周期管理
- 放入 `apply_selected()` 会使 `self_learner.py` 产生对 `dfa_scanner.py` 的导入依赖，增加模块耦合
- View 层（`tab4_learn.py`）是工作流编排者，负责协调 self_learner 和 dfa_scanner 的交互，符合单一职责原则

**为什么是创建新实例而非复用全局 Scanner？**

- 当前架构中不存在 Scanner 全局单例（Tab2 每次扫描创建局部实例）
- Streamlit 每次 rerun 都重新执行脚本，旧实例已被 GC
- 创建新实例调用 `reload()` 的开销可以忽略（仅读取 112 行文件 + 构建自动机）

### 决策 2：仅在新增词 > 0 时重载

`apply_selected()` 返回 `(added_count, new_words)`，当 `added_count == 0`（所有候选词已存在）时，文件未变更，跳过重载。避免无效操作。

## Risks / Trade-offs

- **[Low] 创建临时 DFAScanner 仅为了 reload** → 开销可忽略（<10ms），但如果未来词库增长到数万条，可考虑改成静态方法。当前 112 词不必过度设计。
- **[Low] Streamlit rerun 行为变化** → 如果未来 Streamlit 版本改变对象生命周期模型（如引入 session-scoped cache），当前显式 reload 可保证正确性。
