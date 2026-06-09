---
date: "2026-06-09"
tags: [changelog, bugfix, h20, montage, voice-clone, scheduler, heygem]
---

# H20 视频任务高倍速后端兜底

## 改动类型

- [ ] 新功能
- [x] Bug 修复
- [ ] 重构
- [ ] 配置变更

## 改动内容

为昨天记录的“混剪视频 3 倍速导致字幕体感跟不上”增加后端兜底。最新 test 已核准主链路为 Heygem / `VideoGenService`，不是 LatentSync。

当前实现：

- 在 `router/service/video_server2/voice_params.py` 中：
  - `VOICE_CLONE_ALLOWED_SPEEDS = {0.75, 1.0, 1.25, 1.5}`。
  - `VOICE_CLONE_MAX_SPEED = 1.5`。
  - `clamp_voice_speed()` 会把历史高倍速值降到 `1.5`。
- 在 `scheduler/collect_scheduler.py` 处理任务时：
  - 先计算 `voice_speed_original`。
  - 调用 `clamp_voice_speed()` 得到 `voice_speed_effective`。
  - 把 `voice_speed_effective` 传给 `video_work_Heygem_Whisper()`。
- 参数校验不再接受 `2.0` / `3.0`；历史任务或接口直传高倍速时，scheduler 进入生成前也会降到 `1.5`。
- 增加日志字段：`voice_speed_original`、`voice_speed_effective`、素材总数、选中的混剪素材数、视频素材数、图片素材数。
- 第 1、2、3 项生产素材同步/DB 大改已单独延后记录，不纳入本次变更。

## 影响范围

- 影响 H20 scheduler 路径下的视频生成任务。
- 普通视频生成链路也不再保留 3 倍速能力，最高按 1.5 倍速执行。
- 不修改 CRM 接口协议，不修改 DB 表结构，不处理生产素材同步大改。

## 验证

```text
python -m unittest test.test_scheduled_video_voice_params test.test_voice_speed_timeline_alignment
Ran 20 tests OK
```

```text
python -m py_compile router\service\video_server2\voice_params.py router\service\video_server2\video_time_align.py router\service\video_server2\video_work.py scheduler\collect_scheduler.py
exit 0
```

```text
python -m unittest test.test_scheduled_video_voice_params test.test_voice_speed_timeline_alignment test.test_montage_material_audio_policy test.test_video_material_montage_sync test.test_voxcpm_voice_style_prompt test.test_voice_clone_upload test.test_production_baseline_alignment test.test_video_model_busy_retry
Ran 63 tests OK
```

## 相关记录

- [[projects/joying-bot-server/docs/h20-montage-voice-speed-status-2026-06-09|H20 混剪倍速与插入音频当前状态]]
- [[projects/joying-bot-server/changelog/h20-voice-speed-video-timeline-align-2026-06-09|H20 倍速口播与 Heygem 视频时间轴对齐]]
- [[projects/joying-bot-server/docs/h20-montage-voice-speed-work-summary-2026-06-08|H20 混剪倍速字幕排查今日总结]]
- [[projects/joying-bot-server/bugs/h20-montage-voice-speed-subtitle-2026-06-08|H20 混剪视频 3 倍速导致字幕体感跟不上]]
- [[projects/joying-bot-server/docs/prod-montage-material-sync-deferred-todo-2026-06-09|生产混剪素材同步大改延后待办]]