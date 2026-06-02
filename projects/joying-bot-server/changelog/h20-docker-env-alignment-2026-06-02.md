---
date: "2026-06-02"
tags: [changelog, h20, docker, latentsync, voxcpm, performance]
---

# h20 Docker 环境对齐裸机进展 2026-06-02

## 背景

h20 测试服 Docker 链路已能端到端跑通，但 1 分钟左右视频完整生成耗时约 35-40 分钟，比之前裸机模型服务约 18-20 分钟慢。主要疑点是 Docker 内部运行环境和裸机环境不一致。

已记录的环境差异：

```text
裸机 LatentSync: Python 3.10.20 + Torch 2.5.1+cu121 + conda latentsync
Docker LatentSync: Python 3.11.14 + Torch 2.9.1+cu128 + /opt/latentsync-venv
```

## 本次本地仓库改动

目标：让 Docker 构建尽量对齐裸机环境。

已改方向：

- `deploy/docker/docker-compose.h20.yml`
  - VoxCPM / LatentSync 构建基础镜像改为 `nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04`。
  - `INSTALL_TORCH` 改为 `true`。
  - `PYTHON_BIN` 改为 `python`。
  - LatentSync 容器显式设置 `LATENTSYNC_INFERENCE_TIMEOUT_SECONDS=7200`。

- `deploy/docker/latentsync/Dockerfile`
  - 安装 `python3-venv`。
  - 构建阶段强制校验：Python 3.10、Torch 2.5.1、CUDA 12.1。
  - 过滤 LatentSync requirements 中可能覆盖 Torch/JAX/SciPy/peft 的依赖，再安装测试服已验证可用的版本。
  - healthcheck 和启动命令固定使用 `/opt/latentsync-venv/bin/python`。

- `deploy/docker/voxcpm/Dockerfile`
  - 构建阶段强制校验：Python 3.10、Torch 2.5.1、CUDA 12.1。
  - 继续固定 `setuptools==80.9.0`、`datasets==3.3.2`、`voxcpm==2.0.3`。

- `deploy/docker/README.md`
  - 更新为新 Docker 环境目标说明。
  - 记录如果 h20 无法拉取 CUDA 基础镜像，需要通过 `docker save/load` 预加载。

## LatentSync 参数回默认值

按用户要求，取消产品试测参数：

```text
inference_steps: 30 -> 20
guidance_scale: 1.8 -> 1.5
```

涉及文件：

- `router/service/video_server/latentsync_api.py`
- `test/test_video_quality_pipeline.py`
- `test/test_latentsync_timeout.py`
- `deploy/docker/README.md`

说明：`7200` 秒超时修复继续保留，因为这是长视频防误判失败的稳定性修复，不属于产品嘴型强度试测参数。

## 本地验证

已执行：

```text
python -m py_compile router/service/video_server/latentsync_api.py router/service/video_server/latentsync_service.py router/service/video_server2/latentsync_service.py
python -m unittest test.test_latentsync_timeout test.test_video_quality_pipeline
git diff --check
```

结果：

```text
py_compile: 通过
unit tests: Ran 9 tests, OK
git diff --check: 通过，仅 CRLF warning
```

## 当前未完成

- 还没有在 h20 重新 build 新 Docker 镜像。
- 还没有停/换当前正在跑的 Docker 容器。
- 还没有用同一份视频做 Docker 新环境和裸机环境的严格 A/B 性能对比。

## 下一步

1. 提交当前本地改动到 GitLab `test`。
2. 等 Jenkins 或手动同步到 h20 后，在 h20 构建新镜像。
3. 如果 h20 拉取 `nvidia/cuda:12.1.1-cudnn8-runtime-ubuntu22.04` 失败，先在可联网机器拉取并 `docker save/load` 到 h20。
4. 新镜像启动后先验证：

```text
127.0.0.1:8120/health
127.0.0.1:8121/health
```

5. 再用同一份短视频/短音频直接测 LatentSync Docker，确认运行环境输出为 Python 3.10 + Torch 2.5.1/cu121。
6. 最后提交 1 个 CRM 视频任务做端到端验证，和裸机耗时对比。

## 2026-06-02 本地验证补充

继续完成本地校验：

```text
docker compose -f deploy/docker/docker-compose.h20.yml config
python -m unittest test.test_scheduled_video_voice_params test.test_voice_clone_upload test.test_latentsync_timeout test.test_video_quality_pipeline
python -m py_compile router/service/video_server/latentsync_api.py router/service/video_server/latentsync_service.py router/service/video_server2/latentsync_service.py router/service/video_server/voxcpm_api.py
git diff --check
```

结果：

```text
docker compose config: 通过，本机仅有 Docker config 权限 warning
unit tests: Ran 23 tests, OK
py_compile: 通过
git diff --check: 通过，仅 CRLF warning
```

当前代码仍停留在本地工作区，尚未提交 GitLab，也尚未在 h20 构建/替换 Docker 镜像。

## 2026-06-02 14:30 方向修正：优先复用现有镜像并用 yml 启动

用户确认：Docker 镜像里本来已有模型文件，当前不应继续走复杂的重新 build / clone GitHub 路线，应优先复用 h20 已验证可运行的镜像，通过 yml 启动和管理。

本地仓库已调整：

- `deploy/docker/docker-compose.h20.yml`
  - 移除默认 `build` 配置。
  - 保留现有镜像：
    - `joying/voxcpm-api:h20-test`
    - `joying/latentsync-api:h20-test`
  - 通过 volume 挂载当前 Jenkins 部署目录中的 API 包装文件：
    - `/data/project/test_ai_botserver/router/service/video_server/voxcpm_api.py -> /app/voxcpm_api.py`
    - `/data/project/test_ai_botserver/router/service/video_server/latentsync_api.py -> /app/latentsync_api.py`

这样后续 `inference_steps/guidance_scale` 默认值、超时等 API 层改动，可以通过 Jenkins 部署 + yml recreate 生效，不必重打模型镜像。

已提交并推送到 GitLab `test`：

```text
f403f055 fix: run h20 model containers from compose images
# rebase 后远端提交为 7c4796f7
```

h20 已部署到：

```text
/data/project/test_ai_botserver.20260602143158
```

h20 当前队列状态只读检查：

```text
task_status=2: 1 条处理中，task_id=1027
task_status=0: 3 条待处理
t_comfyui_config.id=1 is_active=2
```

因此暂未执行 `docker compose up -d` 刷新容器，避免打断正在生成的视频任务。

当前需要等待任务完成，或由用户明确确认可以取消任务后，再用 yml 刷新模型容器。

## 与生产调用逻辑的关系

- yml 启动镜像：解决“模型服务怎么运行/管理”的问题，已接近旧生产 Docker 管理方式。
- 最终生产式调度：还需要继续改 Bot 调度逻辑，让 scheduler 领取 `t_comfyui_config` 后使用：
  - `config_value_audio` 调 VoxCPM
  - `config_value` 调 LatentSync

当前还没完成这一步，所以“用 yml 起镜像”只是模型服务部署方式对齐，不等于调度调用逻辑已经完全对齐生产。

## 2026-06-02 14:30 思路修正：优先复用已有模型镜像

用户确认：Docker 里本来就有模型文件，当前阶段不应该每次重新 clone / rebuild 大镜像，优先使用 yml 启动已有镜像。

已调整本地仓库并推送 GitLab `test`：

```text
commit: 7c4796f7 fix: run h20 model containers from compose images
```

当前 h20 compose 方式：

- 继续使用已有镜像：
  - `joying/voxcpm-api:h20-test`
  - `joying/latentsync-api:h20-test`
- 不默认 build。
- 通过 bind mount 挂载当前 Jenkins 部署目录里的 API 文件：
  - `/data/project/test_ai_botserver/router/service/video_server/voxcpm_api.py -> /app/voxcpm_api.py`
  - `/data/project/test_ai_botserver/router/service/video_server/latentsync_api.py -> /app/latentsync_api.py`

这样模型文件、LatentSync 源码和已验证环境继续留在镜像内，Bot/API 小代码可以跟随 Jenkins 部署，通过 yml 刷新容器生效。

h20 已部署到：

```text
/data/project/test_ai_botserver.20260602143158
```

当前未刷新容器，原因是测试库仍有任务：

```text
task_status=2: 1 条处理中
task_status=0: 3 条待处理
t_comfyui_config.id=1 is_active=2
```

为避免打断产品/前端正在生成的视频，暂不执行 `docker compose up -d`。

下一步等队列空闲后执行：

```bash
cd /data/project/test_ai_botserver
/cm/local/apps/docker/current/bin/docker compose -f deploy/docker/docker-compose.h20.yml up -d
curl -s http://127.0.0.1:8120/health
curl -s http://127.0.0.1:8121/health
```

注意：这一步只刷新模型服务容器，不是重新打镜像。

## 2026-06-02 14:38 测试任务清理与 yml 刷新完成

按用户确认，已直接断掉当前测试库任务并继续 yml 刷新模型容器。

执行内容：

1. 停止 `ai_botserver_sch` 调度，避免清理任务时发生竞态。
2. 将测试库 `t_video_generate_task.task_status in (0,1,2)` 的任务全部标记失败：
   - `id=1239 / job_id=1036 / task_id=1027 / 原 task_status=2`
   - `id=1240 / job_id=1037 / task_id=1028 / 原 task_status=0`
   - `id=1241 / job_id=1038 / task_id=1029 / 原 task_status=0`
   - `id=1242 / job_id=1039 / task_id=1030 / 原 task_status=0`
3. 释放 `t_comfyui_config.id=1`：`is_active=1`。
4. 执行：

```bash
cd /data/project/test_ai_botserver
/cm/local/apps/docker/current/bin/docker compose -f deploy/docker/docker-compose.h20.yml up -d
```

5. 重新启动 `ai_botserver_sch`。

验证结果：

```text
latentsync-api-h20-test: Up, healthy
voxcpm-api-h20-test: Up, healthy
127.0.0.1:8120/health -> {"status":"ok"}
127.0.0.1:8121/health -> {"status":"ok"}
127.0.0.1:8100/status/check -> {"status":"ok"}
测试库 active_counts -> 空
t_comfyui_config.id=1 -> is_active=1
```

LatentSync 容器内 `/app/latentsync_api.py` 已来自当前部署挂载文件，确认默认值：

```text
LATENTSYNC_INFERENCE_TIMEOUT_SECONDS=7200
inference_steps default=20
guidance_scale default=1.5
```

说明：当前仍复用已有 `joying/latentsync-api:h20-test` 镜像，所以容器 Python/Torch 环境仍是旧镜像环境，不是重新 build 的 Python 3.10/Torch 2.5。此次目标已按用户确认调整为“复用现有镜像 + yml 启动管理”。
