---
date: "2026-06-09"
status: in-progress
tags: [status, h20, montage, voice-clone, subtitle, audio, heygem]
---

# H20 混剪倍速与插入音频当前状态

## 当前结论

截至 2026-06-09，本轮混剪问题拆成两条：

1. 混剪高倍速导致字幕体感跟不上。
2. 混剪视频插入时没声音。

最新 test 已拉取并核准：当前主链路是 Heygem / `VideoGenService`，不是 LatentSync。LatentSync 在代码里只是注释保留的切换点。

当前代码层已处理第 1 条；第 2 条已经确认口径：混剪素材沿用原链路，只使用画面，不使用素材自身原声。因此“插入素材自己的声音没有了”不是 bug，而是当前产品/后端策略。后续只需要确认最终视频主口播音轨没有在插入片段期间丢失。

## 最新 test 拉取记录

```text
git fetch origin test
git pull --ff-only origin test
```

当前 test 提交：

```text
d4cd445a Merge remote-tracking branch 'origin/test' into feature/ai_v6.3.1_video
```

核准结果：

- `router/service/video_server2/video_work.py` 使用 `VideoGenService(video_domain=Original_video_url, task_id=task_id)`。
- `scheduler/collect_scheduler.py` 中 `config_value` 对应 Heygem `/easy/*` 服务域名，`config_value_audio` 对应 VoxCPM。
- `LatentSyncService` 未启用，只在注释里保留切换点。

## 已处理：倍速字幕跟不上

最新确认：`voice_speed=3.0` 不再保留，最高阈值设为 `1.5`。

代码状态：

- `router/service/video_server2/voice_params.py`
  - `VOICE_CLONE_ALLOWED_SPEEDS = {0.75, 1.0, 1.25, 1.5}`
  - `VOICE_CLONE_MAX_SPEED = 1.5`
  - `clamp_voice_speed()` 会把历史高倍速值降到 `1.5`。
- `scheduler/collect_scheduler.py`
  - 调用 `clamp_voice_speed()` 后再把 `voice_speed_effective` 传给 `video_work_Heygem_Whisper()`。
  - 日志记录 `voice_speed_original`、`voice_speed_effective`、`has_montage`、素材总数和混剪素材数量。
  - 日志口径为 `[处理任务-音色倍速降级]`，避免被理解成混剪素材原声处理。

后端效果：

- 新接口入参 `2.0` / `3.0` 会被参数校验拒绝。
- 历史任务或接口绕过传入高倍速时，scheduler 进入生成前会降到 `1.5`。
- 普通视频也不再保留 `3.0` 能力。

## 已处理：倍速后视频时间轴未对齐

产品反馈的“字幕跟不上 / 后面口播消失”，核心不是字幕单独变慢，而是 `voice_speed` 只影响口播音频速度。倍速后克隆音频变短，但模板视频仍按原时长进入 Heygem，导致最终视频/字幕时间轴可能长于真实口播音频。

后端修复：

- VoxCPM TTS 克隆完成后读取 `clone_audio_duration`。
- HDR/SDR 处理后读取模板视频 `source_video_duration`。
- 如果两者相差超过 `0.3s`，先调用 `align_video_to_audio(..., duration_padding=0.0)` 把模板视频精确 trim/loop 到克隆音频时长。
- 重新上传对齐后的视频，并把新的 `Video_url` 传给 Heygem / `VideoGenService.generate_video()`。
- 混剪素材自身的对齐仍保留默认 `0.2s` padding，不受主视频模板对齐影响。

## 已确认：混剪素材继续静音

最终口径：如果之前原链路就是静音素材，那么本轮也继续静音素材。

代码证据：

- `router/service/video_server2/video_work.py` 在处理混剪视频素材时，会调用 `remove_audio_from_video()`，主动去掉混剪素材自身音轨。
- `router/service/video_server2/video_time_align.py` 的 `align_video_to_audio()` 在裁剪/循环素材画面时也会使用 `-an` 输出无音轨视频。
- `router/service/video_server2/video_select_overlay.py` 只映射 `0:a?`，即保留主视频音轨，不混入插入素材音轨。

当前处理：

- 已撤回“把普通混剪素材原声低音量混入主音轨”的尝试实现。
- 新增策略测试 `test/test_montage_material_audio_policy.py`，确保后续不会误把素材原声混回去。
- 如果后续反馈是“插入片段期间主口播也没声音”，那是另一类音轨丢失 bug，需要拿具体 H20 样例任务排查。

## 验证记录

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

说明：测试输出中仍有仓库既有 `DeprecationWarning: invalid escape sequence '\s'`，不影响通过。本地 Windows PATH 没有 `ffmpeg`，本机媒体级烟测未跑成。

## 其他未闭环事项

- H20 测试服还需要跑一条真实混剪任务，确认最终视频主口播音轨在插入片段期间没有丢失；素材自身原声按当前口径不应出现。
- H20 真实任务还需要确认 Heygem 输出时长与克隆音频/对齐后模板一致，字幕不再拖到口播结束之后。
- 生产混剪素材同步 / CRM 异常素材 ID / AI `material_id` 是否改 `BIGINT` 已单独延后，不纳入本轮倍速修复。
- BGM 下载失败降级为无 BGM 尚未完整闭环；当前只是混音内部有 fallback。

## 关联记录

- [[projects/joying-bot-server/changelog/h20-montage-voice-speed-clamp-2026-06-09|H20 混剪任务高倍速后端兜底]]
- [[projects/joying-bot-server/changelog/h20-voice-speed-video-timeline-align-2026-06-09|H20 倍速口播与 Heygem 视频时间轴对齐]]
- [[projects/joying-bot-server/changelog/h20-montage-material-audio-muted-policy-2026-06-09|H20 混剪素材继续静音口径]]
- [[projects/joying-bot-server/bugs/h20-montage-insert-audio-muted-2026-06-09|H20 混剪插入视频原声被静音]]
- [[projects/joying-bot-server/docs/prod-montage-material-sync-deferred-todo-2026-06-09|生产混剪素材同步大改延后待办]]
- [[projects/joying-bot-server/docs/h20-montage-voice-speed-work-summary-2026-06-08|H20 混剪倍速字幕排查今日总结]]
- [[projects/joying-bot-server/bugs/h20-montage-voice-speed-subtitle-2026-06-08|H20 混剪视频 3 倍速导致字幕体感跟不上]]