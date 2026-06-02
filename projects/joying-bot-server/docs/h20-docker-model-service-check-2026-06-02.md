﻿﻿﻿﻿---
date: "2026-06-02"
tags: [h20, docker, model-service, model-pool, ops]
---

# h20 Docker 模型服务调用与多开复核

## 关联执行计划

- [[h20-docker-multiopen-execution-plan-2026-06-02|h20 Docker 多开执行计划]]

## 本轮结论

- h20 当前模型服务调用逻辑已经回到生产式调度主链路：CRM 调 Bot，Bot 入库 `t_video_generate_task`，`ai_botserver_sch` 扫描任务，按 `t_comfyui_config.is_active` 领取资源，处理完成后释放。
- 如果只看“资源池调度/锁/并发分配”这一层，h20 和生产模型池逻辑基本一致。
- 如果看“具体模型 API”，h20 不是生产旧模型的完全同款：h20 现在是 VoxCPM + LatentSync Docker，生产旧口型是改过启动脚本的 `duix.avatar` Docker；生产 TTS 仍是 DashScope 路径，除非后续把新模型代码迁到生产。
- h20 当前 Docker 化方式和生产旧口型 Docker 运维方式相似，都是 yml/compose 管理、GPU 绑定、端口健康检查、日志查看；但镜像来源、Dockerfile、启动命令、代码挂载方式不完全一样，不能直接把生产 duix yml 当作 h20 新模型结论。

## 本地代码依据

- `scheduler/collect_scheduler.py`：负责查询 `t_video_generate_task`、领取 `t_comfyui_config`、并发执行、释放锁。
- `router/service/video_server2/video_work.py`：已启用 VoxCPM 和 LatentSync 服务封装，并从调度层接收模型服务地址。
- `router/service/video_server2/voxcpm_tts.py`：`POST {voxcpm_api_base}/v1/clone-voice`。
- `router/service/video_server2/latentsync_service.py`：`POST {latentsync_api_base}/v1/lip-sync`。
- `deploy/docker/docker-compose.h20.yml`：当前 h20 单组 Docker 服务，VoxCPM `8120`，LatentSync `8121`，GPU1/GPU2。
- `deploy/docker/voxcpm/Dockerfile`、`deploy/docker/latentsync/Dockerfile`：h20 新模型镜像构建方式。

## 当前 h20 单组模型池

```text
VoxCPM     -> joying/voxcpm-api:h20-test     -> 127.0.0.1:8120 -> GPU1
LatentSync -> joying/latentsync-api:h20-test -> 127.0.0.1:8121 -> GPU2
```

`t_comfyui_config` 当前含义：

```text
config_key         = comfyui_url
config_value_audio = VoxCPM API base
config_value       = LatentSync API base
is_active          = 1 idle / 2 busy
```

## 多开 Docker 的操作骨架

1. 复制 compose 里的两条服务，改成第二组容器名、GPU、端口。
2. 因为当前镜像 CMD 和 HEALTHCHECK 写死第一组端口，第二组必须在 compose 里覆盖 `command` 和 `healthcheck`。
3. 建议第二组先用：
   - VoxCPM-2：`8122`，GPU3
   - LatentSync-2：`8123`，GPU4
4. 启动后检查：

```bash
/cm/local/apps/docker/current/bin/docker compose -f deploy/docker/docker-compose.h20.yml up -d
curl -s http://127.0.0.1:8122/health
curl -s http://127.0.0.1:8123/health
```

5. 在 `zhugedata_test.t_comfyui_config` 增加或启用第二条资源池记录：

```sql
INSERT INTO zhugedata_test.t_comfyui_config
  (config_key, config_value_audio, config_value, is_active, description)
VALUES
  ('comfyui_url', 'http://127.0.0.1:8122', 'http://127.0.0.1:8123', 1, 'h20 docker pair 2');
```

执行 SQL 前必须先确认真实表结构和索引；本地 SQLAlchemy model 写了 `config_key unique=True`，但多模型池需要多条 `config_key='comfyui_url'` 记录。如果真实库有唯一索引，需要先和运维/DBA 确认迁移方案。

6. 并发验收看三处：
   - scheduler 日志出现 `max_workers=2` 和两个不同 `config_id`。
   - 两条 `t_comfyui_config` 在处理中变为 `is_active=2`，结束后回到 `1`。
   - 两个任务都完成并回调成功，且 Docker/GPU 无 OOM。

## 远程复核状态

## 2026-06-02 17:50 远程只读复核

已按 `docs/h20登录与排查Skill.md` 通过跳板进入 h20，只做只读检查，未改配置、未重启、未 kill 进程。

h20 当前状态：

- 主机：`hgx19`。
- Docker CLI：`/cm/local/apps/docker/current/bin/docker`。
- 当前 Docker 模型容器：
  - `voxcpm-api-h20-test`，镜像 `joying/voxcpm-api:h20-test`，`Up ... healthy`。
  - `latentsync-api-h20-test`，镜像 `joying/latentsync-api:h20-test`，`Up ... healthy`。
- 健康检查：
  - `http://127.0.0.1:8120/health` -> ok。
  - `http://127.0.0.1:8121/health` -> ok。
  - `http://127.0.0.1:8122/health` -> connection refused。
  - `http://127.0.0.1:8123/health` -> connection refused。
- 说明：h20 当前还只有一组 Docker 模型服务，第二组 `8122/8123` 尚未启动。
- 旧裸机模型服务仍在：
  - `8110`：旧 VoxCPM API。
  - `8101`：旧 LatentSync API。
- Bot/辅助服务仍在：
  - `8017`：supervisor/测试 Bot。
  - `8100`：外部联调入口对应 Bot。
  - `8188`：独立 Whisper 服务监听中；`/health` 返回 404，说明服务在，但该服务未暴露 `/health` 路由。
- GPU 概览：GPU1 约 11GB，GPU2 几乎空闲；GPU3/4/5/6/7 基本空闲，可优先用于第二组 Docker。

生产旧口型 Docker 只读复核：

- yml 目录：`/data/Comfyui_Duix/Duix-Avatar/deploy/docker-employ`。
- 当前有多份 `docker-compose-text*.yml`，每份对应一个 duix 容器。
- 运行中的旧口型容器使用镜像 `guiji2025/duix.avatar:2.9`。
- 运行中示例：
  - `duix-avatar-gen-video14` -> `6014:8383`
  - `duix-avatar-gen-video15` -> `6015:8383`
  - `duix-avatar-gen-video16` -> `6016:8383`
  - `duix-avatar-gen-video17` -> `6017:8383`
  - `duix-avatar-gen-video-test2/test3/test4/test5/test6/test7` -> `6002/6003/6006/6007/6008/6004:8383`
- 生产 yml 共同特征：`restart: always`、显式 `container_name`、GPU `device_ids`、`NVIDIA_VISIBLE_DEVICES`、`ports` 映射、`command: python /code/app_local.py`。

因此，h20 要“像生产一样多开”，应借鉴生产的一容器一端口一配置文件/服务的运维方式；但不能直接复用生产 duix 镜像、命令和端口，因为 h20 新模型是 VoxCPM/LatentSync 两类容器，且当前使用 host network + 8120/8121 内部端口。

执行计划见：[[h20-docker-multiopen-execution-plan-2026-06-02|h20 Docker 多开执行计划]]

可执行计划见：

- [[h20-docker-multiopen-execution-plan-2026-06-02|h20 Docker 多开执行计划]]





