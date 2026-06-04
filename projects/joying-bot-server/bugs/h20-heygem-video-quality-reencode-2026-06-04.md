---
date: "2026-06-04"
status: fixed
severity: high
tags: [bug, h20, heygem, video-generation, ffmpeg, quality]
---

# h20 Heygem 完整流程后画质下降

## 问题描述

切回 Heygem/duix 唇形模型后，用户反馈视频经过完整生成流程后，最终输出相对原视频画质明显下降。这个现象和 2026-06-01 LatentSync 试测期间遇到的画质下降类似，但这次主唇形模型已经切回 `VideoGenService` / Heygem。

## 复现步骤

1. 使用当前 heygem rollback 逻辑生成视频。
2. 完整经过唇形同步、转竖屏/标准化、字幕烧录、可选 BGM、封面合成流程。
3. 对比输入视频、heygem 输出中间文件、最终上传视频的清晰度和压缩观感。

## 期望行为

后处理阶段只在必须改画面的地方重编码，并统一使用高质量参数；仅做封面拼接或音频格式统一时，不应再次重编码整段主视频画面。

## 实际行为

- `router/service/video_server2/video_cover.py` 最终封面阶段无论有没有 BGM 都会执行。
- 封面合成内部先把主视频重新编码成 `main_normalized.mp4`，旧参数为 `libx264 + preset fast + crf 23`，然后再 concat copy。
- `add_subtitle.py` 字幕烧录只指定 `-c:v libx264`，没有显式 CRF，实际会落到 x264 默认质量。
- 带混剪/图片时，`video_select_overlay.py`、`Photo_video.py`、`video_time_align.py` 也存在 `crf=23` 或隐式默认 CRF 的质量损失点。

## 环境信息

- 分支: `lucky-test/voice-emotion-prompts`
- 相关提交背景: `75143382 fix: restore heygem lip sync model pool`
- 当前主链路: `router/service/video_server2/video_work.py` 使用 `VideoGenService` 调 Heygem `/easy/submit`、`/easy/query`

## 原因

根因不是 heygem 单点，而是完整后处理链路里的 ffmpeg 参数回退叠加：

1. 封面合成是最后阶段，旧实现为了拼 0.5 秒封面，把整段主视频又重编码一次，且使用 `crf=23`。
2. 字幕烧录和 overlay 本来必须重编码画面，但没有沿用之前画质修复里的 `crf=18` / `preset=medium`。
3. 之前 LatentSync 画质修复只覆盖了 HDR->SDR、9:16 标准化、横转竖等关键路径，没有覆盖 heygem 回滚后重新启用的封面/字幕/overlay 路径。

## 解决方案

- `video_server2/video_cover.py` 与 legacy `video_server/video_cover.py`:
  - 封面图片转视频改为 `crf=18`、`preset=medium`、48k audio、`+faststart`。
  - 主视频封面拼接前改为 `-c:v copy`，只统一音频，不再重编码主视频画面。
- `video_server2/add_subtitle.py` 与 legacy `video_server/add_subtitle.py`:
  - 字幕烧录显式加入 `preset=medium`、`crf=18`、`pix_fmt=yuv420p`、`+faststart`。
- `video_server2/video_select_overlay.py`:
  - overlay 重编码从硬编码 `preset fast / crf 23` 改为默认 `preset=medium / crf=18`。
- `video_server2/Photo_video.py`:
  - 图片转视频默认从 `preset=fast / crf=23` 改为 `preset=medium / crf=18`。
- `video_server2/video_time_align.py`:
  - 新增 `VIDEO_QUALITY_CRF = "18"` 和 `VIDEO_QUALITY_PRESET = "medium"`，覆盖混剪时长对齐中的 6 个 x264 命令。
- `test/test_video_quality_pipeline.py`:
  - 增加回归测试，锁定封面不再重编码主视频、字幕/overlay/photo/time-align 高质量参数，防止 CRF 23 回退。

## 相关文件

- `router/service/video_server2/video_cover.py`
- `router/service/video_server/video_cover.py`
- `router/service/video_server2/add_subtitle.py`
- `router/service/video_server/add_subtitle.py`
- `router/service/video_server2/video_select_overlay.py`
- `router/service/video_server2/Photo_video.py`
- `router/service/video_server2/video_time_align.py`
- `test/test_video_quality_pipeline.py`

## 验证

- `python -m unittest test.test_video_quality_pipeline` 通过，9 tests OK。
- `python -m unittest test.test_video_quality_pipeline test.test_scheduled_video_voice_params` 通过，20 tests OK。
- `python -m unittest test.test_video_quality_pipeline test.test_scheduled_video_voice_params test.test_video_perf_logging test.test_audio_conversion_ffmpeg_binary` 通过，33 tests OK。
- `python -m py_compile router/service/video_server2/video_cover.py router/service/video_server/video_cover.py router/service/video_server2/add_subtitle.py router/service/video_server/add_subtitle.py router/service/video_server2/video_select_overlay.py router/service/video_server2/Photo_video.py router/service/video_server2/video_time_align.py` 通过。
- `git diff --check` 通过，仅有 Windows 行尾提示。

## 优化点

- 后续最好在真实任务中保留原视频、heygem 输出、字幕后、封面后四段文件，使用 `ffprobe` 比较 bitrate、pix_fmt、codec、fps、色彩元数据，并抽关键帧做视觉对比。
- 如果仍有差异，再继续排查 heygem 服务端自身输出码率和 `/easy/*` 服务内部 ffmpeg 参数。
- 生产部署前建议把质量参数抽成统一常量，避免各工具文件再次分叉。
