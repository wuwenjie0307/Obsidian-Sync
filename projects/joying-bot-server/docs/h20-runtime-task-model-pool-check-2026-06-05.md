---
date: "2026-06-05"
tags: [h20, runtime-check, task-status, model-pool, scheduler, ops]
---

# h20 测试服任务与模型池运行巡检 2026-06-05

## 一句话结论

2026-06-05 17:08 CST 左右只读巡检显示：H20 测试服视频生成任务队列和模型池没有卡住；当前没有 `task_status IN (0,1,2)` 的待处理/处理中任务，也没有 `is_active=2` 的模型池占用锁残留。

需要单独留意的是：`18017` scheduler 进程 CPU 偏高，日志主要忙在微信/CRM 同步类任务，例如 `sync_bot_wxid` 返回 404、`get_friend_alias` 调用等；这不是视频生成模型池卡住，但属于运行噪音和潜在负载问题。

## 登录与检查方式

按 `logging-into-h20` 路线进入：

```text
Local -> Joying jump host: developer@222.71.55.27:9527
Jump host -> H20: sudo ssh -p 10019 root@h20
H20 hostname: hgx19
```

本次只做只读检查，没有重启服务、没有修改文件、没有写数据库。密码只在本次会话中临时使用，没有写入 Obsidian、Git、代码文件或最终回复。

## 服务进程快照

| 端口/进程 | PID | 启动时间 | 运行目录 | 状态 |
|---|---:|---|---|---|
| `8100 app_server_api.py` | `3918518` | 2026-06-05 14:22:59 | `/data/project/test_ai_botserver.20260605120425` | `/status/check` ok |
| `8017 app_server_api.py` | `3983401` | 2026-06-05 15:13:34 | `/data/project/test_ai_botserver.20260605151425` | `/status/check` ok |
| `18017 app_server_sch.py` | `3983402` | 2026-06-05 15:13:34 | `/data/project/test_ai_botserver.20260605151425` | scheduler 运行中 |

注意：`8100` 与 `8017/18017` 仍不是同一部署目录。后续排查不能只看健康检查，必须按端口确认 cwd。

## 任务表状态

查询库：`zhugedata_test`

表：`t_video_generate_task`

当前统计：

| 状态 | 数量 | 含义 |
|---:|---:|---|
| `3` | `537` | 成功 |
| `4` | `375` | 失败 |
| `0/1/2` | `0` | 当前无待处理/处理中任务 |

当前判断：

```text
task_status=0/1/2: 待处理、已领取或处理中
task_status=3: 成功
task_status=4: 失败
callback_status=1: 主回调成功
```

最近成功任务示例：

| 字段 | 值 |
|---|---|
| `id` | `1315` |
| `job_id` | `1112` |
| `task_id` | `1103` |
| `task_status` | `3` |
| `progress` | `100` |
| `callback_status` | `1` |
| `created_time` | `2026-06-05 08:42:20` |
| `updated_time` | `2026-06-05 08:49:59` |
| `generate_video_url` | 已生成并回填 |

最近失败记录中，`id=1311` 的失败原因是：

```text
上线前清理：历史卡住任务未生成视频，释放模型池资源
```

这是一条清理记录，不是当前新卡住任务。

## 模型池状态

表：`t_comfyui_config`

本次从当前运行代码 `scheduler/collect_scheduler.py` 再次确认了语义：

```text
is_active=1: 可用，scheduler 可领取
is_active=2: 使用中，任务占用
is_active=0: 禁用或不参与当前调度
```

当前启用的视频模型池：

| id | VoxCPM / audio | lip / avatar | is_active | 判断 |
|---:|---|---|---:|---|
| `16` | `http://127.0.0.1:8120` | `http://127.0.0.1:6004` | `1` | 可用 |
| `17` | `http://127.0.0.1:8122` | `http://127.0.0.1:6005` | `1` | 可用 |
| `18` | `http://127.0.0.1:8124` | `http://127.0.0.1:6006` | `1` | 可用 |
| `19` | `http://127.0.0.1:8126` | `http://127.0.0.1:6007` | `1` | 可用 |

没有 `is_active=2` 的视频模型池记录，因此没有看到模型池锁死。

试听池：

| id | endpoint | is_active |
|---:|---|---:|
| `12` | `8128` | `1` |
| `13` | `8129` | `1` |
| `14` | `8130` | `1` |
| `15` | `8131` | `1` |

## 模型服务健康检查

以下端口均返回健康：

```text
8120 ok
8121 ok
8122 ok
8123 ok
8124 ok
8125 ok
8126 ok
8127 ok
8128 ok
8129 ok
8130 ok
8131 ok
8110 ok
8101 ok
```

`8188 /health` 返回 404，这不等同于 Whisper 服务不可用；历史接口口径是 `POST /whisper/transcribe`。

Docker 容器状态：VoxCPM、LatentSync、试听 VoxCPM、duix avatar 容器都在运行，其中 VoxCPM/LatentSync/试听容器显示 healthy 或 up。

GPU 快照：8 张 H20 GPU 均有显存占用，但采样时 `utilization.gpu=0`，符合当前无视频生成任务的状态。

## Scheduler 日志观察

`logs/run.log` 最新视频生成定时任务显示：

```text
开始执行定时任务：generate_video_and_callback
待生成任务数: 0
无待生成任务。总任务数=912, task_status=0的任务数=0
结束执行定时任务：generate_video_and_callback
```

同一日志中有大量非视频生成链路日志：

```text
sync_bot_wxid response['code'] == 404
get_friend_alias result:{'friend_alias': None}
```

CPU 快照显示 `18017` scheduler 进程 `%CPU` 约 `257`，说明它在多线程/多核上比较忙。当前判断：这不是视频任务或模型池卡住，但如果后续要看整机负载，应单独排查微信/CRM 同步循环。

## 外部入口说明

本机直连 `http://223.112.222.90:48100/status/check` 超时，但 H20 内部 `127.0.0.1:8100/status/check` 正常。公网入口可能受网络策略、映射或访问来源限制影响，不能仅凭本机超时判断 H20 内部服务挂掉。

## 后续建议

1. 视频生成验收时继续按三层看：任务表 `task_status`、模型池 `is_active`、scheduler 日志。
2. 检查运行版本时继续按端口看 cwd，尤其 `8100` 和 `8017/18017`。
3. 如果 `18017` CPU 继续偏高，单独排查 `sync_bot_wxid` 404 与 `get_friend_alias` 调用频率。
4. 如果 CRM 反馈外部入口异常，再从允许访问的 CRM/跳板侧验证 `48100 -> 8100` 映射。

## 相关记录

- [[projects/joying-bot-server/docs/h20-test-task-status-db-check-2026-06-03|h20-test-task-status-db-check-2026-06-03]]
- [[projects/joying-bot-server/docs/h20-model-pool-ops-handoff-2026-06-02|h20-model-pool-ops-handoff-2026-06-02]]
- [[projects/joying-bot-server/docs/h20登录与排查Skill|h20登录与排查Skill]]
- [[projects/joying-bot-server/changelog/h20-8100-runtime-refresh-2026-06-05|h20-8100-runtime-refresh-2026-06-05]]
