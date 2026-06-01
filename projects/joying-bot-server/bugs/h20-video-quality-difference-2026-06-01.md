---
date: "2026-06-01"
status: fixed
severity: high
tags: [bug, h20, video-generation, latentsync, ffmpeg]
---

# h20 视频处理前后画质差异

## 问题描述

产品反馈同一视频处理前后画质差异明显，表现为处理后画面更软、观感和原视频不一致，需要确认是否由 ffmpeg 引起，并要求 h20 测试服把 LatentSync `guidance_scale` 调整为 `1.8`。

## 原因

主要原因不是单一 ffmpeg 问题，而是两类因素叠加：

1. LatentSync 是生成式唇形同步，会对人脸区域做重绘和融合，天然可能改变脸部细节、肤色和边缘锐度。
2. 后续 ffmpeg 管线存在多次重编码，部分路径默认使用 `crf=23`，会在已经生成过的视频上继续叠加压缩损失；HDR 输入也没有在进入唇形同步前统一检查并转换为 SDR，可能造成曝光和色彩观感差异。

## 解决方案

- 将 `router/service/video_server/latentsync_api.py` 默认 `guidance_scale` 调整为 `1.8`。
- 在 `router/service/video_server2/video_work.py` 中恢复进入唇形同步前的 HDR -> SDR 检查，仅 HDR 输入会转换，SDR 输入保持原文件路径。
- 将关键二次编码路径默认质量提高到 `crf=18`：
  - `router/service/video_server2/HDR_TO_SDR.py`
  - `router/service/video_server2/video_format_keep.py`
  - `router/service/video_server2/video_portrait_screen.py`
- 新增 `test/test_video_quality_pipeline.py`，覆盖上述画质管线约束。
- 同步更新旧的 LatentSync 参数测试期望为 `1.8`。

## 验证

- GitLab `test` 已推送并合并：
  - `a0820871 fix: preserve h20 video quality defaults`
  - `0d7e9021 merge h20 video quality preserve into test`
- 本地验证：
  - `python -m unittest test.test_video_quality_pipeline`
  - `python -m unittest test.test_video_quality_pipeline test.test_latentsync_timeout test.test_production_baseline_alignment test.test_audio_conversion_ffmpeg_binary`
  - `python -m py_compile router/service/video_server/latentsync_api.py router/service/video_server2/HDR_TO_SDR.py router/service/video_server2/video_format_keep.py router/service/video_server2/video_portrait_screen.py router/service/video_server2/video_work.py`
  - `git diff --check origin/test..HEAD`
- 全量 `python -m unittest discover -s test` 未通过，原因是当前本机环境缺 `pytest`，且部分老测试依赖不存在的 `app_config-template.json`，不是本次改动引入。
- h20 验证：
  - `/data/project/test_ai_botserver` 指向 `/data/project/test_ai_botserver.20260601202651`。
  - 当前部署目录包含 `guidance_scale=1.8`、HDR -> SDR 检查、`crf=18`。
  - `ai_botserver_sch` 已重启，进程 cwd 为 `/data/project/test_ai_botserver.20260601202651`。
  - LatentSync `http://127.0.0.1:8101/health` 返回 ok。

## 优化点

- 后续如果仍有明显差异，需要针对同一个任务保存原视频、LatentSync 输出和最终输出，比较 bitrate、codec、pix_fmt、色彩元数据和关键帧截图。
- 如果需要进一步接近原视频，可以考虑保留原视频码率上限、减少不必要的重编码次数，或在 LatentSync 输出后增加清晰度/码率指标记录。
