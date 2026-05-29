---
date: "2026-05-29"
status: fixed
severity: high
tags: [bug, h20, video-generation, voice-clone, ffmpeg]
---

# h20 视频生成声音克隆阶段失败

## 问题描述

CRM 前端创建视频任务后，任务进入 h20 测试服调度流程，但最终显示“声音克隆失败”。

## 原因

h20 的 `botserver` Python 环境里安装的是 `ffmpeg==1.4` 包，该包没有 `ffmpeg.input` 和 `ffmpeg.Error`。

代码在处理非 `.wav` 的参考音频（例如 `.m4a`）时，会先把音频转换成 16kHz 单声道 WAV；旧实现依赖 Python `ffmpeg` wrapper：

```python
ffmpeg.input(audio_path)
```

因此在转换阶段直接抛错，实际还没调用到 VoxCPM 声音克隆模型。

## 解决方案

已将以下两个文件里的 `_convert_audio_to_wav` 改为直接调用系统 `ffmpeg` 二进制：

- `router/service/video_server2/video_tool.py`
- `router/service/video_server/video_tool.py`

h20 上确认系统 `ffmpeg` 命令可用，因此不再依赖 Python `ffmpeg` 包。

## 验证

- 本地新增回归测试：`test/test_audio_conversion_ffmpeg_binary.py`
- 本地验证通过：
  - `python -m py_compile router/service/video_server2/video_tool.py router/service/video_server/video_tool.py`
  - `python -m unittest test.test_audio_conversion_ffmpeg_binary test.test_scheduled_video_voice_params test.test_voice_clone_upload`
  - `git diff --check origin/test..HEAD`
- 已推送并合入 `origin/test`：
  - `ff054847 fix: use ffmpeg binary for audio conversion`
  - `f3ea81d6 merge h20 audio conversion ffmpeg fix into test`
- h20 自动部署目录已更新到 `/data/project/test_ai_botserver.20260529203845`。
- h20 验证：
  - 两个 `video_tool.py` 不再包含 `ffmpeg.input`
  - 两个文件 `py_compile` 通过
  - 使用同一个 `.m4a` 测试文件跑系统 `ffmpeg` 转 WAV 成功
  - `8017/8100/8110/8101` health 均返回 `ok`

## 当前状态

旧任务已经被旧代码标记为 `task_status=4`，失败原因仍是“声音克隆阶段失败”，不会自动重跑。

调度槽位 `t_comfyui_config.id=1` 当前已释放为 `is_active=1`。新建任务可以直接重新验证完整链路；如果要让旧失败任务重跑，需要人工把指定任务状态改回待处理。

## 优化点

- 后续可以把 `_convert_audio_to_wav` 的真实转换行为做更细的单元测试，目前测试重点是防止重新依赖 Python `ffmpeg` wrapper。
- h20 的配置日志仍可能输出敏感配置，排查时不要复制完整日志。
