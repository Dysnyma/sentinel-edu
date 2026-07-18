## Why

`core/database.py:37` 在 `init_db()` 中使用 f-string 拼接列名来构建 SQL 查询。尽管当前列名来自代码内的硬编码列表，这种写法在语法层面就是 SQL 注入的入口——一旦后续有人将外部输入传入这个拼接点，就可能导致数据泄露或破坏。同时，bandit 安全扫描将此处标记为 **Medium 风险**。修掉它，让代码安全扫描报告清零这个风险项。

## What Changes

- `core/database.py` `init_db()` 函数中，将 `c.execute(f"SELECT {col} FROM results LIMIT 1")` 改为使用参数化查询，或改用白名单校验后拼接
- 不修改任何查询逻辑和返回结果
- 不修改其他模块

## Capabilities

### New Capabilities
- `safe-sql-query`: 数据库查询统一使用参数化绑定或白名单校验，避免字符串拼接

### Modified Capabilities
<!-- No existing specs to modify — this is purely a code-level safety fix -->

## Impact

- **修改范围**：仅 `core/database.py` 中的 `init_db()` 函数，影响第 37 行那一处
- **对外接口**：无变化（`init_db()` 签名不变，行为不变）
- **依赖**：无新增
