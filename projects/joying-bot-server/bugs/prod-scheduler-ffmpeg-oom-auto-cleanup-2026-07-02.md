---
date: "2026-07-02"
project: "joying-bot-server"
type: bug
status: investigation
severity: high
tags: [bug, prod, scheduler, ffmpeg, oom, video-task, model-pool]
aliases: ["生产 scheduler OOM 重启触发 auto cleanup 任务失败"]
---

# 生产 scheduler OOM 重启触发 auto cleanup 任务失败

## 图谱链接

- 项目: [[projects/joying-bot-server/00-项目概览|joying-bot-server]]
- 索引: [[projects/joying-bot-server/bugs/00-bugs-index|Bug 记录索引]]

## 问题描述

2026-07-02 正式库多条视频任务失败，前端失败原因统一显示：

```text
auto cleanup: scheduler restarted; interrupted task cancelled and model pool released
```

涉及用户反馈任务包括：

- `task_id=18689`
- `task_id=18693`
- `task_id=18779`
- `task_id=18825`
- `task_id=18828`

## 实际行为

任务并不是在某个正常业务阶段主动失败，而是在 scheduler 进程重启后，被启动清理逻辑统一标记失败。

代码来源：

- `app_server_sch.py` 启动时调用 `cleanup_interrupted_video_tasks_on_scheduler_start()`
- `scheduler/collect_scheduler.py` 中该函数筛选 `task_status in (1, 2)` 的视频任务
- 命中任务被更新为失败，并写入固定失败原因：

```text
auto cleanup: scheduler restarted; interrupted task cancelled and model pool released
```

## 原因

LLM76 系统日志显示，scheduler 重启的直接原因是 `ffmpeg` 触发系统 OOM，导致 `supervisor.service` 被 systemd 判定失败并自动重启。

09:38 批次证据：

```text
09:38:45 ffmpeg invoked oom-killer
09:38:45 Out of memory: Killed process ... (ffmpeg)
09:38:46 supervisor.service: Failed with result 'oom-kill'
09:39:38 spawned: 'ai_botserver_sch'
```

15:33 批次证据：

```text
15:33:12 ffmpeg invoked oom-killer
15:33:12 Out of memory: Killed process ... (ffmpeg)
15:33:14 supervisor.service: Failed with result 'oom-kill'
15:34:05 spawned: 'ai_botserver_sch'
```

完整链路：

```text
ffmpeg 内存占用过高
-> Linux OOM killer 杀掉 ffmpeg
-> supervisor.service 被判定 oom-kill 失败
-> systemd 自动重启 supervisor
-> ai_botserver_sch 被重新拉起
-> scheduler 启动清理处理中任务
-> task_status=1/2 的视频任务被标失败并回调
```

## 与模型池保护的关系

这次 `auto cleanup` 失败不是 `MODEL_INSTANCE_BUSY` 唇形模型池卡死保护直接触发的。

`MODEL_INSTANCE_BUSY` 是模型实例忙碌时的隔离重试逻辑；本次失败原因来自 scheduler 启动清理逻辑。两者可能在同一时间段附近出现，但不是同一个直接触发源。

## 影响范围

该固定失败原因只应由 scheduler 启动清理逻辑产生。

普通 API 服务、前端页面、模型池 busy 隔离本身不会直接写入这条失败原因。它们最多间接导致 scheduler 被重启或任务状态变化，但只要没有执行 `cleanup_interrupted_video_tasks_on_scheduler_start()`，就不会出现这句固定文案。

## 解决方向

短期：

- 降低 `ffmpeg` OOM 风险，排查高内存 ffmpeg 任务来源。
- 避免 scheduler 重启时把 `task_status=1/2` 全部直接标失败。
- 启动清理可考虑改为释放模型池后让任务回到待处理，或者只处理确认已中断且不可恢复的任务。

中期：

- 对 ffmpeg 子进程增加资源限制、超时和更明确的阶段日志。
- 将 scheduler 与重型 ffmpeg 后处理隔离，避免一个 ffmpeg OOM 拖垮整个 supervisor 进程组。
- 部署/重启前先暂停领取新任务，等待处理中任务完成或安全回队。

## 验证结果

- 已在 LLM76 `/var/log/syslog` 查到两次 `ffmpeg invoked oom-killer` 与 `supervisor.service: Failed with result 'oom-kill'`。
- 已在 scheduler 日志查到对应时间点的 `video_restart_cleanup`：
  - `09:41:46 failed_tasks=2 released_model_configs=1`
  - `15:36:08 failed_tasks=5 released_model_configs=7`
- 已确认固定失败原因字符串在当前功能分支代码中只出现在 `scheduler/collect_scheduler.py` 的启动清理函数。

## 相关文件

- `app_server_sch.py`
- `scheduler/collect_scheduler.py`
- LLM76 日志：`/data/server_logs/supervisord/botserver_sch.out`
- LLM76 系统日志：`/var/log/syslog`

## 相关记录

- [[projects/joying-bot-server/bugs/prod-release-interrupt-model-container-state-drift-2026-07-01|生产发布中断任务后模型容器状态不同步]]
- [[projects/joying-bot-server/docs/prod-llm74-llm76-runtime-login-notes-2026-07-01|正式服 LLM74/LLM76 运行与登录记录]]
