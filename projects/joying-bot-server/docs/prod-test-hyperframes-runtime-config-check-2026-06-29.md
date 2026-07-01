---
tags: [joying-bot-server, hyperframes, prod, test, release-check]
date: 2026-06-29
---

# 正式服 / 测试服 HyperFrames 配置对比

## 背景

2026-06-29 晚，对照 `vibevideo-master-release-checklist-2026-06-25(1)(1).md` 和现有 Obsidian 发布记录，检查测试服 H20 与正式服 LLM-74 / LLM-76 的网感视频 HyperFrames Docker runner 配置。

本次只读检查，没有改配置、没有重启服务。

## 登录与机器职责

### 测试服 H20

- 登录路径：先登录跳板机 `developer@222.71.55.27:9527`，再从跳板机执行 `sudo ssh -p 10019 root@h20`。
- 主机名：`hgx19`
- 服务：`ai_botserver_sch`
- 当前目录：`/data/project/test_ai_botserver.20260629191919`
- 日志：常见在 `/data/server_logs/supervisord/`

### 正式服 LLM-74

- 登录路径：跳板机 / 正式 API 机器 `developer@222.71.55.27:9527`
- 主机名：`LLM-74`
- 当前正式 API 服务：`ai_botserver_api`
- 当前目录：`/data/project/prod_ai_botserver.20260629201345`
- 旧服务仍在：`ai_autodone_py_prod`，目录 `/data/project/prod_ai_autodone.20260617160207`
- 注意：LLM-74 上的 `ai_botserver_sch` 当前为 `STOPPED`，正式定时任务不在这台机器跑。

### 正式服 LLM-76

- 来源：张晋良提供
- IP：`222.71.55.26`
- SSH 端口：`31222`
- 用户名：`llm-76`
- 密码：用户在本次沟通中提供；不在 Obsidian-Sync 明文保存，避免同步扩散。
- 主机名：`llm76-NF5280M6`
- 服务：`ai_botserver_sch`
- 当前目录：`/data/project/prod_ai_botserver.20260629201403`
- 日志目录：`/data/server_logs/supervisord/botserver_sch.out`

## Jenkins 构建信息

- `Prod_Ai_BotServer`
  - 构建编号：`#27`
  - 构建时间：`2026-06-29 20:13:52`
  - 耗时：`7秒`
  - 状态：构建成功
  - 说明：部署完成，服务已重启
- `Prod_Ai_BotServer_llm76`
  - 构建编号：`#4`
  - 构建时间：`2026-06-29 20:14:09`
  - 耗时：`6秒`
  - 状态：构建成功
  - 说明：部署完成，服务已重启

## Checklist 关键项

- `t_video_generate_task` 需要包含 HyperFrames 相关字段：
  `voice_emotion`, `voice_speed`, `voice_volume`, `templates_style_id`,
  `whisper_timeline_path`, `whisper_timeline_ms`, `analysis_path`, `analysis_ms`,
  `hf_manifest_path`, `hf_result_path`, `hf_final_video_path`, `hf_cover_path`,
  `hf_subtitle_timeline_path`, `hf_render_ms`, `hf_final_video_url`, `hf_cover_url`
- 索引：`idx_video_generate_task_templates_style_id(templates_style_id, task_status)`
- `t_comfyui_config` 需要有可用 `comfyui_url` 模型池；正式试听如需要，需要可用 `voice_audition_url`
- Docker runner 关键环境：
  - `HF_RENDER_BACKEND=docker`
  - `HF_DOCKER_IMAGE=h20-hyperframes-renderer:0.6.42-node22.22.2`
  - `HF_DOCKER_MOUNTS=/data:/data,/tmp:/tmp`
  - `HF_DOCKER_SHM_SIZE=2g`
  - `HF_RENDER_LOCK_TIMEOUT_SECONDS=60`
  - `HF_MAX_CONCURRENCY` 测试服原记录为 `3`

## 实际检查结果

| 项目 | H20 测试 scheduler | LLM-74 正式 API | LLM-76 正式 scheduler |
|---|---|---|---|
| 服务状态 | `RUNNING` | `RUNNING` | `RUNNING` |
| 服务名 | `ai_botserver_sch` | `ai_botserver_api` | `ai_botserver_sch` |
| 代码目录 | `/data/project/test_ai_botserver.20260629191919` | `/data/project/prod_ai_botserver.20260629201345` | `/data/project/prod_ai_botserver.20260629201403` |
| HyperFrames 代码文件 | 存在 | 存在 | 存在 |
| `HF_RENDER_BACKEND` | `docker` | 未设置 | `docker` |
| `HF_MAX_CONCURRENCY` | `3` | 未设置 | `7` |
| `HF_DOCKER_BINARY` | `/cm/local/apps/docker/current/bin/docker` | 未设置 | `/data/script/hf-docker` |
| Docker image tag | `h20-hyperframes-renderer:0.6.42-node22.22.2` | 同 tag 存在 | 同 tag 存在 |
| Docker image id | `sha256:2e436...` | `sha256:2e436...` | `sha256:a4d26...` |
| Docker image created | `2026-06-26T21:39:31+08:00` | `2026-06-26T21:39:31+08:00` | `2026-06-26T21:39:31+08:00` |
| Runtime fallback | node 存在，但 hyperframes bin 直接跑缺 `node` PATH | `/data/project/hyperframes-runtime` 缺失 | `/data/project/hyperframes-runtime` 缺失 |
| DB | `zhugedata_test` | `zhugedata` | `zhugedata` |
| DB 字段 | 缺失：`NONE` | 缺失：`NONE` | 缺失：`NONE` |
| DB 索引 | `templates_style_id,task_status` | `templates_style_id,task_status` | `templates_style_id,task_status` |

## 数据库模型池对比

### H20 测试库 `zhugedata_test`

- `comfyui_url`: active=1 有 4 条，active=0 有 12 条
- 可用 `comfyui_url`：
  - `http://127.0.0.1:6005`
  - `http://127.0.0.1:6006`
  - `http://127.0.0.1:6007`
  - `http://127.0.0.1:6004`
- `voice_audition_url`: active=1 有 3 条，active=0 有 1 条
- 可用 `voice_audition_url`：
  - `http://127.0.0.1:8129`
  - `http://127.0.0.1:8130`
  - `http://127.0.0.1:8131`

### 正式库 `zhugedata`

- `comfyui_url`: active=1 有 10 条，active=0 有 17 条
- 可用 `comfyui_url`：
  - `http://192.192.168.139:6002`
  - `http://192.192.168.139:6003`
  - `http://192.192.168.139:6006`
  - `http://192.192.168.139:6008`
  - `http://192.192.168.47:6001`
  - `http://192.192.168.47:6002`
  - `http://192.192.168.47:6003`
  - `http://192.192.168.47:6004`
  - `http://192.192.168.47:6005`
  - `http://192.192.168.47:6006`
- `voice_audition_url`: active=1 有 2 条，active=0 有 3 条
- 正式可用 `voice_audition_url` 当前值为 `/`，如果正式试听链路依赖这里，需要确认这是否是预期占位值，还是漏配真实 VoxCPM URL。

## 差异与风险

1. 正式 scheduler 实际在 LLM-76，不在 LLM-74。LLM-74 的 `ai_botserver_sch` 停止是符合“定时任务在 LLM-76”这个部署方式的，但后续排查不要只看 LLM-74。

2. 正式 LLM-76 的核心 Docker runner 已配置，并且代码、DB DDL、DB 索引、正式模型池都已到位。不能再按早期检查结论认为正式完全没部署。

3. 测试 H20 当前 `HF_MAX_CONCURRENCY=3`，正式 LLM-76 当前 `HF_MAX_CONCURRENCY=7`。Obsidian 里有 H20 7 并发压测通过记录，但这不是“测试服当前配置”。如果要完全按测试当前配置灰度，正式应先用 3；如果按压测容量上线，7 需要重点观察 CPU/IO/容器残留和任务锁。

4. 正式 LLM-76 的 `HF_DOCKER_BINARY=/data/script/hf-docker`，内容为 `sudo -n /usr/bin/docker "$@"`，是包装器，不改渲染参数。与 H20 的 `/cm/local/apps/docker/current/bin/docker` 路径不同，但功能上应是直接调用 Docker。

5. LLM-76 与 H20/LLM-74 的 Docker image tag 相同，但 image id 不同：
   - H20 / LLM-74：`sha256:2e436...`
   - LLM-76：`sha256:a4d26...`
   这说明同 tag 下实际镜像不是完全同一个 digest。若正式出现 H20 无法复现的问题，需要优先统一镜像或对比 Dockerfile 构建产物。

6. LLM-76 没有 `/data/project/hyperframes-runtime` fallback runtime；在 `HF_RENDER_BACKEND=docker` 正常生效时不是阻塞项，但如果代码 fallback 到 local runtime，会失败。

7. LLM-74 API 进程没有 `HF_RENDER_BACKEND/HF_MAX_CONCURRENCY` 等变量，只看到 `HF_HUB_OFFLINE=1`。如果 API 只负责提交任务、LLM-76 scheduler 负责渲染，这是可以接受的；如果 API 内也会直接触发 HyperFrames 渲染，需要给 API 进程补同一套 env。

## 当前结论

正式服不是没配好：真正跑定时任务的 LLM-76 已经有 HyperFrames Docker runner、正式 DB 字段/索引也齐，模型池可用。

但正式服与 H20 测试服不是完全一致，最需要关注的差异是：

- `HF_MAX_CONCURRENCY`: H20 当前 `3`，LLM-76 正式 `7`
- Docker image digest: H20 `sha256:2e436...`，LLM-76 `sha256:a4d26...`
- 正式 `voice_audition_url` active 值为 `/`
- LLM-74 API 没有完整 HF env，依赖 LLM-76 scheduler 承接渲染

上线后如果正式混剪不能用，优先按这四个点排查。
