---
date: "2026-06-02"
tags: [changelog, h20, latentsync, docker, timeout, video-generation]
---

# h20 LatentSync Docker 超时排查与修复 2026-06-02

## 背景

h20 测试服切到 Docker 模型链路后，产品提交的部分视频任务出现“视频合成阶段失败”。本次排查重点对比裸机 LatentSync `8101` 与 Docker LatentSync `8121` 的差异，并确认失败是否由 Docker 环境导致。

## 结论

- Docker LatentSync 不是完全不可用，`task_id=1025`、`task_id=1026` 已在 Docker 链路下端到端生成成功。
- `task_id=1024` 失败的直接原因是 LatentSync 超过 1800 秒超时阈值：Bot 客户端等待 `8121` 超时，任务被标记为“视频合成阶段失败”。
- 同时 `latentsync_api.py` 服务端内部也有 `subprocess.run(..., timeout=1800)`，长视频可能被服务端自身超时杀掉。
- 裸机 `8101` 与 Docker `8121` 使用同一份 `latentsync_api.py` API 代码，默认参数相同：`inference_steps=30`、`guidance_scale=1.8`。
- 差异主要是运行环境：
  - 裸机：Python 3.10.20、Torch 2.5.1+cu121、conda `latentsync`。
  - Docker：Python 3.11.14、Torch 2.9.1+cu128、容器内 `/opt/latentsync-venv`。
- Docker 目前能跑通，但耗时波动较大；超过 30 分钟的视频任务会被旧超时误判失败。

## 任务观察

- `task_id=1024 / job_id=1033`
  - 11:41 开始调用 LatentSync Docker。
  - 12:11 Bot 侧报 `Read timed out (read timeout=1800)`。
  - 最终落库失败：`视频合成阶段失败`。
  - 调度锁后续释放成功。

- `task_id=1025 / job_id=1034`
  - 12:27 开始处理。
  - 12:49 LatentSync Docker 返回成功。
  - 13:06 最终视频生成成功并回调 CRM。
  - 最终视频：`https://videos-test.joyingai.cn/video/crm/20260602/user4_1780376853683_4d2b6e54ae822363.mp4`
  - 最终视频时长：约 84 秒。

- `task_id=1026 / job_id=1035`
  - Docker 链路下已成功，`task_status=3`。

## 已实施修复

本地仓库与 h20 当前部署均已改动：

- `router/service/video_server2/latentsync_service.py`
  - Bot 调 LatentSync API 的客户端超时默认从 `1800` 调整到 `7200` 秒。
  - 支持环境变量 `LATENTSYNC_CLIENT_TIMEOUT_SECONDS` 覆盖。

- `router/service/video_server/latentsync_service.py`
  - 同步上述客户端超时修复，保持旧路径一致。

- `router/service/video_server/latentsync_api.py`
  - LatentSync 服务端内部 `scripts.inference` 超时从 `1800` 调整到 `7200` 秒。
  - 支持环境变量 `LATENTSYNC_INFERENCE_TIMEOUT_SECONDS` 覆盖。

## h20 部署动作

执行时间：2026-06-02 13:26 CST。

- 暂停 `ai_botserver_sch`。
- 备份并替换 h20 当前部署目录下 3 个文件。
- 编译检查通过。
- 将新的 `latentsync_api.py` 复制进 `latentsync-api-h20-test` 容器。
- 重启 `latentsync-api-h20-test`。
- 健康检查通过：`127.0.0.1:8121/health -> ok`。
- 重启 `ai_botserver_sch`。

备份文件后缀：`.bak.timeout_20260602132632`。

## 当前状态

- `ai_botserver`：运行中。
- `ai_botserver_sch`：运行中。
- VoxCPM Docker `8120`：健康。
- LatentSync Docker `8121`：健康。
- `t_comfyui_config.id=1` 在 `task_id=1025/1026` 成功后能正常释放并继续领取任务。

## 后续建议

- 继续观察后续较长视频任务是否还能触发超时。
- 如果 7200 秒仍不够，优先做耗时拆解：下载、VoxCPM、LatentSync 推理、尺寸转换、字幕、BGM、封面、上传分别打点。
- Docker 镜像后续需要把该超时修复固化进 Dockerfile 或重新构建镜像；当前 h20 容器内补丁属于测试服热修复，容器重建后会丢失。
- 长期方案不只是加超时，还要评估 LatentSync Docker 环境与裸机环境是否应对齐到 Python 3.10 + Torch 2.5/cu121，减少性能和兼容性不确定性。
