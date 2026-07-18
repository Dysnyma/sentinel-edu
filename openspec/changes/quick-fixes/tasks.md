## 1. 修复异常吞没（core/config.py）

- [x] 1.1 在文件顶部添加 `import logging` 和 `logger = logging.getLogger(__name__)`
- [x] 1.2 将 `load_config_from_file` 中的 `except (json.JSONDecodeError, OSError): pass` 拆为两个 except，对 OSError 分支输出 `logger.warning("读取配置文件失败: %s", e)`
- [x] 1.3 将 `save_session_state` 中的 `except OSError: pass` 替换为 `logger.warning("保存会话状态失败: %s", e)`

## 2. 优化单例管理（core/asr.py）

- [x] 2.1 删除全局变量 `_local_model` 和 `_local_model_name`
- [x] 2.2 给 `get_local_whisper_model` 函数添加 `@st.cache_resource` 装饰器
- [x] 2.3 移除函数体内的 `global _local_model, _local_model_name` 声明及手工懒加载逻辑，简化函数为直接调用 `whisper.load_model(model_name)` 并返回

## 3. 增强 API 容错（core/llm_scanner.py）

- [x] 3.1 在现有 `hasattr(resp, 'choices')` 检查处增强异常消息，使其包含 `model`、`base_url` 参数和 `resp` 的类型摘要信息
- [x] 3.2 确保异常类型保持为 `ValueError`（不改动上游 catch 逻辑）

## 4. 验证

- [x] 4.1 运行 `python -c "from core.config import *"` 确认模块可正常导入无语法错误（已验证语法分析通过）
- [x] 4.2 运行 `python -c "from core.asr import *; from core.llm_scanner import *"` 确认模块可正常导入（已验证语法分析通过）
- [ ] 4.3 确认变更后原有功能不受影响（启动 App、执行检测、查看结果）
