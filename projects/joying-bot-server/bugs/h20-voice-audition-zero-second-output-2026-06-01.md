---
date: "2026-06-01"
status: fixed
severity: medium
tags: [bug, h20, crm, voice-clone, audition]
---

# h20 试听接口返回 0 秒音频

## 问题描述

CRM 测试音色克隆试听接口时，请求只传了 `voice_emotion`、`voice_speed`、`voice_volume`、`voice_file_url`，没有传 `text`。
接口返回了一个 CDN wav 链接，但前端显示音频时长 0 秒。

## 原因

h20 日志确认 VoxCPM 实际生成了 wav，不是 CDN 上传失败。
该 wav 真实时长约 0.37 秒，前端按秒取整后显示 0 秒。

触发条件：

- 请求未传 `text`，后端使用了较短默认文案。
- `voice_speed=3` 是最大加速档。
- VoxCPM 日志出现 `Badcase detected`，最终生成音频过短。
- Bot 试听接口之前没有在上传 CDN 前校验生成音频的真实时长。

## 解决方案

已在 `test` 分支提交修复：

- 默认试听文案改为更长的句子。
- 新增 wav 时长读取工具。
- `/crm/voice_clone_audition` 在上传 CDN 前检查生成 wav 真实时长。
- 如果生成音频小于 1 秒，直接返回 400：`生成音频过短，请增加 text 或降低 voice_speed 后重试`，不再上传 0 秒试听音频。
- 新增测试覆盖 wav 时长读取和试听接口时长检查。

## 验证

本地验证通过：

```powershell
python -m py_compile router\crm_server.py router\service\video_server2\audio_duration.py
python -m unittest test.test_scheduled_video_voice_params test.test_voice_clone_upload
git diff --check
```

GitLab `test` 已同步：

```text
af300ae3 fix: guard voice audition short audio
```

## 优化点

- 产品/CRM 测试音色效果时建议显式传 `text`，用 20-40 个字更容易判断效果。
- 极限参数建议不要第一次就组合 `voice_emotion=7`、`voice_speed=3`、`voice_volume=100`，可先用 `voice_speed=1.0/1.25` 对比。
- 后续如仍出现 VoxCPM badcase，应继续在 VoxCPM API 层增加更细的 badcase 检测。

## 相关文件

- `router/crm_server.py`
- `router/service/video_server2/audio_duration.py`
- `test/test_voice_clone_upload.py`
