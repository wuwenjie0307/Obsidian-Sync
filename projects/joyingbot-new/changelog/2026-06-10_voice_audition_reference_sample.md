---
date: "2026-06-10"
tags: [project, changelog, h20-test, voice-clone]
---

# 2026-06-10 voice audition reference sample

## 改动类型
- new feature
- api contract
- docs

## 改动内容
- 声音克隆试听响应新增 `data.reference_sample`。
- `reference_sample.voice_file_url` 使用本次试听合成后的音频地址。
- `reference_sample.voice_emotion=1`、`reference_sample.voice_speed=1.0`、`reference_sample.voice_volume=50`，用于前端在用户选择“使用本次试听作为音色样本”后，直接作为下一次试听或正式视频生成的音色字段。
- 保留原有 `data.voice_emotion`、`data.voice_speed`、`data.voice_volume`、`data.voice_file_url`，兼容旧调用方。
- README 和 YApi 已同步：试听接口 `1936`、个人形象保存接口 `707` 均说明试听音频作为样本时应使用默认参数，避免二次叠加情绪/语速效果。
- 修正文档里的 `voice_speed` 取值口径：当前后端允许 `0.75/1.0/1.25/1.5`。

## 影响范围
- `router/crm_server.py`
- `test/test_voice_clone_upload.py`
- `README.md`
- YApi CRM 接口 `1936`、`707`

## 验证结果
- `python -m unittest test.test_voice_clone_upload test.test_scheduled_video_voice_params test.test_video_perf_logging test.test_voice_audition_pool_service test.test_voxcpm_voice_style_prompt`
- 结果：`Ran 66 tests in 0.670s`，`OK`
- 测试中仍有历史 `DeprecationWarning: invalid escape sequence '\s'`，非本次改动引入。

## 后续待办
- 前端需要在试听结果区域增加“使用本次试听作为音色样本”动作，点击后使用 `data.reference_sample` 更新当前音色字段。
- 前端生成正式视频时若当前样本来自试听音频，应提交 `reference_sample` 中的默认参数，避免再传上一次的愤怒/悲伤等情绪参数。

## 提交与合并状态
- 本地提交：`896f4317 feat: add voice audition reference sample`
- 已推送个人分支：`origin/feature/ai_v6.3.1_video`
- 已快进合并到：`origin/test`
- 合并前确认：`origin/test is ancestor of HEAD`，无冲突。
- 最终远端状态：`origin/test` 与 `origin/feature/ai_v6.3.1_video` 均指向 `896f4317e377dd6c39d613c43562b1e198638800`。
- 未纳入提交：工作区原有未跟踪文件未处理、未提交。
