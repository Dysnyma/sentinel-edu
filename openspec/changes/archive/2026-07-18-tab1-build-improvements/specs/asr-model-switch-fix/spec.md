# ASR 模型切换修复

## ADDED Requirements

### Requirement: 模型切换触发重新转写
当用户在侧边栏切换本地 Whisper 模型时，系统 SHALL 自动清空上一次的转写缓存并触发重新转写。

- 检测模型变化：对比当前 `local_whisper_model` 与 session_state 中记录的 `_last_model`。
- 清空缓存：清除 `_last_file_id` 和 `asr_transcript`，使得文件上传区域在下次渲染时重新处理。
- 保持文件选择：不清除用户已上传的文件引用，仅清除处理结果。

#### Scenario: 切换模型后重新转写
- **WHEN** 用户已上传音频文件并完成首次转写（模型 A），随后在侧边栏切换到模型 B
- **THEN** 系统清除旧转写结果，显示待处理状态，用户无需重新上传文件
- **THEN** 页面自动触发使用模型 B 的重新转写

#### Scenario: 首次使用无缓存时
- **WHEN** 用户刚启动应用，未上传任何文件，切换模型
- **THEN** 不影响任何状态，不触发错误
