---
date: 2026-05-28
status: fixed
severity: medium
tags: [bug, voxcpm, tts]
---

# VoxCPM 声音克隆效果差 — reference_text 未传递

## 问题描述

测试 VoxCPM API 声音克隆时，生成的音频完全听不懂，语音模糊不清。

## 原因

1. `voxcpm_tts.py` 调用 VoxCPM API 时没有传 `reference_text` 参数
2. VoxCPM 模型需要参考音频对应的文本（`prompt_text`）来对齐音素，文本为空时对齐失败
3. 同时 `voice_emotion`、`voice_speed`、`voice_volume` 三个参数在 `voxcpm_tts.py` 中硬编码为默认值，无法从 CRM 任务数据传入

## 复现步骤

```bash
# 不带 reference_text 的请求 → 音频糊掉
curl -X POST http://127.0.0.1:8100/v1/clone-voice \
  -d '{"text": "你好", "reference_audio_url": "...", "reference_text": ""}'
```

## 解决方案

1. 测试阶段：手动传入正确的 `reference_text`，效果立即改善
2. 代码层面：
   - `voxcpm_tts.py` 扩展函数签名，新增 `reference_text`、`voice_emotion`、`voice_speed`、`voice_volume` 可选参数
   - `video_work.py` 调用时传入 `simplified_text`（Whisper 转录）作为 `reference_text`
   - `video_work_Heygem_Whisper` 和上游 submit 路由增加 voice 参数传递

## 优化点

- `simplified_text` 在 video_work 作用域内已存在（Whisper 转录结果），但从未传给克隆函数 — 只需加一个 keyword arg 即可

## 相关文件

- `router/service/video_server/voxcpm_tts.py`
- `router/service/video_server2/voxcpm_tts.py`
- `router/service/video_server/voxcpm_api.py`
- `router/service/video_server2/video_work.py`
- `router/crm_server.py`
