## 1. 新增 `BaseLLMClient` 类级别缓存与工厂方法

- [x] 1.1 在 `BaseLLMClient` 中新增 `_instance_cache: dict` 类属性和 `_lock: threading.Lock` 
- [x] 1.2 新增 `@classmethod get_instance(api_key, base_url, model)` 工厂方法，实现 double-check locking 缓存逻辑

## 2. 替换业务函数中的实例化方式

- [x] 2.1 `core/llm_scanner.py`: 将 `BaseLLMClient(api_key, base_url, model)` 改为 `BaseLLMClient.get_instance(api_key, base_url, model)`
- [x] 2.2 `core/poison_generator.py`: 同上
- [x] 2.3 `core/text_correction.py`: 同上

## 3. 验证

- [x] 3.1 运行现有单元测试，确认全部通过
- [x] 3.2 确认缓存命中：构造两个相同 `(api_key, base_url)` 的客户端，验证为同一实例
