---
date: "2026-06-01"
tags: [changelog, h20, latentsync, video-generation, config]
---

# h20 LatentSync guidance_scale 调整为 1.8

## 改动类型

- [x] config change
- [x] deployment verification

## 背景

产品反馈处理后视频画面和原视频画质存在明显差异，要求在 h20 测试服把当前启动的 LatentSync `guidance_scale` 从 `1.7` 调整为 `1.8` 继续试测。

初步判断：截图中的脸部变软、肤色/曝光和背景灰度变化，更像 LatentSync 生成式唇形同步阶段带来的画面重绘/融合差异；ffmpeg 后续二次编码会叠加压缩损失，但通常不是这种整体观感变化的唯一原因。

## 改动内容

h20 当前运行的 LatentSync 8101 进程工作目录为：

- `/data/projects/joyingbot-new`

已修改以下文件中的默认值：

- `/data/projects/joyingbot-new/router/service/video_server/latentsync_api.py`
- `/data/project/test_ai_botserver.20260601193716/router/service/video_server/latentsync_api.py`

修改点：

```python
guidance_scale: float = Field(default=1.8, description="引导比例")
```

## 备份

- `/data/projects/joyingbot-new/router/service/video_server/latentsync_api.py.bak.20260601193853`
- `/data/project/test_ai_botserver.20260601193716/router/service/video_server/latentsync_api.py.bak.20260601193853`

## 重启与验证

- 仅重启 h20 LatentSync API `8101`，未重启 Bot、VoxCPM 或其他服务。
- 新进程：
  - parent PID: `1879303`
  - worker PID: `1879348`
- `http://127.0.0.1:8101/health` 返回 `{"status":"ok"}`。
- 远程 `py_compile` 在停止旧进程前已通过，否则脚本不会进入重启阶段。

## 操作备注

第一次停止旧进程时，PID 匹配表达式把当前远程检查 shell 也匹配进去了，导致连接提前断开。随后重新登录 h20，确认 8101 没有运行后，已从 `/data/projects/joyingbot-new` 重新拉起 LatentSync API 并完成健康检查。

## 后续建议

如果 `guidance_scale=1.8` 仍有明显画质差异，需要拿同一任务的三个阶段视频做定量对比：原始输入、LatentSync 输出、字幕/BGM/封面后最终输出。优先比较分辨率、fps、bitrate、codec、pix_fmt、色彩信息和单帧截图，再判断是否需要降低 ffmpeg 压缩损失或调整 LatentSync 预处理/后处理参数。

## 追加核验记录

最终核验时发现 `/data/project/test_ai_botserver` 软链已从 `test_ai_botserver.20260601193716` 切到新的 `test_ai_botserver.20260601194116`。新的软链目标文件仍为 `guidance_scale=1.7`。

当前实际运行的 LatentSync 8101 进程仍来自 `/data/projects/joyingbot-new`，该运行文件已是 `guidance_scale=1.8`，且 `8101/health` 返回 `{"status":"ok"}`。

尝试补丁当前软链目标时，远程写操作授权被拒绝，因此没有修改 `test_ai_botserver.20260601194116`。后续如果 8101 改为从 `/data/project/test_ai_botserver` 启动，需要先把该目录的 `latentsync_api.py` 也同步为 `1.8`。
