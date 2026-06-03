---
date: "2026-06-03"
tags: [changelog, h20, docker, model-pool, production-handoff, voxcpm, latentsync]
---

# h20 测试服当前状态与生产落地交接

## 改动类型

- [ ] 新功能
- [ ] Bug 修复
- [ ] 重构
- [x] 配置变更

## 当前一句话结论

h20 测试服已经验证完“VoxCPM 声音克隆 + LatentSync 唇形同步”的 Docker 多实例和数据库资源池调度逻辑；当前状态应对外表述为：测试服验证通过，进入生产部署对齐阶段，不是已经可以无条件直接切生产。

## 当前 h20 测试服状态

### 1. Docker 多实例

当前测试服已按服务组跑通两组模型服务：

| 服务组 | 声音克隆 VoxCPM | 唇形同步 LatentSync | DB config_id |
|---|---|---|---|
| 第 1 组 | `http://127.0.0.1:8120` | `http://127.0.0.1:8121` | `id=1` |
| 第 2 组 | `http://127.0.0.1:8122` | `http://127.0.0.1:8123` | `id=2` |

健康检查口径：

```bash
curl -s http://127.0.0.1:8120/health
curl -s http://127.0.0.1:8121/health
curl -s http://127.0.0.1:8122/health
curl -s http://127.0.0.1:8123/health
```

预期均为：

```json
{"status":"ok"}
```

### 2. DB 调度规则

`zhugedata_test.t_comfyui_config` 当前不是按“声音类型/唇形类型”分开调度，而是一行代表一套完整服务组。

字段约定：

```text
config_value_audio = VoxCPM 声音克隆地址
config_value       = LatentSync 唇形同步地址
is_active=1        = 空闲，可被 scheduler 领取
is_active=2        = 使用中，已被任务锁定
is_active=0        = 禁用，不参与调度
```

示例：

```text
id=1: config_value_audio=8120, config_value=8121
id=2: config_value_audio=8122, config_value=8123
```

注意：截图里如果 `id=1/id=2` 显示 `is_active=2`，含义是当前正在被任务占用；新增或启用正式可调度记录时应写 `is_active=1`，不是 `2`。

### 3. 代码读取逻辑

当前代码逻辑是：scheduler 从 `t_comfyui_config` 里找 `config_key='comfyui_url' and is_active=1` 的一行，领取后改成 `is_active=2`，然后把同一行里的两个地址传给任务。

调用关系：

```text
scheduler 领取 t_comfyui_config 一行
-> config_value_audio 传给 VoxCPM /v1/clone-voice
-> config_value 传给 LatentSync /v1/lip-sync
-> 一个视频任务独占这一整套服务组
-> 任务完成或失败后释放 is_active 回 1
```

因此 `description` 和 `type` 当前不参与调度，只用于人工理解。建议 description 不要写成单个模型名，最好写成：

```text
h20 group 1: voxcpm-8120 + latentsync-8121
h20 group 2: voxcpm-8122 + latentsync-8123
```

## 已和晋良哥对齐的信息

### Docker 是否用 yml 启动

h20 测试服 Docker compose 文件：

```text
/data/project/test_ai_botserver/deploy/docker/docker-compose.h20.yml
```

本地仓库对应文件：

```text
deploy/docker/docker-compose.h20.yml
```

当前启动方式：

```bash
cd /data/project/test_ai_botserver
/cm/local/apps/docker/current/bin/docker compose -f deploy/docker/docker-compose.h20.yml up -d
```

### 多实例磁盘占用口径

同一个 image 启多个容器时，镜像层本身是共享的一份；多个实例不会各自复制整份镜像。真正需要控制的是日志、临时文件、视频输出、少量容器 writable layer，以及每个实例运行时单独占用的 GPU 显存和进程内存。

### 当前建议挂载目录

容器内临时/输出目录：

```text
/data/video_tmp
```

宿主机挂载：

```text
/data/video_tmp -> /data/video_tmp
```

模型缓存：

```text
/root/.cache/huggingface -> /data/model_cache/huggingface
```

LatentSync 权重：

```text
/opt/LatentSync/checkpoints -> /data/models/LatentSync-1.6
```

日志现状：

```text
当前服务日志主要走 stdout/stderr，由 docker logs / json-file 管理。
如需文件日志，可新增 /data/logs 挂载，并调整启动命令或日志配置。
```

### 模型是否放镜像

两个模型约各 5G。结论：

```text
可以做包含模型的 fat image 作为迁移/灾备备用方案；正式服主方案更建议镜像放代码和环境，模型权重独立挂载或作为模型制品管理。
```

原因：

- 同一台机器上同一个 image 多实例会共享镜像层，不会因启动 6 个容器复制 6 份镜像。
- 但模型放进镜像后，每次模型更新都要重打、推送、拉取大镜像。
- 多个实例运行时仍会各自占用 GPU 显存，显存不会因为共享镜像层而共享。

## 当前分工建议

### 晋良哥侧

主要负责生产部署落地：

- Docker 多实例编排。
- yml 固化。
- 端口和 GPU 分配。
- 日志、视频输出、临时目录挂载。
- 镜像 tag 和启动命令。
- 生产环境健康检查和回滚方式。

### 我们侧

主要负责代码和 DB 配合验证：

- 确认 `t_comfyui_config` 配置规则。
- 配合提供初始化 SQL。
- 验证 scheduler 能按多条 active 配置领取任务。
- 验证任务完成后资源池释放。
- 跟进异常任务导致资源未释放的兜底问题。

## 早会口径

简短版：

```text
h20 测试服这边已经验证完了，两个模型服务可以用 Docker 多开，代码也能按数据库配置自动调度。现在剩下主要是生产部署工作，比如 Docker 怎么起、多实例端口/GPU 怎么分、日志和视频目录怎么挂，这块已经跟晋良哥对齐，让他那边来落。我这边后面配合确认数据库配置和任务能不能正常跑就行。
```

更短版：

```text
h20 测试服这边 Docker 多开和数据库调度都能跑了。接下来主要是晋良哥那边做生产部署和目录挂载，我这边配合看 DB 配置和任务验证。
```

如果被问是否可以直接上生产：

```text
测试服链路已经验证通过，可以进入生产部署准备；正式切生产前还要把 compose、DB 初始化 SQL、挂载目录、健康检查和回滚方案固化，并做一次生产环境灰度验证。
```

## 生产前剩余项

还不能说 100% 生产就绪，剩余项如下：

1. 把 h20 现场实际 `docker-compose.h20.yml` 固化回 Git 或生产运维目录。
2. 确认正式服镜像 tag、GPU 绑定、端口分配。
3. 固化模型权重/缓存挂载策略。
4. 准备 `t_comfyui_config` 幂等初始化 SQL。
5. 准备健康检查命令和回滚命令。
6. 做生产灰度验证：至少 1 个任务完整跑通，最好再做 2 个并发任务。
7. 继续确认任务异常时 `is_active=2` 是否能兜底释放，避免模型池被锁死。

## 影响范围

- 影响 h20 测试服 Docker 模型服务部署和 DB 模型池配置。
- 不直接修改生产服。
- 不改变 CRM 入口，仍走现有视频任务入库和 scheduler 调度链路。
- 生产切换前需要运维、DB、代码验证三方确认。

## 相关 Commit

- `1435d36e fix: route scheduled model calls through config`
- h20 当前发布目录曾核验：`/data/project/test_ai_botserver -> /data/project/test_ai_botserver.20260602145953`

## 2026-06-03 11:40 h20 测试服新增第三组 Docker 模型服务

本次在 h20 当前部署目录追加并启动第三组 Docker 模型服务，用于提升视频生成并发：

- compose 文件：`/data/project/test_ai_botserver/deploy/docker/docker-compose.h20.yml`
- 远程备份：`/tmp/docker-compose.h20.yml.backup.20260603113754`
- 新增容器：
  - `voxcpm-api-h20-test-3`，端口 `8124`，GPU5，健康检查 ok
  - `latentsync-api-h20-test-3`，端口 `8125`，GPU6，健康检查 ok
- 共享挂载：`/data/video_tmp`、`/data/model_cache/huggingface`、`/data/models/LatentSync-1.6`
- 测试库新增资源池：`zhugedata_test.t_comfyui_config.id=10`
  - `config_value_audio=http://127.0.0.1:8124`
  - `config_value=http://127.0.0.1:8125`
  - `is_active=1` 写入后已被 scheduler 领取为 `2`
- 验证结果：`8124/8125 /health` 均返回 `{"status":"ok"}`；scheduler 已开始使用新增资源处理排队任务，测试服视频生成并发从 2 路提升到 3 路。

注意：当前远程 compose 已修改，但本地 Git 工作区的 `deploy/docker/docker-compose.h20.yml` 仍是旧单组版本；后续需要把远程现场配置固化回 Git 或生产运维目录，避免 Jenkins/重新部署覆盖。
