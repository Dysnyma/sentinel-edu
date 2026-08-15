## Context

当前 `BaseLLMClient` 实例在每个业务函数调用中重建：

```python
# llm_scanner.py
client = BaseLLMClient(api_key, base_url, model)

# poison_generator.py
client = BaseLLMClient(api_key, base_url, model)

# text_correction.py
client = BaseLLMClient(api_key, base_url, model)
```

每次构造都会创建一个新的 `openai.OpenAI` 客户端，而该客户端内部初始化了一个 `httpx.Client` 连接池。频繁新建导致：
- TCP 连接无法复用（每个新客户端通过 HTTP 的 `Connection: keep-alive` 建立的连接在客户端销毁后关闭）
- 并发批量扫描时 TIME_WAIT 端口堆积
- 不必要的 SSL 握手开销

## Goals / Non-Goals

**Goals：**
- 相同 `(api_key, base_url)` 配置复用同一个 `BaseLLMClient` 实例，共享底层 HTTP 连接池
- 线程安全，适配 `ThreadPoolExecutor` 并发场景
- 保留 `__init__` 兼容性，不破坏已有直接实例化的代码
- 不同密钥/地址的客户端互不污染

**Non-Goals：**
- 不改变业务函数签名或行为
- 不引入第三方缓存库
- 不做客户端清理/过期机制（客户端是轻量级的资源包装，进程生命周期内常驻无害）

## Decisions

### 决策 1：类级别 `dict` 缓存 vs 模块级别 `functools.lru_cache`

| 方案 | 评价 |
|---|---|
| **类级别 `dict` + `Lock`（选定）** | 简单明确，缓存逻辑与 `BaseLLMClient` 类绑定，不污染模块命名空间。`threading.Lock` 保证首次同时调用时不会重复创建 |
| `functools.lru_cache` 装饰工厂函数 | 需要额外包装函数，且无法直接处理 `threading` 锁控制；`model` 参数变化时缓存键需特别处理 |
| 模块级全局 `dict` | 功能等价但组织性较差，缓存职责应由 `BaseLLMClient` 自身管理 |

### 决策 2：缓存键设计

```
(api_key, base_url) → BaseLLMClient 实例
```

- **`api_key` 和 `base_url` 为键**：因为底层 `openai.OpenAI` 连接的远端由 `base_url` 决定，鉴权由 `api_key` 决定；`model` 只是请求参数，不影响连接
- **不包含 `model`**：同一个服务地址的不同模型共享连接池（HTTP 连接与模型无关），避免因 `model` 不同而创建冗余客户端

### 决策 3：线程安全实现

使用 `threading.Lock` 保护缓存的读写。采用 double-check locking 模式：

```python
@classmethod
def get_instance(cls, api_key, base_url, model):
    key = (api_key, base_url)
    if key not in cls._instance_cache:      # 第一次检查（无锁）
        with cls._lock:                      # 加锁
            if key not in cls._instance_cache:  # 第二次检查（有锁）
                cls._instance_cache[key] = cls(api_key, base_url, model)
    return cls._instance_cache[key]
```

此模式避免每次调用都获取锁的开销，同时保证首次并发创建时的线程安全。

### 决策 4：缓存可见性

`_instance_cache` 和 `_lock` 使用前导下划线(`_`)表示保护成员，不暴露给外部调用者。`get_instance` 是唯一的公开工厂入口。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|---|---|
| 缓存中的客户端在进程生命周期内永不释放，长期运行的进程可能持有已过期的 API 密钥连接 | 密钥变更通常伴随进程重启（环境变量重载）。必要时可在 `get_instance` 上增加 `force_refresh` 参数 |
| 多线程下 `key not in dict` + `dict[key] = ...` 非原子操作 | `threading.Lock` 保证线程安全 |
| 极端并发下锁竞争 | 仅在首次未命中时加锁，命中后直接返回，无锁路径无竞争 |
| `model` 不在缓存键内，不同模型使用相同客户端 | `model` 通过 `self.model` 实例属性存储，不影响连接池复用；HTTP 连接层面的复用是正确的 |
