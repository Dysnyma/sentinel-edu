## 1. 创建 BaseLLMClient 基类

- [x] 1.1 新建 `core/llm_client.py`，实现 `BaseLLMClient.__init__`（URL 标准化、openai 客户端初始化）
- [x] 1.2 实现 `BaseLLMClient._call_api()`：带指数退避重试（3 次，捕获 `openai.APIError`）、异常上下文包装
- [x] 1.3 实现 `BaseLLMClient._extract_content()`：安全提取 `choices[0].message.content`，含 `model_dump()` 降级
- [x] 1.4 实现 `BaseLLMClient.call()`：公开方法，返回纯文本（含 Markdown 代码块清理）
- [x] 1.5 实现 `BaseLLMClient.call_and_parse()`：公开方法，返回 `json_repair.loads()` 后的 dict

## 2. 重构 llm_scanner.py

- [x] 2.1 移除 `llm_scanner.py` 中的 URL 标准化、重试、响应提取、json_repair 解析等重复代码
- [x] 2.2 改用 `BaseLLMClient.call_and_parse()` 替代手工调用
- [x] 2.3 保持 `llm_scan()` 函数签名与返回值不变

## 3. 重构 poison_generator.py

- [x] 3.1 移除 `poison_generator.py` 中的 URL 标准化、重试、响应提取、json_repair 解析等重复代码
- [x] 3.2 改用 `BaseLLMClient.call_and_parse()` 替代手工调用
- [x] 3.3 保持 `generate_poison()` 函数签名与返回值不变

## 4. 重构 text_correction.py

- [x] 4.1 移除 `text_correction.py` 中的 URL 标准化、客户端初始化、响应提取等重复代码
- [x] 4.2 改用 `BaseLLMClient.call()` 替代手工调用（不解析 JSON）
- [x] 4.3 保持 `correct_text()` 函数签名与返回值不变

## 5. 验证

- [x] 5.1 运行 `python3 -m py_compile core/llm_client.py core/llm_scanner.py core/poison_generator.py core/text_correction.py` 确认语法正确
- [x] 5.2 运行 AST 分析确认四个文件结构正确，导入链路完整
- [x] 5.3 对比重构前后的三个文件，确认重复代码已消除
