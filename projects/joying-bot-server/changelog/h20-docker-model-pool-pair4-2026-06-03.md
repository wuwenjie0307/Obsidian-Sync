---
date: "2026-06-03"
tags: [changelog, h20, docker, model-pool, voxcpm, latentsync, test-env]
---

# h20 测试服新增第 4 组 Docker 模型池 2026-06-03

## 改动类型

- [ ] 新功能
- [ ] Bug 修复
- [ ] 重构
- [x] 配置变更

## 改动内容

2026-06-03 15:08 左右，在 h20 测试服新增第 4 组 Docker 模型服务池，用于把视频生成并发从 3 路扩到 4 路。

新增服务组：

| 服务组 | VoxCPM 声音克隆 | LatentSync 唇形同步 | DB config_id | GPU 绑定 |
|---|---|---|---:|---|
| 第 4 组 | `http://127.0.0.1:8126` | `http://127.0.0.1:8127` | `id=11` | VoxCPM=GPU0, LatentSync=GPU7 |

当前 h20 测试服 active Docker 模型池：

| DB id | VoxCPM | LatentSync | 状态 |
|---:|---|---|---|
| `1` | `http://127.0.0.1:8120` | `http://127.0.0.1:8121` | `is_active=1` |
| `2` | `http://127.0.0.1:8122` | `http://127.0.0.1:8123` | `is_active=1` |
| `10` | `http://127.0.0.1:8124` | `http://127.0.0.1:8125` | `is_active=1` |
| `11` | `http://127.0.0.1:8126` | `http://127.0.0.1:8127` | `is_active=1` |

## 执行步骤

### 1. 预检

确认当前 h20 部署目录：

```text
/data/project/test_ai_botserver -> /data/project/test_ai_botserver.20260603145500
```

预检结果：

- 现有 3 组 Docker 模型服务健康：`8120/8121`、`8122/8123`、`8124/8125`。
- 新端口 `8126/8127` 未监听，可用。
- 测试库当前没有 `task_status in (0,1,2)` 的待处理/处理中任务。
- GPU 使用状态：GPU7 基本空闲；GPU0 被旧裸机/回滚相关进程占用约 46GB，但 H20 单卡总显存约 98GB，仍有余量。
- 绑定策略：把主要耗时的 LatentSync 放到完全空闲的 GPU7；把新增 VoxCPM 放 GPU0。

### 2. 备份 compose

备份 h20 当前 compose 文件：

```text
/data/project/test_ai_botserver/deploy/docker/docker-compose.h20.yml
```

备份文件：

```text
/data/project/test_ai_botserver/deploy/docker/docker-compose.h20.yml.bak.20260603150801
```

### 3. 补齐 compose 到 4 组

将当前 h20 compose 文件补齐为 4 组服务，新增：

```yaml
voxcpm-api-4:
  container_name: voxcpm-api-h20-test-4
  image: joying/voxcpm-api:h20-test
  network_mode: host
  command: ["python", "/app/voxcpm_api.py", "--host", "0.0.0.0", "--port", "8126"]
  NVIDIA_VISIBLE_DEVICES: "0"

latentsync-api-4:
  container_name: latentsync-api-h20-test-4
  image: joying/latentsync-api:h20-test
  network_mode: host
  command: ["/opt/latentsync-venv/bin/python", "/app/latentsync_api.py", "--host", "0.0.0.0", "--port", "8127"]
  NVIDIA_VISIBLE_DEVICES: "7"
```

共享挂载保持和现有组一致：

```text
/data/project/test_ai_botserver/router/service/video_server/voxcpm_api.py -> /app/voxcpm_api.py
/data/project/test_ai_botserver/router/service/video_server/latentsync_api.py -> /app/latentsync_api.py
/data/model_cache/huggingface -> /root/.cache/huggingface
/data/models/LatentSync-1.6 -> /opt/LatentSync/checkpoints
/data/video_tmp -> /data/video_tmp
```

校验 compose：

```bash
cd /data/project/test_ai_botserver
/cm/local/apps/docker/current/bin/docker compose -f deploy/docker/docker-compose.h20.yml config >/tmp/docker-compose.h20.4groups.rendered.yml
```

结果：通过。

### 4. 启动第 4 组

只启动新增服务，不重建已有 3 组：

```bash
cd /data/project/test_ai_botserver
/cm/local/apps/docker/current/bin/docker compose -f deploy/docker/docker-compose.h20.yml up -d voxcpm-api-4 latentsync-api-4
```

启动结果：

```text
voxcpm-api-h20-test-4      Up, healthy
latentsync-api-h20-test-4  Up, healthy
```

健康检查：

```text
8126 -> {"status":"ok"}
8127 -> {"status":"ok"}
```

全量端口健康检查：

```text
8120 -> {"status":"ok"}
8121 -> {"status":"ok"}
8122 -> {"status":"ok"}
8123 -> {"status":"ok"}
8124 -> {"status":"ok"}
8125 -> {"status":"ok"}
8126 -> {"status":"ok"}
8127 -> {"status":"ok"}
```

### 5. 启用 DB 模型池

测试库新增记录：

```sql
INSERT INTO zhugedata_test.t_comfyui_config
  (config_key, config_value_audio, config_value, is_active, description)
VALUES
  ('comfyui_url', 'http://127.0.0.1:8126', 'http://127.0.0.1:8127', 1, 'h20 docker pair 4');
```

实际写入结果：

```text
id=11
config_key=comfyui_url
config_value_audio=http://127.0.0.1:8126
config_value=http://127.0.0.1:8127
is_active=1
description=h20
```

## 影响范围

- h20 测试服模型池从 3 组扩到 4 组。
- scheduler 现在最多可按 4 条 active `t_comfyui_config` 并发领取 4 个视频任务。
- 不改生产库、不改正式服、不改 CRM 接口。
- 第 4 组 VoxCPM 使用 GPU0，GPU0 当前也有旧裸机/回滚相关进程占显存；如果旧服务被实际调用，可能和第 4 组声音克隆抢 GPU。当前 scheduler active 配置走 Docker 池，不走旧裸机地址。

## 验证结果

- Docker 容器：`voxcpm-api-h20-test-4` 和 `latentsync-api-h20-test-4` 均为 healthy。
- 端口：`8126/8127` 均返回 `{"status":"ok"}`。
- DB：`t_comfyui_config.id=11` 已写入且 `is_active=1`。
- 队列：写入前后测试库无待处理/处理中任务。

## 回滚方式

先禁用 DB 资源池：

```sql
UPDATE zhugedata_test.t_comfyui_config
SET is_active = 0,
    description = CONCAT(COALESCE(description, ''), ' disabled after pair4 rollback')
WHERE id = 11;
```

停止第 4 组容器：

```bash
cd /data/project/test_ai_botserver
/cm/local/apps/docker/current/bin/docker compose -f deploy/docker/docker-compose.h20.yml stop voxcpm-api-4 latentsync-api-4
```

如需恢复 compose：

```bash
cd /data/project/test_ai_botserver
cp deploy/docker/docker-compose.h20.yml.bak.20260603150801 deploy/docker/docker-compose.h20.yml
/cm/local/apps/docker/current/bin/docker compose -f deploy/docker/docker-compose.h20.yml config >/tmp/docker-compose.h20.rollback.rendered.yml
```

## 注意事项

当前 h20 现场 compose 已补齐到 4 组，但本地 Git 工作区/远端 `test` 分支里的 `deploy/docker/docker-compose.h20.yml` 可能仍不是现场最终版本。后续需要把现场 compose 固化回 Git 或生产运维目录，否则下一次 Jenkins/自动部署可能覆盖该文件，导致 compose 文件和实际运行容器不一致。

## 相关 Commit

- 本次是 h20 测试服现场配置变更，没有新增代码 commit。


### 2026-06-03 15:20 配置字段统一补充

已将 `t_comfyui_config.id=11` 的展示字段统一为前三组口径：

```text
description=h20
type=1
```

说明：scheduler 当前不使用 `type` 参与调度，只按 `config_key='comfyui_url'` 和 `is_active=1` 领取资源；本次补 `type=1` 是为了保持测试库配置展示一致。
