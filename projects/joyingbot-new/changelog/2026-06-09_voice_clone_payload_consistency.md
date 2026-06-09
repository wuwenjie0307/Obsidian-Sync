---
date: "2026-06-09"
tags: [project, changelog, h20-test, voice-clone]
---

# 2026-06-09 voice clone payload consistency

## 改动类型
- bug fix
- observability

## 改动内容
- 保留试听池 `voice_audition_url` 与视频生成池 `comfyui_url` 的资源隔离。
- 在 `router/service/video_server2/voxcpm_tts.py` 中新增统一的 `build_clone_voice_api_url()` 与 `build_clone_voice_payload()`。
- 将 `router/crm_server.py` 的 `voice_clone_audition()` 改为复用同一套 VoxCPM 请求 URL 与 payload 构造，避免试听和视频链路字段、默认值、reference_text 处理发生代码漂移。
- 补充视频 VoxCPM 日志/性能埋点中的 `reference_text_len`、`voice_emotion`、`voice_speed`、`voice_volume`，试听日志也补 `text_len`。
- 新增回归测试覆盖统一 payload 构造和试听入口复用公共构造。

## 影响范围
- `router/crm_server.py`
- `router/service/video_server2/voxcpm_tts.py`
- `test/test_video_perf_logging.py`
- `test/test_voice_clone_upload.py`

## 验证结果
- `python -m unittest test.test_video_perf_logging test.test_voice_clone_upload test.test_scheduled_video_voice_params test.test_voice_audition_pool_service`
- 结果：`Ran 50 tests in 0.671s`，`OK`
- 注意：测试输出存在历史 `DeprecationWarning: invalid escape sequence '\s'`，非本次改动引入。

## 后续待办
- 发布到 H20 测试服后，继续验证试听池与视频池 VoxCPM 的模型版本、情绪 prompt 映射、reference_text 清洗逻辑是否一致。
- 建议 VoxCPM 服务后续增加 `/version` 或 `/health` 元信息，暴露 code/model/emotion_prompt/text_cleaner 版本 hash。
