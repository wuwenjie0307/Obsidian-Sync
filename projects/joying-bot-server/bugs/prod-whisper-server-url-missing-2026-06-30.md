---
date: "2026-06-30"
project: "joying-bot-server"
type: bug
status: fixed
severity: high
tags: [bug, prod, whisper, scheduler, heygem, hyperframes, env]
aliases: ["正式服 HEYGEM_STANDARDIZE_FAILED 声音克隆阶段失败"]
---

# 正式服 HEYGEM_STANDARDIZE_FAILED 声音克隆阶段失败

## 问题描述

正式服网感视频任务失败，前端显示：

`HEYGEM_STANDARDIZE_FAILED: 声音克隆阶段失败`

## 复现步骤

1. 正式库创建 `templates_style_id=1/2` 的网感视频任务。
2. LLM-76 的 `ai_botserver_sch` 领取任务。
3. scheduler 进入 HyperFrames 前置标准化流程，调用 `build_heygem_standardized_video()`。
4. `video_work.py` 在 `reference_audio_whisper` 阶段调用独立 Whisper 服务。
5. LLM-76 scheduler 未配置 `WHISPER_SERVER_URL`，代码回退到默认 `http://127.0.0.1:8188/whisper/transcribe`。
6. LLM-76 本机没有 8188 Whisper 服务，连接失败，任务被标记为 `HEYGEM_STANDARDIZE_FAILED: 声音克隆阶段失败`。

## 期望行为

LLM-76 scheduler 应调用正式可用的 Whisper 服务完成参考音频转写，然后继续进入 VoxCPM 声音克隆和后续 HyperFrames 渲染。

## 实际行为

日志中 `task_id=17626` 和 `task_id=17627` 均在 `reference_audio_whisper` 后失败：

`HTTPConnectionPool(host='127.0.0.1', port=8188): Failed to establish a new connection: [Errno 111] Connection refused`

## 原因

正式部署职责为：

- LLM-74：正式主 API，`ai_botserver_api` 运行，且本机有 `whisper_service.py` 监听 8188。
- LLM-76：正式定时任务，`ai_botserver_sch` 运行，负责领取并执行视频生成任务。

代码默认从环境变量 `WHISPER_SERVER_URL` 读取独立 Whisper 地址；未配置时回退到 `127.0.0.1:8188`。H20 测试服本机有 8188，因此默认值可用；正式 LLM-76 本机没有 8188，因此需要显式指向 LLM-74 的 Whisper 服务。

## 解决方案

2026-06-30 00:34 CST 在 LLM-76 修复 `ai_botserver_sch` supervisor 环境：

1. 备份 `/etc/supervisord.d/ai_botserver_sch.conf` 到 `/etc/supervisord.d/ai_botserver_sch.conf.bak.20260630003430`。
2. 在 `environment=` 中追加：
   `WHISPER_SERVER_URL="http://192.192.168.139:8188/whisper/transcribe"`
3. 执行 `supervisorctl reread`，确认 `ai_botserver_sch: changed`。
4. 执行 `supervisorctl update ai_botserver_sch`，重新加载并启动进程组。
5. 新进程 PID 为 `578383`，状态 `RUNNING`。

## 优化点

- 正式发布 checklist 应明确：scheduler 所在机器如果没有本机 Whisper 服务，必须配置 `WHISPER_SERVER_URL`。
- H20 与正式服的“主服务 / 定时任务 / Whisper 服务”职责应记录成拓扑图，避免把主 API 机器和任务执行机器混淆。
- 新版本上线后应跑一个正式 smoke task，覆盖 `reference_audio_whisper -> voxcpm_clone -> hyperframes render` 全链路。

## 验证结果

2026-06-30 00:35 CST 修复后验证：

- LLM-76 `ai_botserver_sch` 新进程环境包含 `WHISPER_SERVER_URL=http://192.192.168.139:8188/whisper/transcribe`。
- 新进程仍保留 `H20_HYPERFRAMES_ROUTE_ENABLED=1`、`HF_RENDER_BACKEND=docker`、`HF_MAX_CONCURRENCY=7`、`HF_DOCKER_IMAGE=h20-hyperframes-renderer:0.6.42-node22.22.2`、`HF_DOCKER_BINARY=/data/script/hf-docker`。
- LLM-76 访问 LLM-74 Whisper 地址返回 HTTP 400，响应为 `audio_url is required`，说明服务和网络可达。
- 正式库 `2026-06-30 00:34:30 CST` 之后新增 `HEYGEM_STANDARDIZE_FAILED` 数为 0。
- 正式库 `2026-06-30 00:34:30 CST` 之后新增 `HYPERFRAMES_ROUTE_DISABLED` 数为 0。

历史失败任务已回调失败，不直接重置或重跑，避免重复回调或结算状态二次影响。

## 相关文件

- `router/service/video_server2/model_whisper_server.py`
- `router/service/video_server2/video_work.py`
- `scheduler/collect_scheduler.py`

## 相关记录

- [[projects/joying-bot-server/bugs/prod-hyperframes-route-disabled-env-missing-2026-06-30|正式服 HYPERFRAMES_ROUTE_DISABLED]]
- [[projects/joying-bot-server/docs/prod-test-hyperframes-runtime-config-check-2026-06-29|正式服 / 测试服 HyperFrames 配置对比]]
