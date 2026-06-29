---
date: 2026-06-29
project: joying-bot-server
type: doc
tags: [doc, production, hyperframes, docker, deployment, mount]
aliases: [prod-hyperframes-docker-runner-mount-check-2026-06-29]
---

# 正式服 HyperFrames Docker runner 挂载检查

## 背景

准备把网感视频 H20 HyperFrames 功能上线到正式服时，需要给 botserver / scheduler 进程配置 Docker runner 环境变量。

讨论中的配置为：

```bash
HF_RENDER_BACKEND=docker
HF_DOCKER_IMAGE=h20-hyperframes-renderer:0.6.42-node22.22.2
HF_DOCKER_BINARY=/cm/local/apps/docker/current/bin/docker
HF_DOCKER_MOUNTS=/data/hyperframes:/data,/tmp:/tmp
HF_DOCKER_SHM_SIZE=2g
HF_RENDER_LOCK_TIMEOUT_SECONDS=60
HF_MAX_CONCURRENCY=3
```

运维侧指出：正式服务器上所有项目和服务都在 `/data` 下，不能直接把整个 `/data` 挂载给临时容器。这个安全判断是对的。

## 正式服只读检查结果

检查时间：2026-06-29 20:23 CST。

本次只读检查，没有改配置、没有重启、没有写文件。

生产环境当前状态：

- 机器：`LLM-74`
- 正式服务目录：`/data/project/prod_ai_autodone -> /data/project/prod_ai_autodone.20260617160207`
- 正式进程：`ai_autodone_py_prod`
- 进程 cwd：`/data/project/prod_ai_autodone.20260617160207`
- 当前正式进程没有 `HF_` / `HYPERFRAMES_` 环境变量
- `/data/hyperframes` 目录当前不存在
- 当前正式代码目录里暂时没有：
  - `hyperframes-postprocess`
  - `router/service/video_server2/hyperframes_cli.py`
  - `deploy/docker/hyperframes-renderer/Dockerfile`
- Docker 可用，当前只看到旧的 `duix.avatar` 容器，没有 `h20-hyperframes-renderer:0.6.42-node22.22.2` 镜像

结论：正式环境当前还没有部署新网感视频 HyperFrames 代码，也没有准备 HyperFrames Docker runner 镜像和运行环境变量。

## 挂载结论

不能直接把下面这个配置用于当前代码：

```bash
HF_DOCKER_MOUNTS=/data/hyperframes:/data,/tmp:/tmp
```

原因：当前 Docker runner 的执行方式会在容器内访问宿主机项目路径和任务产物路径，例如：

```text
-w /data/project/prod_ai_autodone.<release>
node /data/project/prod_ai_autodone.<release>/hyperframes-postprocess/index.js
--input /data/project/prod_ai_autodone.<release>/tmp/h20_hyperframes/<task_id>/manifest.json
--output /data/project/prod_ai_autodone.<release>/tmp/h20_hyperframes/<task_id>/result.json
```

如果只挂：

```text
宿主机 /data/hyperframes -> 容器 /data
```

那么容器里的 `/data/project/prod_ai_autodone.<release>` 实际会对应宿主机：

```text
/data/hyperframes/project/prod_ai_autodone.<release>
```

这个路径当前不存在，也不是 botserver 的真实发布目录，所以容器会找不到项目代码、`hyperframes-postprocess/index.js`、manifest 或输出路径。

## 2026-06-29 临时上线决策

现阶段为了快速上线，先接受以下挂载配置：

```bash
HF_DOCKER_MOUNTS=/data:/data,/tmp:/tmp
```

这不是因为它是最终最安全方案，而是因为：

- 当前代码按 `/data/project/prod_ai_autodone.<release>/...` 访问项目代码和任务文件，`/data:/data` 可以保持容器内外路径一致。
- 测试服已使用同类挂载方式验证过，没有出现误删或异常清理宿主机 `/data` 的情况。
- 当前 HyperFrames runner 正常流程主要是读项目代码、读 manifest / 素材，写 `result.json`、`final.mp4`、`cover.png`、`subtitle_timeline.json` 等产物；没有发现主动删除 `/data` 项目文件的逻辑。
- `docker run --rm` 只删除临时容器本身，不会删除宿主机 `/data` 里的文件。

风险说明：

- `/data:/data` 会把宿主机整个 `/data` 以读写方式暴露给临时渲染容器，权限面较大。
- 如果未来脚本路径计算出错、第三方工具异常写入/删除，理论影响范围会比只挂 release 目录更大。

当前取舍：先按 `/data:/data,/tmp:/tmp` 上线；后续如果运维或安全要求收窄挂载，再改为只挂 release 目录，或推动代码把 HyperFrames 工作目录迁移到 `/data/hyperframes`。

## 短期上线建议

安全上不挂整个 `/data`，但要保证容器能按同一路径看到当前 release 目录。

短期建议挂当前正式 release 目录到容器内同路径：

```bash
HF_RENDER_BACKEND=docker
HF_DOCKER_IMAGE=h20-hyperframes-renderer:0.6.42-node22.22.2
HF_DOCKER_BINARY=/usr/bin/docker
HF_DOCKER_MOUNTS=/data/project/prod_ai_autodone.<release>:/data/project/prod_ai_autodone.<release>,/tmp:/tmp
HF_DOCKER_SHM_SIZE=2g
HF_RENDER_LOCK_TIMEOUT_SECONDS=60
HF_MAX_CONCURRENCY=3
```

如果仍使用当前正式 release 目录，则示例为：

```bash
HF_DOCKER_MOUNTS=/data/project/prod_ai_autodone.20260617160207:/data/project/prod_ai_autodone.20260617160207,/tmp:/tmp
```

但正式发版后 release 目录会变化，必须以当次服务进程的真实 cwd 为准：

```bash
readlink -f /proc/<ai_autodone_py_prod_pid>/cwd
```

注意：如果代码里引用的素材、临时音频或视频路径不在当前 release 目录和 `/tmp` 下面，还需要额外挂载那些路径；不要默认只挂 release 目录就一定覆盖所有输入文件。

## 长期方案

如果一定要用 `/data/hyperframes` 做隔离目录，需要配套改代码，而不是只改环境变量。

长期改造方向：

1. 让 HyperFrames 的工作目录、manifest、result、final.mp4、cover.png、subtitle_timeline.json 都写到 `/data/hyperframes/...`。
2. 保证容器可以访问 `hyperframes-postprocess/index.js`，可以选择把项目 release 目录只读挂进去，或者把 postprocess 代码打入镜像。
3. 对宿主机 `/data/hyperframes` 增加定时清理策略，因为 `docker run --rm` 只会删除容器，不会删除挂载目录里的宿主机文件。
4. 上线前做一次 smoke test，确认容器内可读 manifest、可读素材、可写 result/final/cover，且宿主机能上传最终产物。

## 推荐给运维/后端的说明

可以这样同步：

```text
安全上不能挂整个 /data，我认可。
但当前代码直接配置 /data/hyperframes:/data 会让容器找不到 /data/project/prod_ai_autodone.<release> 下的项目代码和 manifest。
短期建议挂当前 release 目录到容器内同路径，再挂 /tmp，不挂整个 /data。
如果一定要统一用 /data/hyperframes 隔离，需要代码把 HyperFrames 工作目录迁过去，并增加宿主机产物清理策略。
```

## 图谱链接

- [[projects/joying-bot-server/00-项目概览|项目概览]]
- [[projects/joying-bot-server/docs/00-docs-index|参考文档索引]]
- [[projects/joying-bot-server/docs/h20-hyperframes-docker-runner-release-plan-2026-06-26|H20 HyperFrames Docker runner 上线方案]]
- [[projects/joying-bot-server/docs/h20-hyperframes-concurrency-capacity-summary-2026-06-29|HyperFrames 并发压测记录]]
