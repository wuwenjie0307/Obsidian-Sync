---
date: "2026-07-01"
project: "joying-bot-server"
type: bug
status: open
severity: high
tags: [bug, prod, release, scheduler, voxcpm, latentsync, model-pool]
aliases: ["生产发版中断任务后模型容器状态不同步"]
---

# 生产发版中断任务后模型容器状态不同步

## 图谱链接
- 项目: [[projects/joying-bot-server/00-项目概览|joying-bot-server]]
- Bug 索引: [[projects/joying-bot-server/bugs/00-bugs-index|00-bugs-index]]
- 相关记录:
  - [[projects/joying-bot-server/bugs/prod-voxcpm-port-mapping-healthcheck-fix-2026-06-29|正式服音色克隆容器启动后访问不到应用]]
  - [[projects/joying-bot-server/bugs/prod-video-stale-timeout-mismatch-2026-06-30|生产视频模型超时与 scheduler 卡死保护不一致]]
  - [[projects/joying-bot-server/docs/prod-vibevideo-master-release-runbook-2026-06-30|正式服 vibevideo master 上线 runbook]]

## 问题描述
正式服发版后，视频任务出现“声音克隆阶段失败”。排查发现不是模型健康检查整体挂了，而是发版期间后端 / scheduler 中断了旧任务并释放了数据库里的模型池锁，但部分模型容器内部可能还在继续跑已经接收的旧请求。

随后新版本 scheduler 重新领取新任务，数据库看起来可调度，但容器内部仍然 busy，VoxCPM 返回 503 “服务繁忙，请稍后重试”。当前代码没有把这个 503 busy 当成可重试模型繁忙，而是直接回调成失败。

## 现象
- 正式服任务示例: `task_id=18088`，`job_id=20594`，`t_video_generate_task.id=18081`
- 失败原因: `声音克隆阶段失败`
- 模型池配置: `config_id=28`
- VoxCPM 地址: `http://192.192.168.47:8116`
- 对应视频容器: `http://192.192.168.139:6012`
- 日志核心报错: `VoxCPM API 返回 503: VoxCPM 服务繁忙，请稍后重试`
- LLM76 上 `8110-8119`、`8120-8124` 的 `/health` 均返回 `ok`，说明容器不是简单宕机，而是容器内部仍处于繁忙状态。

## 复现步骤
1. 正式服有视频任务正在 VoxCPM / 唇形 / 视频模型阶段运行。
2. 发版重启 BotServer / scheduler，并按当前逻辑中断任务、回调失败、释放模型池锁。
3. 新版本 scheduler 启动后领取新任务，调度到同一个模型容器。
4. 容器内部旧请求尚未结束，新请求进入后返回 busy / 503。
5. 后端把 busy 当成业务失败，导致前端看到音色克隆失败或视频生成失败。

## 期望行为
发版中断属于系统中断，不应该直接变成业务失败。模型容器、数据库调度锁、任务状态要保持一致：要么等旧请求跑完再恢复调度，要么统一重启模型容器后再释放锁并让任务重试。

## 实际行为
数据库 `t_comfyui_config.is_active` 锁被释放或恢复后，scheduler 认为容器可用；但容器内部还有旧请求占用，导致新任务撞上容器内部锁，返回 503 busy。由于 503 busy 没有被识别为可重试，任务被直接标记失败并回调。

## 原因
这里有两层状态：

- 数据库调度锁: `t_comfyui_config.is_active`
- 容器内部锁: VoxCPM / 唇形模型服务进程里的 semaphore 或实际推理占用

发版只处理了后端任务和数据库锁，没有同步处理模型容器内部正在跑的旧请求，所以出现“数据库认为空闲，但容器实际还忙”的状态漂移。

另外，之前已经把视频模型轮询超时和 scheduler 卡死保护补到 7200 秒，但这次是另一个问题：VoxCPM 返回 503 busy 后，业务代码没有把它纳入模型繁忙重试逻辑。

## 解决方案
短期处理：

1. 发版前先暂停 scheduler，避免继续领取新任务。
2. 如果发版会中断正在处理的任务，就同步重启相关模型容器，包括 VoxCPM、LatentSync / 唇形、HeyGem / duix。
3. 等容器 `/health` 正常后，只恢复确认卡住的 `is_active=2` 视频模型池配置为 `1`，不要动原本主动下线的 `is_active=0`。
4. 对发版期间被误打失败的 busy 类任务，改回待执行或进入重试队列，不直接回调终态失败。

代码兜底：

1. 将 VoxCPM `503 / 服务繁忙` 纳入 `is_video_model_busy_error` 可重试识别。
2. 对唇形模型、视频模型、音色克隆模型统一做 busy / timeout / stale 的可重试分类。
3. 发版中断导致的任务失败单独标记为系统中断，不作为业务失败回调给前端。
4. scheduler 启动时增加清理逻辑，识别上一次进程遗留的锁和 processing 任务，按规则恢复或重试。

## 优化点
- 增加发布维护开关：发版期间 scheduler 不再领取新任务。
- 引入模型池锁租约字段，例如 `locked_at`、`owner`、`run_id`，避免单纯依赖 `is_active` 判断状态。
- 模型服务支持 cancel / job_id 查询会更稳，可以在发版前主动取消或确认旧请求状态。
- Jenkins 发版流程里补“停调度 -> 等待/中断 -> 重启模型容器 -> 健康检查 -> 恢复锁 -> 启动调度”的顺序。

## 验证结果
- LLM76 scheduler 已确认运行在新版目录 `/data/project/prod_ai_botserver.20260701003143`。
- 正式库任务日志确认 `task_id=18088` 是 VoxCPM 503 busy 后被标记为声音克隆失败。
- LLM76 上 VoxCPM 端口 `8110-8119` 和试听端口 `8120-8124` 健康检查均为 `ok`。
- 本地已补充并暂存 VoxCPM busy 可重试兜底代码和回归测试，尚未提交、尚未推送，避免未确认前污染 master。

## 相关文件
- `scheduler/collect_scheduler.py`
- `router/service/video_server/video_gen_service.py`
- `router/service/video_server2/video_gen_service.py`
- `router/service/video_server/voxcpm_api.py`
- `router/service/video_server2/voxcpm_tts.py`
- `router/service/video_server2/video_work.py`
