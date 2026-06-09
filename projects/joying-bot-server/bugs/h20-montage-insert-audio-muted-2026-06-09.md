---
date: "2026-06-09"
status: as-designed
severity: medium
tags: [bug, h20, montage, audio, ffmpeg]
---

# H20 混剪插入视频原声被静音

## 问题描述

混剪任务中，视频素材插入到主视频画面后，插入素材自身没有声音。用户侧体感是“混剪视频插入的时候没声音”。

## 原因

代码链路中存在两层静音：

- `router/service/video_server2/video_work.py` 下载混剪视频素材后，会调用 `remove_audio_from_video()` 主动去掉素材音轨。
- `router/service/video_server2/video_time_align.py` 的 `align_video_to_audio()` 在裁剪/循环对齐素材画面时也使用 `-an` 输出无音轨视频。
- `router/service/video_server2/video_select_overlay.py` 旧逻辑只映射主视频 `0:a?`，没有把插入素材的原始音频混回最终视频。

因此这不是随机丢音轨，而是当前实现默认“插入素材只用画面”。

## 解决方案

保留画面处理链路的静音行为，避免影响现有对齐、口型和格式化逻辑；同时单独保存普通混剪视频素材的原始下载路径，在 overlay 阶段把原素材音轨按对应时间段低音量混入主视频音轨。

实现口径：

- 普通视频混剪素材：保留原素材音频源，overlay 时按字幕命中的 `(start, end)` 裁剪、延迟到正确时间点，并以 `0.28` 音量混入主音轨。
- 口型同步素材：仍走现有 `Merged_shapes_server()`，不混入素材原声，避免与主口播冲突。
- 图片素材：无原声，不参与混音。
- 如果素材源无音轨或文件不存在，跳过该素材音频，保留主音频。

## 优化点

- 后续 H20 真实任务验收时，需要听感确认 `0.28` 是否合适；如果素材原声盖住口播，可以继续降低到 `0.18-0.22` 或做 sidechain ducking。
- 本地 Windows 环境没有 `ffmpeg` 命令，未能跑本地媒体烟测；需要在 H20 服务环境跑真实任务验证。

## 相关文件

- `router/service/video_server2/video_work.py`
- `router/service/video_server2/video_select_overlay.py`
- `test/test_montage_overlay_audio_mix.py`

## 2026-06-09 最终口径更新

根据最新确认，如果原链路本来就会静音混剪素材，本轮也继续静音素材。也就是说：

- “插入素材自己的原声没有了”按当前口径属于预期行为。
- 后端撤回普通混剪素材原声混入逻辑。
- 新增 `test/test_montage_material_audio_policy.py` 防止后续误把素材原声混回去。
- 仍需在 H20 真实任务中确认的是：主视频口播音轨在插入片段期间不能丢失。
