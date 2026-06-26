---
date: "2026-06-26"
project: "joying-bot-server"
type: doc
tags: [doc, h20, hyperframes, docker, vibevideo, deployment]
aliases: ["H20 HyperFrames Docker runner 上线方案"]
---

# H20 HyperFrames Docker runner 上线方案

## 图谱链接

- 项目: [[projects/joying-bot-server/00-项目概览|joying-bot-server]]
- 索引: [[projects/joying-bot-server/docs/00-docs-index|参考文档索引]]

## 背景

网感视频 HyperFrames 渲染目前由 Python scheduler 在宿主机直接调用 Node 后处理脚本。测试中发现渲染阶段存在环境漂移、并发排队和锁等待超时误判失败的风险。正式上线前先做最小 Docker runner，隔离 HyperFrames 渲染环境，同时不改现有任务表、CRM 接口和后端调度主链路。

## 结论

初期只做 Docker runner，不做完整 worker 池：

- Python scheduler 继续跑在宿主机。
- 每个 HyperFrames 渲染任务临时执行一次 `docker run`。
- 容器只负责执行 `hyperframes-postprocess/index.js --input manifest.json --output result.json`。
- 产物仍写到现有 `/data/.../tmp/h20_hyperframes/<task_id>/`。
- 不新增数据库字段，不改 `t_video_generate_task` 结构，继续使用现有 `hf_*` 字段。
- 现有进程内渲染锁继续保留，通过 `HF_MAX_CONCURRENCY` 控制同时运行的 Docker 渲染容器数量。

## 本次代码改动

开发工作区：`C:\Users\admin\AppData\Local\Temp\joyingbot-new-vibevideo-master-rebuild-clean`
功能分支：`feature/ai_v6.3.3_vibevideo_master_rebuild_clean`

主要文件：

- `router/service/video_server2/hyperframes_cli.py`
  - 新增 `HF_RENDER_BACKEND=local|docker`，默认 `local`。
  - 新增 `HF_DOCKER_IMAGE`、`HF_DOCKER_BINARY`、`HF_DOCKER_MOUNTS`、`HF_DOCKER_SHM_SIZE` 等 Docker runner 配置。
  - Docker backend 生成 `docker run --rm --network host --ipc=host -v /data:/data -v /tmp:/tmp ...`。
  - Docker backend 默认容器内 Python 为 `/usr/bin/python3`，HyperFrames node_modules 为 `/opt/hyperframes/deps/hyperframes-0.6.42/node_modules`。
  - Docker 失败时错误名为 `HYPERFRAMES_DOCKER_FAILED`，包含 returncode、stdout、stderr 摘要。
  - 锁等待默认值从 600 秒改为 60 秒：`HF_RENDER_LOCK_TIMEOUT_SECONDS=60`。
- `scheduler/collect_scheduler.py`
  - `HF_RENDER_LOCK_TIMEOUT` 不再按最终失败处理。
  - 返回 `retry_later=True`，任务回到待处理，下一轮继续排队，不回调 CRM 失败。
- `deploy/docker/hyperframes-renderer/Dockerfile`
  - 新增 HyperFrames renderer 镜像定义。
  - 固定 Ubuntu 22.04、Node 22.22.2、HyperFrames 0.6.42、ffmpeg、Python/Pillow/requests/rembg、Chromium 依赖和中文字体。
- `deploy/docker/hyperframes-renderer/README.md`
  - 记录 build、scheduler env、rollback、历史 manifest smoke test。
- `test/test_hyperframes_cli.py`
  - 覆盖 Docker backend 命令构造和 Docker 非零退出错误摘要。
- `test/test_video_model_busy_retry.py`
  - 覆盖 HyperFrames 锁等待超时进入 `retry_later`，避免终态失败。

注意：当时工作区还有上一段任务遗留的 `router/crm_server.py` 和 `test/test_scheduled_video_voice_params.py` 未提交改动，不属于本次 Docker runner 改动。

## Docker runner 运行方式

上线环境变量建议：

```bash
export HF_RENDER_BACKEND=docker
export HF_DOCKER_IMAGE=h20-hyperframes-renderer:0.6.42-node22.22.2
export HF_MAX_CONCURRENCY=1
export HF_RENDER_LOCK_TIMEOUT_SECONDS=60
export HF_DOCKER_MOUNTS=/data:/data,/tmp:/tmp
export HF_DOCKER_SHM_SIZE=2g
```

渲染时宿主机执行的核心形式：

```bash
docker run --rm --network host --ipc=host \
  -v /data:/data \
  -v /tmp:/tmp \
  -w <当前项目目录> \
  -e HF_POSTPROCESS_PYTHON=/usr/bin/python3 \
  -e HYPERFRAMES_SHARED_NODE_MODULES=/opt/hyperframes/deps/hyperframes-0.6.42/node_modules \
  h20-hyperframes-renderer:0.6.42-node22.22.2 \
  node hyperframes-postprocess/index.js --input manifest.json --output result.json
```

## 镜像获取方式

初期可选三种：

1. 目标服务器本机 build：

```bash
cd /data/project/test_ai_botserver
docker build \
  -t h20-hyperframes-renderer:0.6.42-node22.22.2 \
  -f deploy/docker/hyperframes-renderer/Dockerfile .
```

2. 公司内网 registry：CI 或构建机 build 后 push，正式服 `docker pull`，再把 `HF_DOCKER_IMAGE` 指到 registry 镜像。

3. tar 包分发：构建机 `docker save`，目标机 `docker load`。

当前最稳妥的上线方式是先在目标机本机 build 或 tar 包导入，后续稳定后再接内网 registry。

## 回退方式

```bash
export HF_RENDER_BACKEND=local
export HF_MAX_CONCURRENCY=1
```

然后重启 scheduler。不需要回滚数据库，也不需要改 CRM 参数。

## 验证记录

已在本地工作区完成：

```text
python -m unittest test.test_hyperframes_cli test.test_video_model_busy_retry.VideoModelBusyRetryTest
Ran 47 tests OK

python -m py_compile router/service/video_server2/hyperframes_cli.py scheduler/collect_scheduler.py
OK

git diff --check ...
OK
```

未完成：

- 已在 H20 上 build Docker 镜像，见「H20 实际构建记录」。
- 已用历史 manifest 做容器 smoke test，见「H20 实际构建记录」。
- 尚未在测试服连续提交 2-3 个长视频验证并发和排队行为。

## 上线步骤建议

1. 确认目标机器 Docker Engine 可用。
2. build 或导入 `h20-hyperframes-renderer:0.6.42-node22.22.2` 镜像。
3. 先设置 `HF_RENDER_BACKEND=docker`、`HF_MAX_CONCURRENCY=1`。
4. 用历史 manifest 单独跑一次 Docker smoke test，确认生成 `final.mp4`、`cover.png`、`result.json`。
5. 重启 scheduler。
6. 提交 1 个网感视频任务验证 CRM 回调成功。
7. 稳定后再把 `HF_MAX_CONCURRENCY` 升到 2。
8. 观察 CPU、内存、磁盘、容器退出码、`callback_status`、`HF_RENDER_LOCK_TIMEOUT` 次数。

## 后期 worker 池方向

如果后续需要多个 scheduler 进程或跨机器并发，当前单进程 `BoundedSemaphore` 不够，需要做真正 worker 池：

- 新增 `t_hyperframes_render_worker`，不复用 `t_comfyui_config`。
- 字段建议：`id`、`worker_key`、`container_name/base_url`、`is_active`、`current_task_id`、`locked_at`、`heartbeat_at`、`last_error`、`created_time`、`updated_time`。
- scheduler 使用 DB 行锁领取空闲 worker。
- worker 心跳超时自动释放或置不可用。
- 每个 worker/slot 同一时间只跑一个 HyperFrames 渲染。

这个属于第二阶段，初期上线不做。
## H20 实际构建记录（2026-06-26）

本次已在 H20 测试服完成镜像构建和历史 manifest smoke test。

环境确认：

- H20 hostname: `hgx19`
- Docker binary: `/cm/local/apps/docker/current/bin/docker`
- Docker version: `26.1.5 / 26.1.5`
- 当前测试服 symlink: `/data/project/test_ai_botserver -> /data/project/test_ai_botserver.20260626210153`
- scheduler 进程 cwd: `/data/project/test_ai_botserver.20260626210153`
- 8100 仍有一个旧 cwd deleted 进程，构建镜像本身没有动这个进程。

构建方式：

```bash
cd /tmp/h20-hyperframes-renderer-build
/cm/local/apps/docker/current/bin/docker build --network=host \
  -t h20-hyperframes-renderer:0.6.42-node22.22.2 \
  -f Dockerfile .
```

构建结果：

```text
image: h20-hyperframes-renderer:0.6.42-node22.22.2
image id: 2e4363328bb0
size: 2.14GB
build exit: 0
```

踩坑：

1. `docker` 不在默认 PATH。
   - H20 可用路径是 `/cm/local/apps/docker/current/bin/docker`。
   - scheduler 后续切 Docker backend 时需要设置：`HF_DOCKER_BINARY=/cm/local/apps/docker/current/bin/docker`。

2. 第一次 build 被本地交互脚本提前断开。
   - 原因是脚本 body marker 和 final marker 撞名，命令回显中提前匹配到了 marker。
   - 这不是 Docker 构建失败；后来用不同 marker 重跑即可。

3. `npm install hyperframes@0.6.42` 第一次失败在 `onnxruntime-node` postinstall。
   - 错误：下载 onnxruntime build list 时返回 HTTP 302，install 脚本没有跟随，退出码 1。
   - 修复：Dockerfile 改为 `ONNXRUNTIME_NODE_INSTALL=skip npm install ...`。
   - 修复后 npm 安装成功，镜像构建成功。

Smoke test：

- 使用历史 manifest：`/data/project/test_ai_botserver.20260626210153/tmp/h20_hyperframes/1517/manifest.json`
- task_id: `1517`
- style: `1`
- template: `science_guide`
- 临时输出目录：`/tmp/h20-hyperframes-renderer-smoke`

执行形式：

```bash
/cm/local/apps/docker/current/bin/docker run --rm --network host --ipc=host \
  -v /data:/data \
  -v /tmp:/tmp \
  -w /data/project/test_ai_botserver \
  -e HF_POSTPROCESS_PYTHON=/usr/bin/python3 \
  -e HF_POSTPROCESS_TRANSLATION_PYTHON=/usr/bin/python3 \
  -e HF_POSTPROCESS_TRANSLATION_SCRIPT=/data/project/test_ai_botserver/router/service/video_server2/hyperframes_subtitle_translation.py \
  -e HYPERFRAMES_SHARED_NODE_MODULES=/opt/hyperframes/deps/hyperframes-0.6.42/node_modules \
  -e APP_CONFIG_FILE=/data/project/test_ai_botserver/config/config-dev.json \
  h20-hyperframes-renderer:0.6.42-node22.22.2 \
  node /data/project/test_ai_botserver/hyperframes-postprocess/index.js \
  --input /tmp/h20-hyperframes-renderer-smoke/manifest.json \
  --output /tmp/h20-hyperframes-renderer-smoke/result.json
```

Smoke test 结果：

```json
{
  "success": true,
  "final_video_path": "/tmp/h20-hyperframes-renderer-smoke/final.mp4",
  "cover_path": "/tmp/h20-hyperframes-renderer-smoke/cover.png",
  "subtitle_timeline_path": "/tmp/h20-hyperframes-renderer-smoke/subtitle_timeline.json",
  "render_ms": 418513,
  "error": ""
}
```

生成文件：

- `/tmp/h20-hyperframes-renderer-smoke/final.mp4`，约 73.9 MB
- `/tmp/h20-hyperframes-renderer-smoke/cover.png`，约 811 KB
- `/tmp/h20-hyperframes-renderer-smoke/subtitle_timeline.json`
- `/tmp/h20-hyperframes-renderer-smoke/result.json`

结论：

- 镜像已经在 H20 测试服构建成功。
- 不依赖 scheduler，直接跑历史 manifest 已经通过。
- 下一步可以先把代码上 test，但保持 `HF_RENDER_BACKEND=local`；确认部署无影响后，再设置 Docker backend 环境变量并重启 scheduler 做完整链路验证。