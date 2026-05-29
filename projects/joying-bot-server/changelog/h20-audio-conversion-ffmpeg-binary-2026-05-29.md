---
date: "2026-05-29"
tags: [changelog, h20, video-generation, voice-clone]
---

# h20 audio conversion ffmpeg binary

## 改动类型

- [ ] 新功能
- [x] Bug 修复
- [ ] 重构
- [ ] 配置变更

## 改动内容

- 修复 h20 视频生成“声音克隆阶段失败”问题。
- 将 `router/service/video_server2/video_tool.py` 和 `router/service/video_server/video_tool.py` 的音频转 WAV 逻辑从 Python `ffmpeg` wrapper 改为系统 `ffmpeg` 命令。
- 新增 `test/test_audio_conversion_ffmpeg_binary.py`，防止后续代码又改回 `ffmpeg.input`。
- 已合入并推送 `origin/test`：
  - `ff054847 fix: use ffmpeg binary for audio conversion`
  - `f3ea81d6 merge h20 audio conversion ffmpeg fix into test`

## 影响范围

- 影响 h20 视频生成链路中参考音频不是 `.wav` 时的转换步骤。
- 主要解决 `.m4a` 等音频在进入 VoxCPM 前转换失败的问题。
- 不改 VoxCPM、LatentSync、CRM 入口、端口映射和调度表结构。

## 验证记录

- 本地相关测试 11 个通过。
- h20 当前部署目录为 `/data/project/test_ai_botserver.20260529203845`。
- h20 上 `8017/8100/8110/8101` health 均返回 `ok`。
- h20 上系统 `ffmpeg` 可将失败样例 `.m4a` 成功转换成 WAV。
- 最新查询显示旧失败任务仍是 `task_status=4`，调度当前无待生成任务；需要新建任务或人工重置指定任务才能重新跑视频生成。
