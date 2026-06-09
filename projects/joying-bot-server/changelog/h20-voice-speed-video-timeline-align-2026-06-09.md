---
date: "2026-06-09"
tags: [changelog, bugfix, h20, voice-speed, timeline, heygem]
---

# H20 倍速口播与 Heygem 视频时间轴对齐

## 最新 test 核准

2026-06-09 已执行 `git fetch origin test` 与 `git pull --ff-only origin test`，当前 test 最新提交为：

```text
d4cd445a Merge remote-tracking branch 'origin/test' into feature/ai_v6.3.1_video
```

核准结果：最新 test 主链路是 Heygem / `VideoGenService`，不是 LatentSync。

代码证据：

- `router/service/video_server2/video_work.py` 使用 `VideoGenService(video_domain=Original_video_url, task_id=task_id)`。
- `LatentSyncService` 在最新 test 中仅作为注释切换点保留，未启用。
- `scheduler/collect_scheduler.py` 中 `config_value` 对应 Heygem `/easy/*` 服务域名，`config_value_audio` 对应 VoxCPM。

## 改动类型

- [ ] 新功能
- [x] Bug 修复
- [ ] 重构
- [ ] 配置变更

## 改动内容

根据产品口径，倍速问题的核心是：`voice_speed` 只加速口播克隆音频，克隆音频会变短；如果模板视频仍按原时长进入 Heygem，就会导致视频/字幕时间轴长于真实口播音频，后段表现为“字幕跟不上”或“口播消失”。

本次修复按最新 Heygem 链路落位：

- `voice_speed` 后端最高阈值改为 `1.5`，不再保留 `2.0` / `3.0`。
- `scheduler/collect_scheduler.py` 调用 `clamp_voice_speed()`，把历史任务或绕过前端传入的高倍速压到 `1.5` 后再传给 `video_work_Heygem_Whisper()`。
- `video_work.py` 在 VoxCPM 声音克隆完成后读取 `clone_audio_duration`。
- 在 Heygem / `VideoGenService.generate_video()` 前读取模板视频 `source_video_duration`。
- 当模板视频和克隆音频时长相差超过 `0.3s` 时，先调用 `align_video_to_audio(..., duration_padding=0.0)` 把模板视频对齐到克隆音频时长。
- 对齐后重新上传模板视频，并把新的 `Video_url` 传给 Heygem。
- `video_time_align.py` 新增 `duration_padding` 参数；主模板视频对齐使用 `0.0`，混剪素材继续使用默认 `0.2` 秒补尾。

## 影响范围

- 影响 `video_server2` H20 Heygem 生成链路。
- 主要解决倍速后口播音频短于视频/字幕时间轴的问题。
- 不改变混剪素材原声策略：素材自身声音继续静音，只保留主视频口播音轨。
- 最新 test 中性能 stage 名仍保留历史字符串 `latentsync`，这只是日志指标名，不代表实际启用了 LatentSync。

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

说明：测试输出中仍有仓库既有 `DeprecationWarning: invalid escape sequence '\s'`，不影响通过。

## 待验证

- H20 真实任务：确认 Heygem 输出视频时长跟克隆音频一致。
- H20 真实任务：确认字幕不再拖到口播结束之后。
- H20 真实任务：确认混剪插入片段期间主口播音轨不丢失；素材自身原声按当前口径不应出现。

## 相关记录

- [[projects/joying-bot-server/docs/h20-montage-voice-speed-status-2026-06-09|H20 混剪倍速与插入音频当前状态]]
- [[projects/joying-bot-server/changelog/h20-montage-voice-speed-clamp-2026-06-09|H20 混剪任务高倍速后端兜底]]
- [[projects/joying-bot-server/changelog/h20-montage-material-audio-muted-policy-2026-06-09|H20 混剪素材继续静音口径]]
- [[projects/joying-bot-server/bugs/h20-montage-voice-speed-subtitle-2026-06-08|H20 混剪视频 3 倍速导致字幕体感跟不上]]