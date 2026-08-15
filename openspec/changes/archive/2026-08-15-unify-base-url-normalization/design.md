## Context

Base URL 标准化逻辑负责将用户输入的 API 地址统一格式，确保 `/v1` 后缀存在。当前三处重复实现，模式完全一致：

```python
base_url = base_url.strip().rstrip('/')
if not base_url.endswith('/v1'):
    base_url += '/v1'
```

差异点仅在 `app.py` 版本中多了空值保护（`if base_url and ...`），而 `llm_client.py` 和 `helpers.py` 版本在空字符串时也会执行，但行为等价（空串 `strip().rstrip('/')` 仍为空串，`endswith('/v1')` 为 False，追加 `/v1` 得到 `/v1`——不过实际调用中空串场景不会发生，因为调用方保证 `base_url` 非空）。

## Goals / Non-Goals

**Goals：**
- 将标准化逻辑收敛到 `core/config.py` 中唯一的 `normalize_base_url` 函数
- 三处调用点全部改用该函数
- 行为与修改前完全一致

**Non-Goals：**
- 不改变标准化规则本身
- 不修改配置文件字段名、持久化逻辑或 UI
- 不引入新依赖

## Decisions

### 决策 1：函数放置位置

| 方案 | 评价 |
|---|---|
| **`core/config.py`（选定）** | 配置层已有 `load_prompts`、`get_presets` 等工具函数，且 `normalize_base_url` 本质是对配置值（base_url）的预处理，职责归属清晰 |
| `core/utils.py` | 需新建文件，引入额外模块结构变化 |
| `core/llm_client.py` | 虽然客户端使用但函数本身无 LLM 依赖，放这里语义不纯 |

### 决策 2：空值处理

`app.py` 版本有 `if base_url and` 的空值保护，而其他两处没有。统一函数按**最安全版本**实现：如果输入为空字符串或仅空白字符，直接返回空串，不做 `/v1` 补全。

```python
def normalize_base_url(url: str) -> str:
    url = url.strip().rstrip('/')
    if not url:
        return ''
    if not url.endswith('/v1'):
        url += '/v1'
    return url
```

此行为覆盖了三处既有逻辑的全部场景——因为实际调用中空串补 `/v1` 不会发生（调用方保证非空），而统一函数的空值保护是安全的防御性编程。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|---|---|
| `app.py` 的 `if base_url and` 保护被统一函数处理，行为等价 | 统一函数同样包含空值保护，行为一致 |
| `llm_client.py` 中 `__init__` 的参数 `base_url` 可能是空串 | 实际不会出现（调用方从配置读取），且统一函数返回空串后，`openai.OpenAI(base_url='')` 会失败——与修改前行为相同 |
| 新增函数需 import | `core/config.py` 可被其他模块 import，新增 `from core.config import normalize_base_url` 即可 |
