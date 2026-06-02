---
date: "2026-06-02"
tags: [h20, docker, model-pool, ops, concurrency, voxcpm, latentsync]
---

# h20 模型池生产逻辑对齐与运维对接计划

## 当前一句话结论

h20 当前已经完成“CRM 调度链路 + `t_comfyui_config` 资源锁 + 按配置行调用 Docker 模型服务”的单实例闭环验证，和生产模型池调用逻辑的整体对齐度约 80%-85%。

如果只看核心调用链路：

```text
CRM 创建视频任务
-> /crm/generate_video_task
-> Bot 同步任务入库 t_video_generate_task
-> ai_botserver_sch 定时扫描 task_status=0
-> 领取 t_comfyui_config.is_active=1 的配置
-> is_active 改为 2
-> config_value_audio 调 VoxCPM
-> config_value 调 LatentSync
-> 字幕/封面/上传/CRM 回调
-> 释放 t_comfyui_config.is_active=1
```

这条链路已经跑通。

## 当前 h20 已验证状态

### 代码与部署

- GitLab `test` 已包含模型池路由改动：
  - `scheduler/collect_scheduler.py`
  - `router/service/video_server2/video_work.py`
  - `router/service/video_server2/voxcpm_tts.py`
- h20 当前部署目录：
  - `/data/project/test_ai_botserver.20260602145953`

### 当前 Docker 模型服务

| 服务 | 容器名 | 镜像 | 地址 | GPU | 状态 |
|---|---|---|---|---|---|
| VoxCPM | `voxcpm-api-h20-test` | `joying/voxcpm-api:h20-test` | `http://127.0.0.1:8120` | GPU1 | health ok |
| LatentSync | `latentsync-api-h20-test` | `joying/latentsync-api:h20-test` | `http://127.0.0.1:8121` | GPU2 | health ok |

### 当前测试库模型池记录

`zhugedata_test.t_comfyui_config.id=1`：

```text
config_key         = comfyui_url
config_value_audio = http://127.0.0.1:8120
config_value       = http://127.0.0.1:8121
is_active          = 1
```

含义：

- `config_value_audio`：VoxCPM 声音克隆服务地址。
- `config_value`：LatentSync 唇形同步服务地址。
- `is_active=1`：空闲。
- `is_active=2`：使用中。

### 单任务闭环验证

已完成任务：

```text
t_video_generate_task.id = 1243
job_id = 1040
task_id = 1031
task_status = 3
progress = 100
callback_status = 1
```

生成视频：

```text
https://videos-test.joyingai.cn/video/crm/20260602/user4_1780384644704_f0178eaa0ba4c2fb.mp4
```

日志证据：

```text
voxcpm_tts.py -> http://127.0.0.1:8120/v1/clone-voice
latentsync_service.py -> http://127.0.0.1:8121/v1/lip-sync
collect_scheduler.py -> 任务完成后释放 config_id=1, is_active: 2 -> 1
```

## 和生产逻辑对齐度拆分

| 模块 | 当前对齐度 | 说明 |
|---|---:|---|
| CRM 视频任务入口 | 90% | 已回到 `/crm/generate_video_task` 入库调度链路，不走实时接口 |
| 任务表与调度 | 90% | 继续使用 `t_video_generate_task` 和 scheduler 扫表 |
| 资源锁 | 90% | 继续使用 `t_comfyui_config.is_active`，已验证领取和释放 |
| 模型地址来源 | 85% | 已从 `t_comfyui_config` 传入 VoxCPM / LatentSync，仍保留全局 fallback |
| Docker 管理方式 | 70% | 已用 yml + 现有镜像启动，仍需运维固化目录、重启和日志 |
| 并发模型池 | 45% | 代码支持按可用配置数并发，但当前只启用 1 条模型池配置 |
| 运维监控与故障恢复 | 40% | 还需要健康监控、自动重启、异常告警、失败压测 |

整体估算：80%-85%。

## 当前为什么还不能说 100% 对齐

1. 当前只有一组可用 Docker 模型服务，不能证明多服务池并发。
2. 旧裸机服务 `8110/8101` 还在 h20 上运行，短期可作为回滚，但长期会让排查变复杂。
3. Docker yml 目前在项目部署目录中，仍需运维确认是否迁到固定运维目录。
4. 还没有做 Docker 容器异常、模型超时、任务失败后锁释放的压测。
5. 还没有验证 2 个或更多任务同时生成时，GPU 显存和任务锁是否稳定。

## 给运维的短版说明

可以直接这样跟晋良哥说：

```text
晋良哥，我们 h20 测试服现在已经把新模型接回生产式调度链路了：

CRM 还是调 /crm/generate_video_task，Bot 入库后由 ai_botserver_sch 扫 t_video_generate_task，再领取 t_comfyui_config 空闲配置。

现在 t_comfyui_config 里：
config_value_audio 用来放 VoxCPM 声音克隆服务地址；
config_value 用来放 LatentSync 唇形同步服务地址；
is_active 还是沿用原来的 1=空闲、2=使用中。

当前单组 Docker 已经跑通：
VoxCPM: http://127.0.0.1:8120
LatentSync: http://127.0.0.1:8121

现在想进一步按生产模型池方式测试并发，需要你帮忙确认/部署多组 Docker 服务，比如再起一组 8122/8123，或者更多组。每组对应 t_comfyui_config 一条记录，调度会自动按空闲配置领取任务并并发处理。

模型 API 不需要开公网，只需要 h20 本机 Bot 能访问 127.0.0.1 对应端口。
```

## 需要给运维的材料

### 1. 当前 compose/yml 文件

仓库文件：

```text
deploy/docker/docker-compose.h20.yml
```

h20 当前部署后路径：

```text
/data/project/test_ai_botserver/deploy/docker/docker-compose.h20.yml
```

当前启动命令：

```bash
cd /data/project/test_ai_botserver
/cm/local/apps/docker/current/bin/docker compose -f deploy/docker/docker-compose.h20.yml up -d
```

### 2. 当前镜像

```text
joying/voxcpm-api:h20-test
joying/latentsync-api:h20-test
```

### 3. 当前容器与端口

```text
voxcpm-api-h20-test     -> 127.0.0.1:8120
latentsync-api-h20-test -> 127.0.0.1:8121
```

### 4. API 健康检查

```bash
curl -s http://127.0.0.1:8120/health
curl -s http://127.0.0.1:8121/health
```

预期：

```json
{"status":"ok"}
```

### 5. 业务 API

VoxCPM：

```text
POST /v1/clone-voice
```

LatentSync：

```text
POST /v1/lip-sync
```

### 6. 日志查看

```bash
/cm/local/apps/docker/current/bin/docker logs --tail=100 voxcpm-api-h20-test
/cm/local/apps/docker/current/bin/docker logs --tail=100 latentsync-api-h20-test
```

### 7. GPU 绑定

当前：

```text
VoxCPM -> GPU1
LatentSync -> GPU2
```

如果要扩第二组，建议先用：

```text
VoxCPM-2 -> GPU3 -> 8122
LatentSync-2 -> GPU4 -> 8123
```

如果要扩第三组，再考虑：

```text
VoxCPM-3 -> GPU5 -> 8124
LatentSync-3 -> GPU6 -> 8125
```

先不要一次性开太多组，建议从 2 组并发开始。

## 多组模型池怎么配置

### 第一组，当前已存在

```sql
UPDATE zhugedata_test.t_comfyui_config
SET config_value_audio = 'http://127.0.0.1:8120',
    config_value = 'http://127.0.0.1:8121',
    is_active = 1
WHERE id = 1;
```

### 第二组，建议新增或启用一条记录

如果已有 `id=2` 可复用：

```sql
UPDATE zhugedata_test.t_comfyui_config
SET config_key = 'comfyui_url',
    config_value_audio = 'http://127.0.0.1:8122',
    config_value = 'http://127.0.0.1:8123',
    is_active = 1
WHERE id = 2;
```

如果需要新增：

```sql
INSERT INTO zhugedata_test.t_comfyui_config
  (config_key, config_value_audio, config_value, is_active)
VALUES
  ('comfyui_url', 'http://127.0.0.1:8122', 'http://127.0.0.1:8123', 1);
```

执行前需要先确认表结构和是否有必填字段，避免直接插入失败。

## 并发测试前提

执行并发测试前要确认：

```sql
SELECT id, config_key, config_value, config_value_audio, is_active
FROM zhugedata_test.t_comfyui_config
WHERE config_key = 'comfyui_url';
```

期望至少两条：

```text
id=1, 8120/8121, is_active=1
id=2, 8122/8123, is_active=1
```

并且当前没有处理中任务：

```sql
SELECT id, job_id, task_id, task_status, progress, updated_time
FROM zhugedata_test.t_video_generate_task
WHERE task_status IN (0, 1, 2)
ORDER BY id DESC;
```

## 并发测试步骤

### 第一步：让产品/CRM 暂停乱提任务

测试窗口里先只提交指定任务，避免一边测试模型池，一边被其它任务抢锁。

### 第二步：确认两组模型服务都健康

```bash
curl -s http://127.0.0.1:8120/health
curl -s http://127.0.0.1:8121/health
curl -s http://127.0.0.1:8122/health
curl -s http://127.0.0.1:8123/health
```

### 第三步：CRM 连续创建 2 个视频任务

要求：

- 两个任务都走 `/crm/generate_video_task`。
- 都进入 `t_video_generate_task.task_status=0`。
- 每个 task 可以带不同的 `voice_emotion` / `voice_speed` / `voice_volume`，方便确认参数没有串。

### 第四步：观察 scheduler 分配

日志里应看到：

```text
配置分配概览: 任务数=2 可用配置数=2 本轮实际分配任务数=2
预分配任务与配置: task_id=xxx config_id=1 comfyui_url=http://127.0.0.1:8121
预分配任务与配置: task_id=yyy config_id=2 comfyui_url=http://127.0.0.1:8123
并发处理启动 max_workers=2 分配任务数=2
```

数据库里应看到：

```text
t_comfyui_config.id=1 is_active=2
t_comfyui_config.id=2 is_active=2
```

两个任务完成后应释放回：

```text
t_comfyui_config.id=1 is_active=1
t_comfyui_config.id=2 is_active=1
```

### 第五步：观察 Docker 与 GPU

```bash
nvidia-smi
/cm/local/apps/docker/current/bin/docker logs --tail=100 voxcpm-api-h20-test
/cm/local/apps/docker/current/bin/docker logs --tail=100 latentsync-api-h20-test
```

第二组容器的日志命令按运维实际容器名替换。

### 第六步：验收标准

并发 2 个任务测试通过的标准：

- 两个任务都完成，`task_status=3`。
- 两个任务都回调成功，`callback_status=1`。
- 两个任务的最终视频 URL 不为空。
- 两条 `t_comfyui_config` 都释放回 `is_active=1`。
- 两个 LatentSync 容器没有 GPU OOM。
- 任一任务失败时，失败任务应变为 `task_status=4`，对应配置仍必须释放回 `is_active=1`。

## 当前最建议的下一步

1. 先让运维按现有 yml 思路复制第二组容器：
   - VoxCPM：`8122`
   - LatentSync：`8123`
   - GPU：建议 `3/4`
2. 启用或新增 `t_comfyui_config` 第二条记录。
3. 安排一个明确测试窗口，让产品/CRM 只提交 2 个任务。
4. 观察 scheduler 是否 `max_workers=2` 并发处理。
5. 如果 2 并发稳定，再决定是否扩到 3 并发。

## 注意事项

- 模型服务不需要公网入口，只需要 h20 本机 Bot 能访问。
- 不要直接让 CRM 调 VoxCPM / LatentSync；CRM 只调 Bot。
- 不要再启用 `/crm/submit_heygem_whisper_video_task` 做主流程。
- 测试阶段建议先保留旧裸机 `8110/8101` 作为回滚，但验收时要看日志确认实际走的是 Docker 8120/8121 或第二组端口。
- 不要推 master，上线前只进 `test`。
