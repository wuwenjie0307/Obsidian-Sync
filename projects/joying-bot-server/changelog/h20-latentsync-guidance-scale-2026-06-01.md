---
tags: [changelog, h20, latentsync, voxcpm, video-generation]
---

# h20 LatentSync guidance_scale 调整为 1.7

## 时间

- 2026-06-01 17:30 左右

## 背景

产品反馈 `guidance_scale=2.0` 的嘴型/表情幅度偏猛，要求改成 `1.7` 继续测试。同时排查声音克隆是否跳过，以及声音克隆输入文案是否被去掉标点导致语气变平。

## 改动内容

- 本地仓库：
  - `router/service/video_server/latentsync_api.py`
  - `LipSyncRequest.guidance_scale` 默认值从 `2.0` 改为 `1.7`。
- h20 测试服：
  - `/data/projects/joyingbot-new/router/service/video_server/latentsync_api.py`
  - 同步把 `guidance_scale` 默认值改为 `1.7`。
  - 备份文件：`/tmp/latentsync_api.py.bak.20260601172726`
- 只重启了 LatentSync API `8101`，没有重启 Bot 和 VoxCPM。

## 验证结果

- 本地：
  - `python -m py_compile router/service/video_server/latentsync_api.py` 通过。
- h20：
  - `127.0.0.1:8017/status/check` 返回 `{"status":"ok"}`。
  - `127.0.0.1:8100/status/check` 返回 `{"status":"ok"}`。
  - `127.0.0.1:8110/health` 返回 `{"status":"ok"}`。
  - `127.0.0.1:8101/health` 返回 `{"status":"ok"}`。
  - `8101` 当前进程 PID：`1762157`。
  - `t_comfyui_config.id=1 is_active=1`，当前没有排队/处理中视频任务。

## 声音克隆文案排查

- 当前视频生成链路没有跳过声音克隆：
  - 上一次任务 `job_id=1005/task_id=996` 已调用 VoxCPM，声音克隆阶段耗时约 `69.28s`。
- 声音克隆输入文案没有被去掉标点：
  - `scheduler.collect_scheduler` 里只对 `video_user_subtitle`/`ai_rewritten_text` 做 `\r`、`\n` 去除，保留中文逗号、句号、感叹号等标点。
  - 测试库任务 `id=1208` 的 `video_user_subtitle` 本身包含 `，`、`！`、`。`、`；` 等标点。
  - 去标点逻辑 `normalize_text_for_alignment(...)` 用于后续字幕对齐，不是传给 VoxCPM 的正文输入。
- 参考音频 ASR 文本作为 `reference_text` 传给 VoxCPM；ASR 文本本身可能标点较少，但它不是最终要朗读的正文。

## 后续测试口径

- 产品/CRM 重新提交一个视频任务后，新的 LatentSync 默认会使用 `guidance_scale=1.7`。
- 如果仍觉得语气平，优先对比：
  - `voice_emotion` 不同值。
  - 原始文案标点/停顿是否自然。
  - VoxCPM 参考音频本身是否有足够语气起伏。
