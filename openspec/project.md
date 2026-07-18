# 项目全局信息
技术栈：Python 3.10 + Streamlit + SQLite
核心依赖：pyahocorasick、openai-whisper、plotly、jieba
代码规范：PEP8，模块分层：core/ 核心逻辑、views/ 页面UI
运行入口：streamlit run app.py
测试方式：无自动化测试，以页面功能验证为主
约束：不得引入重型依赖，保持单文件启动，兼容本地离线运行