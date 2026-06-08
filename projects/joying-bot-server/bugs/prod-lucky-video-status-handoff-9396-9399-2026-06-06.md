---
date: "2026-06-08"
incident_date: "2026-06-06"
status: fixed
severity: medium
tags: [bug, production, lucky-prod, video-generation, crm-sync, scheduler, run-log]
---

# 正式服 lucky-prod 任务 9396/9399 视频合成阶段失败但本地未进入生成管线

## 问题描述

2026-06-06 晚上，前端“我的作品”里用户谭慧的两个视频任务失败，前端展示失败原因均为“视频合成阶段失败”。截图里的两个任务是：

| 任务 | 标题 | 提交时间 CST | 前端完成/失败时间 CST |
|---|---|---:|---:|
| `9396` / job `10078` | 捡漏状元府第泉中庭精装两房 | `2026-06-06 22:53:19` | `2026-06-06 23:03:51` |
| `9399` / job `10081` | 状元府第一套全中庭的两房 | `2026-06-06 23:07:43` | `2026-06-06 23:11:15` |

这次现象和 2026-06-04 的 `6014` 旧口型 Docker busy 不同：没有看到 `/easy/submit`、`忙碌中`、`任务提交失败` 或 Docker 端口证据；本地 lucky-prod 日志只看到 CRM 同步和轻量预处理，没有看到本地视频生成管线真正启动。

## 复现/定位线索

前端只给截图时，可以用标题、用户、提交时间反查 lucky-prod 的任务表。本次定位到 `zhugedata.t_video_generate_task`：

| local id | task_id | job_id | job_name | 用户 | task_status | fail_reason | 输出 |
|---:|---:|---:|---|---|---:|---|---|
| `9403` | `9396` | `10078` | `C1270T0U6062T20260606225319` | 谭慧 / `6062` | `4` | 视频合成阶段失败 | `generate_video_url=''`, `video_source_url=''` |
| `9406` | `9399` | `10081` | `C1270T0U6062T20260606230743` | 谭慧 / `6062` | `4` | 视频合成阶段失败 | `generate_video_url=''`, `video_source_url=''` |

补充状态：两条记录 `progress=0`，`finish_time=0`；`t_video_material_template` 中没有 `job_id IN (10078, 10081)` 的素材模板行。

注意时间：`task_created_at` 对应前端 CST 时间；DB 的 `created_time/updated_time` 看起来是 UTC-ish，需要加 8 小时和前端显示时间对齐。例如 `updated_time=2026-06-06 15:03:52` 对应前端约 `23:03:52`。

## 环境信息

本次排查的正确链路不是旧 `/data/project/prod_ai_autodone`，而是 lucky-prod：

| 项目 | 值 |
|---|---|
| 服务器 | `222.71.55.27:9527` |
| API/main 目录 | `/data/projects/joying-bot-server-lucky-prod` |
| API/main 进程 | `python app_server_lucky_prod.py` |
| scheduler 进程 | `python app_server_lucky_sch.py` |
| scheduler cwd 现场 | `/data/projects/joying-bot-server-lucky-test-deepseek` |
| 主要日志 | `/data/projects/joying-bot-server-lucky-prod/logs/run.log.2026-06-06` |
| 相关 DB | MySQL `zhugedata` |
| 相关表 | `t_video_generate_task` |

`scheduler cwd` 这一点很容易误判：进程名看起来是 lucky scheduler，但 cwd 在 `joying-bot-server-lucky-test-deepseek`，下次不要只看目录名或旧文档路径，要用进程 cwd 反查实际运行位置。

## 实际证据

`/data/project/prod_ai_autodone/logs/run.log.2026-06-06` 在截图时间段没有对应待生成任务，也没有 `视频合成失败`、`任务提交失败`、`忙碌中`、`easy/submit` 等证据；旧库 `ai_crm` 的视频记录最新只到 `2026-06-05`，找不到截图里的两个任务。因此排除旧 `prod_ai_autodone` / `6014 busy` 链路。

lucky-prod 的 `run.log.2026-06-06` 能看到两条任务被同步并做了轻量预处理：

- `9396` / `10078`：`22:53:20` 同步 CRM job/task，随后 `async preprocessing`，封面跳过、描述跳过、个人字幕无需改写，几十毫秒结束。
- `9399` / `10081`：`23:07:43` 同步 CRM job/task，随后同样完成轻量预处理。

同一日志还能看到重跑接口被调用：

- `9396`：`22:54:15` 和 `23:03:27` 记录“视频任务重新合成9396 当前状态参数为：4 当前的错误原因为：视频合成阶段失败”，随后“9396视频已重置”。
- `9399`：`23:10:48` 到 `23:10:49` 记录“视频任务重新合成9399 当前状态参数为：4 当前的错误原因为：视频合成阶段失败”，随后“9399视频已重置”。

关键缺失证据：

- 没有 `[处理任务-生成开始] job_id=10078 task_id=9396`
- 没有 `[处理任务-生成开始] job_id=10081 task_id=9399`
- 没有 `video_work.py` / `video_gen_service.py` 针对 `9396/9399` 的日志
- 没有 `/easy/submit`
- 没有 `任务提交失败` / `忙碌中`
- `joy-bot-error.log` 没有看到这两个 task 的有效异常

## 原因

已确认的直接状态是：lucky-prod 本地表里两个任务最终都处于 `task_status=4`，`fail_reason=视频合成阶段失败`，但生产日志没有留下进入本地视频生成管线的证据。它更像是 CRM 同步、重跑接口和 scheduler 取任务之间的状态/队列交接问题，而不是旧口型 Docker busy 或模型合成本身失败。

高度怀疑方向：`/video_generated_again` 只重置了本地 `t_video_generate_task`，随后被 CRM 同步或外部状态回写重新覆盖为失败；或者 scheduler 的查询条件、运行目录、锁状态导致 reset 后没有 pick up 任务。这个结论目前是基于日志缺失和状态变化的推断，尚未通过代码级修复或现场复现完全闭环。

## 解决方案

本次只做只读排查：未修改正式服 DB，未重启服务，未改代码。

下次遇到同类截图时，先按以下顺序定位：

1. 先区分服务线：旧口型 `/data/project/prod_ai_autodone` 还是 lucky-prod `/data/projects/joying-bot-server-lucky-prod`。
2. 如果旧链路没有任务、没有 `/easy/submit`、旧库也没有记录，立即转查 lucky-prod。
3. 在 `zhugedata.t_video_generate_task` 里用用户、标题、提交时间或 `job_name` 反查 `task_id/job_id`。
4. grep lucky-prod 当天 `run.log.YYYY-MM-DD`，同时查 `task_id`、`job_id`、`job_name`、`接收到的task_id为`、`处理任务-生成开始`。
5. 如果只看到同步/预处理/重置，没有看到 `[处理任务-生成开始]`，优先按“状态同步/队列交接”排查，不要直接去重启 Docker。
6. 如果需要人工重跑，先确认 CRM 侧状态是否也要协调重置，避免本地刚 reset 又被同步覆盖回失败。

## 优化点

- 在 lucky scheduler 的任务扫描处加日志：每轮待处理数量、查询条件、跳过原因、锁状态、当前 cwd/config 来源。
- 在 CRM 同步逻辑里记录“覆盖本地 task_status/fail_reason”的旧值和新值，尤其是 terminal state 覆盖 reset state 的场景。
- `/video_generated_again` 返回成功前后，记录是否同步处理 CRM 侧状态；如果只 reset 本地，需要在接口返回或运维手册里明确风险。
- 给 `task_id/job_id/job_name/user_id/company_id` 建一条固定排查 SQL 模板，避免只有截图时来回猜库和链路。
- 把“没有生成开始日志”作为一类明确告警：失败不是一定发生在模型合成阶段，也可能是状态机提前失败或被外部同步覆盖。

## 修复结果

- 重试接口 `video_generated_again` 现在会给本地任务打上新的 `task_updated_at` 标记，并清空 `progress` / `fail_reason`。
- CRM 同步逻辑在本地记录比 CRM 更新得更晚时，会保留本地重试态，不再把 `task_status` / `fail_reason` 覆盖回旧失败态。
- 已新增回归测试 `test/test_video_task_retry_handoff.py`，并通过了 `python -m unittest test.test_video_task_retry_handoff -v`。
## 本次排查踩坑

- 先按旧 Obsidian 文档去了 `/data/project/prod_ai_autodone/logs/run.log`，但截图任务不在旧链路里；这个路径只适合旧口型生产链路。
- 旧 `ai_crm` 库没有截图任务，且最新记录只到 `2026-06-05`，继续在旧库查会浪费时间。
- `run.log` 会按天滚动，现场要查 `run.log.2026-06-06`，不要只 tail 当前 `run.log`。
- DB 的 `created_time/updated_time` 和前端 CST 有 8 小时时差；不换算会误以为时间对不上。
- 看到“视频已重置”不能等价理解为“已经重新进入生成”；本次 reset 后仍没有看到生成开始日志。
- 没看到 `视频合成阶段失败` 的本地异常堆栈，不代表前端失败是假；状态可能来自 CRM/同步链路。
- scheduler 的实际 cwd 和目录名容易迷惑，下次要用进程 cwd 确认实际运行配置。
- 本地 CodeGraph 没初始化，结构性代码查询不可用；这类现场排查仍要优先以生产日志、DB 和进程 cwd 为准。

## 相关文件

- `/data/projects/joying-bot-server-lucky-prod/logs/run.log.2026-06-06`
- `/data/projects/joying-bot-server-lucky-prod/nohup.out`
- `/data/projects/joying-bot-server-lucky-prod/joy-bot-error.log`
- `/data/projects/joying-bot-server-lucky-prod/router/crm_server.py`
- `/data/projects/joying-bot-server-lucky-test-deepseek/config.json`
- 本地参考代码：`C:\Users\admin\Desktop\joyingbot-new\scheduler\collect_scheduler.py`
- 本地参考代码：`C:\Users\admin\Desktop\joyingbot-new\router\service\video_server\video_work.py`
- 排查手册：[[projects/joying-bot-server/docs/正式服视频合成失败日志排查|正式服视频合成失败日志排查]]