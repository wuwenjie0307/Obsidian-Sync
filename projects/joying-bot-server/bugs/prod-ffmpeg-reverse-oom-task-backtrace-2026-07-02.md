---
date: "2026-07-02"
project: "joying-bot-server"
type: bug
status: investigation
severity: high
tags: [bug, prod, ffmpeg, oom, video-time-align, scheduler]
aliases: ["生产 ffmpeg reverse OOM 任务反查"]
---

# 生产 ffmpeg reverse OOM 任务反查

## 图谱链接

- 项目: [[projects/joying-bot-server/00-项目概览|joying-bot-server]]
- 索引: [[projects/joying-bot-server/bugs/00-bugs-index|Bug 记录索引]]

## 问题描述

2026-07-02 生产环境多条视频任务出现：

```text
auto cleanup: scheduler restarted; interrupted task cancelled and model pool released
```

前一条记录已经确认：该失败原因由 scheduler 重启后的启动清理逻辑写入。这里记录进一步反查：到底是哪类任务导致 scheduler 被重启。

## 反查结论

触发点集中在视频时长对齐链路的“正反循环扩展”逻辑，也就是视频素材时长短于克隆音频时，代码会创建反向视频再拼接补足时长。

高风险 ffmpeg 阶段：

```text
正在创建反向视频...
ffmpeg -vf reverse -af areverse
```

`reverse / areverse` 会缓存大量视频帧或音频数据再倒放。对 1080x1920、几十秒的视频，叠加并发后内存占用会非常夸张，具备把系统打到 OOM 的风险。

## 关键证据

09:38 批次基本可以定位到 `task_id=18689`：

```text
09:38:45 ffmpeg invoked oom-killer
09:38:45 Out of memory: Killed process ... (ffmpeg)
09:38:46 supervisor.service: Failed with result 'oom-kill'
09:38:45 task_id=18689 创建反向视频失败
```

`task_id=18689` 在业务日志里同一秒报“创建反向视频失败”，和系统 OOM 时间完全对上。

15:33 批次最可疑的是 `task_id=18826`：

```text
18826 source_video_duration=37.800s clone_audio_duration=44.800s
18826 视频时长不足，需要正反循环扩展
18826 正在创建反向视频...
15:33:12 ffmpeg invoked oom-killer
15:33:12 Out of memory: Killed process ... (ffmpeg)
```

同一时间附近 `task_id=18827` 已完成反向视频并进入拼接，`task_id=18824` 也在执行其他 ffmpeg 处理。15:33 这次属于多个 ffmpeg 任务并发叠加，但直接风险最高的仍是 `18826` 的反向视频创建阶段。

## 涉及代码

本地代码位置：

```text
router/service/video_server2/video_time_align.py
```

核心逻辑：

```text
视频时长不足，需要正反循环扩展
-> 创建反向视频
-> ffmpeg reverse / areverse
-> 拼接补足音频时长
```

## 根因判断

这不是前端问题，也不是普通模型池 busy 问题。

更准确的链路是：

```text
高内存 ffmpeg reverse 任务
-> Linux OOM killer 杀掉 ffmpeg
-> supervisor.service 被 systemd 判定 oom-kill 失败
-> supervisor 自动重启
-> ai_botserver_sch 跟着重启
-> scheduler 启动清理把 task_status=1/2 的任务置失败
```

所以 `auto cleanup` 是结果，不是根因；根因在 ffmpeg reverse 这类高内存处理。

## 修复方向

优先级最高：

- 避免对长视频或高分辨率视频直接使用 `reverse / areverse`。
- 用低内存的 forward loop / trim 方案替代正反循环补时长。
- 或者至少对“创建反向视频”阶段做并发限制，避免多个 reverse ffmpeg 同时跑。

辅助优化：

- 给 ffmpeg 子进程日志增加阶段名、task_id、子进程 PID、输入视频参数和命令摘要，后续可以从系统日志 PID 精确反查到任务。
- 对高风险 ffmpeg 阶段增加更细的耗时和内存风险标记。
- scheduler 启动清理不应无差别把处理中任务都置失败，后续可考虑安全回队或只处理明确不可恢复任务。

## 当前状态

已确认问题方向，尚未在代码层修复。

如果要修，最小可控方案是先替换 `video_time_align.py` 里的 reverse 补时长逻辑，避免继续使用内存不可控的反向滤镜。

## 相关文件

- `router/service/video_server2/video_time_align.py`
- `scheduler/collect_scheduler.py`
- `app_server_sch.py`
- 生产 scheduler 日志: `/data/server_logs/supervisord/botserver_sch.out`
- 生产业务日志: `/data/project/prod_ai_botserver/logs/run.log`
- 系统日志: `/var/log/syslog`

## 相关记录

- [[projects/joying-bot-server/bugs/prod-scheduler-ffmpeg-oom-auto-cleanup-2026-07-02|生产 scheduler OOM 重启触发 auto cleanup 任务失败]]
