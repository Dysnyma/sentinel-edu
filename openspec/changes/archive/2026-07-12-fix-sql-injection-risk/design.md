## Context

`database.py:init_db()` 中有一段代码，用于给旧数据库表补充缺失的列（兼容性迁移）：

```python
for col, col_type in [
    ('llm_spans', 'TEXT'), ('llm_reason', 'TEXT'),
    ('dataset_id', 'TEXT'), ('text', 'TEXT'),
]:
    try:
        c.execute(f"SELECT {col} FROM results LIMIT 1")
    except sqlite3.OperationalError:
        c.execute(f"ALTER TABLE results ADD COLUMN {col} {col_type}")
```

`col` 虽然来自硬编码列表，但 f-string 拼接 SQL 的写法本身不安全，被 bandit 标记为 B608 (Medium)。

## Goals / Non-Goals

**Goals:**
- 消除 bandit B608 风险标记
- 保持与原代码完全相同的逻辑和返回值
- 零新增依赖

**Non-Goals:**
- 不修改其他 SQL 查询（它们已使用参数化绑定）
- 不重构 `init_db()` 的整体逻辑
- 不引入额外的列名校验库

## Decisions

### 方案对比

| 方案 | 做法 | 优点 | 缺点 |
|------|------|------|------|
| A（推荐） | 白名单集合校验 | 不改 SQL 结构，性能零开销 | 需维护列名白名单 |
| B | 改成参数化 `?` | SQL 注入免疫 | SQLite 的 `SELECT ? FROM` 绑定的值不是列名而是字面量，`SELECT 'llm_spans' FROM results` 返回的是常量字符串而非列值，逻辑错误 |
| C | 用 `PRAGMA table_info` 替代 | 完全避免拼接 | 多一次查询，代码增加约 5 行，有点过度设计 |

**结论：方案 A**。列名集合本身已经存在（就是 for 循环里的列表），只需在拼接前加一层校验。

```python
ALLOWED_COLUMNS = {'llm_spans', 'llm_reason', 'dataset_id', 'text'}
if col not in ALLOWED_COLUMNS:
    raise ValueError(f"Unexpected column: {col}")
c.execute(f"SELECT {col} FROM results LIMIT 1")
```

这样 bandit 不会再报警（因为列名经过了显式校验），而逻辑上完全等价——能走到拼接的列名只可能是白名单内预先批准的值。

## Risks / Trade-offs

- **[极低] 白名单与实际的列名列表需要同步维护**：当前列名列表在 for 循环中定义，作为白名单集合再写一遍，存在两份数据源。解决方案：将白名单提取为模块级常量，for 循环遍历它即可，避免两份。
