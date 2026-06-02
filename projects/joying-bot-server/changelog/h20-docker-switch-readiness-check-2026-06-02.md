---
date: "2026-06-02"
tags: [changelog, h20, docker, queue, readiness-check, crm]
---

# h20 Docker 切换前只读检查 2026-06-02

## 背景

继续执行 h20 VoxCPM / LatentSync Docker 计划前，先按低风险方式做只读检查，判断是否可以把 Bot 临时切到 Docker 旁路服务：

- VoxCPM Docker: `http://127.0.0.1:8120`
- LatentSync Docker: `http://127.0.0.1:8121`

本次只读检查未修改 h20 配置，未重启服务，未修改数据库。

## 检查时间

```text
2026-06-02 10:57-11:01 CST
h20 hostname: hgx19
```

## 服务状态

Supervisor：

```text
ai_botserver: RUNNING
ai_botserver_sch: RUNNING
ai_botserver_sch_video: STOPPED
```

进程/端口：

```text
Bot 8017: running
Bot 8100: running
VoxCPM bare-metal 8110: running
LatentSync bare-metal 8101: running
VoxCPM Docker 8120: running, healthy
LatentSync Docker 8121: running, healthy
Whisper 8188: running
```

健康检查：

```text
127.0.0.1:8017/status/check -> ok
127.0.0.1:8100/status/check -> ok
127.0.0.1:8110/health -> ok
127.0.0.1:8101/health -> ok
127.0.0.1:8120/health -> ok
127.0.0.1:8121/health -> ok
```

当前 Bot 配置仍走裸机模型服务：

```json
{
  "server_port": 8100,
  "voxcpm_api_base": "http://127.0.0.1:8110",
  "latentsync_api_base": "http://127.0.0.1:8101",
  "h20_api_base": "http://127.0.0.1:8110"
}
```

## 测试库队列状态

`t_video_generate_task` 状态统计：

```text
task_status=0: 18 条待处理
task_status=2: 1 条处理中
task_status=3: 466 条成功
task_status=4: 341 条失败
```

当前处理中任务：

```text
id=1211
job_id=1008
task_id=999
task_status=2
progress=0
callback_status=1
created_time=2026-06-01 12:04:50
updated_time=2026-06-01 12:05:52
finish_time=0
voice_emotion=1
voice_speed=1.0
voice_volume=50
```

`task_id=999` 从 2026-06-01 12:05:52 后没有更新，结合当前调度日志判断，更像是历史卡住任务，不是正常正在处理。

`t_comfyui_config` 当前锁状态：

```text
id=1
config_value=http://60.171.65.125:30278
config_value_audio=http://127.0.0.1:6004
is_active=2
updated_time=2026-06-01 12:04:58
```

其他配置行 `is_active=0`，当前没有 `is_active=1` 的可用配置。

调度日志最新结论：

```text
待生成任务数: 18
可用配置数: 0
没有可用配置（is_active=1），跳过处理，等待下一次执行
```

## 结论

当前不适合把 Bot 临时切到 Docker `8120/8121`。

原因：

- 测试库还有 18 个待处理任务。
- 有 1 个疑似历史卡住的处理中任务 `task_id=999`。
- `t_comfyui_config.id=1` 仍是 `is_active=2`，调度锁被占用。
- 调度目前没有可用生成槽位。

Docker 本身状态正常，阻塞点不是 Docker，而是测试库任务队列和调度锁状态。

## 下一步建议

如果要继续 Docker 受控验证，需要先由用户确认是否允许处理测试库队列：

1. 把疑似卡住的 `task_id=999 / job_id=1008` 标记失败或取消。
2. 释放 `t_comfyui_config.id=1` 为 `is_active=1`。
3. 视产品测试情况，决定是否清理或保留 18 条待处理任务。
4. 确认没有重要产品任务后，再临时把 Bot 模型地址切到 Docker：

```json
{
  "voxcpm_api_base": "http://127.0.0.1:8120",
  "latentsync_api_base": "http://127.0.0.1:8121"
}
```

5. 只提交 1 个 CRM 视频任务做端到端验证。
6. 验证通过后，再进入代码改造：让调度按 `t_comfyui_config.config_value_audio/config_value` 传递 VoxCPM/LatentSync Docker 地址。

## 安全备注

- 本次未写入数据库。
- 本次未重启服务。
- 本次未切换 Bot 配置。
- 日志中存在敏感配置输出，后续整理给用户或写 Obsidian 时必须脱敏。

## 2026-06-02 11:07 队列清理执行结果

已执行测试库旧任务清理：

```text
备份文件：/tmp/h20_docker_queue_cleanup_20260602110650.jsonl
清理任务数：19
清理范围：id=1211~1229，原 task_status in (0,2)
释放锁：t_comfyui_config.id=1 -> is_active=1
```

清理后修正了 `fail_reason` 为 ASCII，避免远程终端编码导致中文乱码：

```text
id=1211: docker verification cleanup: stale processing test task
id=1212~1229: docker verification cleanup: historical pending test task
```

## 2026-06-02 11:10 复查发现新任务被领取

释放锁后，调度很快领取了一个新任务：

```text
id=1230
job_id=1027
task_id=1018
task_status=2
progress=0
callback_status=1
created_time=2026-06-02 03:08:30
updated_time=2026-06-02 03:09:24
voice_emotion=1
voice_speed=1.0
voice_volume=50
```

同时 `t_comfyui_config.id=1` 又变回 `is_active=2`。

判断：这是清理后新进入/新领取的任务，不属于刚才备份清理的旧 19 条任务。可能是产品或前端新提交的测试任务。为了避免误杀有效测试任务，暂未取消该任务，也暂未切 Bot 到 Docker。

当前下一步需要人工确认：

- 如果这是产品正在测的任务：等待它跑完，再做 Docker 切换。
- 如果它也可以取消：先暂停/避开调度竞态，取消该任务并释放锁，然后立刻切 Bot 到 Docker 做单任务验证。

## 2026-06-02 11:15 新任务处理阶段补充

复查 `job_id=1027 / task_id=1018`：

```text
id=1230
task_status=2
progress=0
t_comfyui_config.id=1 is_active=2
```

裸机 VoxCPM 日志显示该任务已进入声音克隆阶段，当前仍走裸机模型服务，不是 Docker 服务：

```text
VoxCPM bare-metal: 127.0.0.1:8110
LatentSync bare-metal: 127.0.0.1:8101
```

处理原则：该任务可能是产品或前端新提交的有效测试任务，暂不取消，避免误杀当前测试。

继续 Docker 验证前需要：

1. 等该任务完成或由用户确认可以取消。
2. 让产品/前端暂停提交新视频任务，避免释放锁后被新任务抢占。
3. 队列和锁空闲后，再切 Bot 到 Docker `8120/8121`。

## 2026-06-02 11:20-11:30 Docker 切换执行结果

按用户确认，直接停掉当前新任务并继续 Docker 验证准备。

### 清理任务

已暂停调度后取消当前任务：

```text
id=1230
job_id=1027
task_id=1018
原状态：task_status=2
新状态：task_status=4
fail_reason=docker verification cleanup: cancelled active test task
```

取消后又发现额外待处理任务，已一起清理，避免 Docker 验证被旧任务抢占：

```text
备份文件：/tmp/h20_docker_extra_pending_cleanup_20260602111948.jsonl
清理任务数：4
清理后 task_status in (0,1,2) 数量：0
```

`t_comfyui_config.id=1` 已释放：

```text
is_active=1
```

### 配置切换

已备份 h20 当前 Bot 配置：

```text
/data/project/test_ai_botserver/config/config-dev.json.bak.docker_switch_20260602112129
```

已将当前测试 Bot 配置切到 Docker 旁路模型服务：

```json
{
  "h20_api_base": "http://127.0.0.1:8120",
  "voxcpm_api_base": "http://127.0.0.1:8120",
  "latentsync_api_base": "http://127.0.0.1:8121"
}
```

### 服务重启

已重启：

```text
ai_botserver: RUNNING, 8017
ai_botserver_sch: RUNNING
manual Bot: RUNNING, 8100
```

注意：8100 原来是旧部署目录进程：

```text
/data/project/test_ai_botserver.20260529211325
```

已按端口监听 PID 精确停止后，从当前部署目录重新启动：

```text
/data/project/test_ai_botserver
```

### 最终验证

h20 内部验证：

```text
127.0.0.1:8017/status/check -> ok
127.0.0.1:8100/status/check -> ok
127.0.0.1:8120/health -> ok
127.0.0.1:8121/health -> ok
```

测试库状态：

```text
t_video_generate_task task_status in (0,1,2): 0
t_comfyui_config.id=1 is_active=1
```

公网入口验证：

```text
从跳板/生产侧 curl http://223.112.222.90:48100/status/check -> {"status":"ok"}
```

本地当前执行环境直接 curl 公网入口未返回，但跳板/生产侧验证通过；以 CRM/生产侧网络结果为准。

## 当前可测试状态

现在 h20 测试服已处于可提交新视频任务状态：

```text
CRM -> 223.112.222.90:48100 -> h20 Bot 8100
Bot / scheduler -> VoxCPM Docker 8120
Bot / scheduler -> LatentSync Docker 8121
```

下一步：让产品/前端只提交 1 个新视频任务，观察是否端到端跑通 Docker 模型链路。不要一开始并发。

## 回滚信息

如 Docker 链路异常，可恢复配置备份：

```text
/data/project/test_ai_botserver/config/config-dev.json.bak.docker_switch_20260602112129
```

或手动将模型地址切回裸机：

```json
{
  "h20_api_base": "http://127.0.0.1:8110",
  "voxcpm_api_base": "http://127.0.0.1:8110",
  "latentsync_api_base": "http://127.0.0.1:8101"
}
```
