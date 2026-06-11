---
date: 2026-06-11
project: joyingbot-new
type: changelog
tags: [changelog, h20, voice-clone, preview-audio, video-generation]
aliases: [H20 试听音频复用 flat payload]
---

# H20 试听音频复用 flat payload

## 改动类型

- 后端兼容性优化
- H20 测试环境部署与重启记录
- API 文档同步

## 改动内容

- 解决试听克隆接口生成的音频与最终视频中音频不一致的问题：最终视频创建链路现在可以直接接受前端已有的试听音频字段，不强制要求前端额外包一层 `reference_sample`。
- 在 `botserver/admin_server.py` 中新增 `_normalize_reference_sample_payload(reference_sample)`，统一规范化试听音频复用 payload。
- `create_digital_human_video` 在没有 `reference_sample` 时，会从请求体顶层字段中提取试听音频信息并转换为内部参考样本结构。
- 兼容字段包括 `audio_url`、`local_audio_url`、`preview_audio_url`、`ref_audio_url`、`reference_audio_url`、`audio_path`、`local_path`、`relative_path`、`path`、`emotion`、`emotion_label`、`source`、`sample_id`、`text`、`speech_text`、`preview_text`、`audition_text`、`voice_id`、`person_id`、`voice_name`、`metadata`、`ref_text`、`speaker_wav_text`、`speaker_text`。
- 保留已存在的 `reference_sample` 包装格式，避免影响旧调用方。
- 通过 apidoc/YApi 同步了 `POST /admin/app/preview_tts_clone` 的请求示例，将参考音频示例更新为本地上传路径风格。

## 影响范围

- `POST /admin/app/preview_tts_clone` 的试听音频结果可继续按前端现有字段传递。
- `POST /admin/app/create_digital_human_video` 可在不新增前端字段的情况下复用试听音频。
- 目标链路是“选择情绪生成试听音频 -> 保存该试听音频作为克隆音频 -> 最终视频复用同一音频”。
- 前端无需新增 `reference_sample` 包装字段，减少前后端再次对齐成本。

## 验证结果

- 本地回归：`python -m pytest tests/test_reference_sample_payload.py -q`，结果 `5 passed`。
- 本地组合回归：`python -m pytest tests/test_reference_sample_payload.py tests/test_audio_clone_helpers.py -q`，结果 `15 passed`。
- Git 分支：`feature/ai_v6.3.1_video`。
- 功能提交：`4423651 fix: reuse preview audio clone payload`。
- 已合并到 `test`，merge commit 为 `bb7f083`，并推送到 GitLab。
- H20 测试服务器 `/www/wwwroot/joyingbot` 已拉取最新 `test`。
- 已执行 `supervisorctl restart h20-botserver:h20-botserver_00` 重启服务。
- 重启后确认 8100 端口服务存活，`POST http://127.0.0.1:8100/admin/create_digital_human_video` 返回 `请先登录`，说明路由和进程已加载。
- 完整登录态端到端视频生成当时仍受已有任务锁影响：任务 `3810` 处于 `processing`，返回“任务正在执行中”，因此最终视频产出未在该轮完全跑完。

## 相关文件

- `botserver/admin_server.py`
- `tests/test_reference_sample_payload.py`
- `tests/test_audio_clone_helpers.py`

## 相关记录

- [[projects/joyingbot-new/changelog/2026-06-10_voice_audition_reference_sample|试听音频参考样本]]
- [[projects/joyingbot-new/changelog/2026-06-09_voice_clone_payload_consistency|语音克隆 payload 一致性]]
- [[projects/joyingbot-new/changelog/2026-06-09_h20_voice_clone_runtime_and_migration_status|H20 语音克隆运行与迁移状态]]

## 图谱链接

- [[projects/joyingbot-new/00-项目概览|项目概览]]
- [[projects/joyingbot-new/changelog/00-changelog-index|更新日志索引]]