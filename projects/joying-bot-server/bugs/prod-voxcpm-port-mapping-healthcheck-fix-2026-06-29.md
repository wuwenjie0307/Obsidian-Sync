---
date: "2026-06-29"
project: "joying-bot-server"
type: bug
status: fixed
severity: high
tags: [bug, prod, voxcpm, voice-clone, docker]
aliases: ["正式服音色克隆容器启动后访问不到应用"]
---

# 正式服音色克隆容器启动后访问不到应用

## 问题描述

正式服 LLM-76 上 VoxCPM 音色克隆容器已启动，日志显示 Uvicorn 应用启动完成，但从宿主机端口访问不到应用，`docker ps` 显示容器长期 `unhealthy`。

## 复现步骤

1. 登录 LLM-76，进入 `/data/project/docker-compose-yml/voxcpm`。
2. 查看 `docker ps`，可见 `voxcpm-api-h20-1` 到 `voxcpm-api-h20-12` 都在运行，但端口映射为 `811x->8015/tcp`，状态为 `unhealthy`。
3. 查看容器日志，应用实际启动在 `http://0.0.0.0:8105`。
4. 宿主机访问 `http://127.0.0.1:8110/health` 等端口失败。

## 期望行为

宿主机 `8110-8121` 应分别转发到容器内实际监听的 VoxCPM 应用端口，并且 `/health` 返回 `{"status":"ok"}`。

## 实际行为

- 容器内 `8015` 未监听，宿主机端口却转发到 `8015`。
- 容器内 `8105` 正常监听，`/health` 返回 200。
- 镜像自带 healthcheck 访问 `127.0.0.1:8120/health`，该端口也未监听，导致容器 unhealthy。

## 原因

Docker Compose 配置与应用启动端口不一致：

- `ports` 配置为 `811x:8015`
- `command` 配置为 `--port 8105`
- 镜像 healthcheck 访问 `8120/health`

应用本身正常，故障发生在 Docker 端口映射和健康检查配置层。

## 解决方案

在 LLM-76 的 `/data/project/docker-compose-yml/voxcpm` 中：

1. 备份原始 compose 文件到：
   `/data/project/docker-compose-yml/voxcpm/backup-before-port-fix-20260629235034`
2. 将 `voxcpm-api-docker-compose1.yml` 到 `voxcpm-api-docker-compose15.yml` 中的端口映射从 `宿主机端口:8015` 改为 `宿主机端口:8105`。
3. 在 compose 中覆盖 healthcheck，改为检查：
   `http://127.0.0.1:8105/health`
4. 修正 `voxcpm-api-docker-compose14.yml` 的重复 `container_name`，从 `voxcpm-api-h20-13` 改为 `voxcpm-api-h20-14`。
5. 对当前运行的 1-12 号容器执行 `docker compose -f voxcpm-api-docker-composeN.yml up -d --force-recreate`。

## 优化点

- 后续生成 compose 文件时应统一应用启动端口、映射端口和 healthcheck 端口。
- 镜像 tag 为 `h20-test`，正式环境继续使用时建议确认 tag 命名是否会造成误解。
- 当前正式库 `t_comfyui_config.config_value_audio` active 地址为 `http://192.192.168.47:8120` 和 `http://192.192.168.47:8121`，容器池如果只开放两条 active 资源，业务并发上限会受这两条配置限制。

## 验证结果

2026-06-29 23:53 CST 验证：

- `docker ps` 中 `voxcpm-api-h20-1` 到 `voxcpm-api-h20-12` 均为 `healthy`。
- 端口映射变为 `8110-8121 -> 8105/tcp`。
- LLM-76 宿主机逐个访问 `http://127.0.0.1:8110/health` 到 `http://127.0.0.1:8121/health`，全部返回 200。
- LLM-76 访问正式库 active 地址：
  - `http://192.192.168.47:8120/health` 返回 200
  - `http://192.192.168.47:8121/health` 返回 200
- LLM-74 访问同样两个正式库 active 地址，也均返回 200。

## 相关文件

- `/data/project/docker-compose-yml/voxcpm/voxcpm-api-docker-compose1.yml`
- `/data/project/docker-compose-yml/voxcpm/voxcpm-api-docker-compose12.yml`
- `/data/project/prod_ai_botserver/router/service/video_server/voxcpm_api.py`
- `router/service/voice_audition_pool_service.py`

## 相关记录

- [[projects/joying-bot-server/docs/prod-test-hyperframes-runtime-config-check-2026-06-29|正式服 / 测试服 HyperFrames 配置对比]]
