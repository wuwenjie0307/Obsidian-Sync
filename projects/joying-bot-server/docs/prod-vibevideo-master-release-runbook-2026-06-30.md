---
date: 2026-06-30
project: joying-bot-server
type: release-runbook
tags: [prod, vibevideo, hyperframes, minimal, hotfix, release, master]
status: draft
---

# 网感视频 / 极简风格正式服问题复盘与上线文档

## 0. 当前结论

今晚正式服已经基本跑通，但这次生产热修还没有进入 `master`。当前代码热修已经独立提交到：

- 分支：`hotfix/prod-video-orientation-stale-20260630`
- 已合入 `master` 提交：`5caa7b2ff8541a4967239eb9526f6c33debd2dd6`
- 已合入 `master` 提交：`5a61a112 fix: extend video model timeout to two hours`
- MR：`https://git.joyingai.cn/services/crm.ai.joyingbot/-/merge_requests/13`
- 状态：已通过命令行 fast-forward 推送到 `origin/master`。验证结果为 `HOTFIX_IN_MASTER`，`origin/master` 最新提交为 `5a61a112`。

当前两个热修提交已经进入 `master`，后续 Jenkins 从 `master` 自动部署时不会再吞掉这次正式服热修。下一步重点是确认 Jenkins 是否已部署到 LLM-74 / LLM-76，并做正式服 smoke test。

本次热修不要再塞回大功能分支作为主路径。正确做法是：

1. 生产热修以 `origin/master` 为基线，单独走 `hotfix -> master`。
2. `master` 合入后，再按需要同步到 `test` 和功能分支。
3. 普通网感大功能仍然走 `feature -> test` 验证，再走 `feature -> master`，但不要把 `test` 合回 `master`。

## 1. 生产拓扑

### LLM-74

- 角色：正式主 API / 部分基础服务。
- 服务：`ai_botserver_api`。
- 当前正式 API 目录：`/data/project/prod_ai_botserver.20260629201345`。
- Whisper 服务：监听 `8188`，正式 scheduler 需要显式访问它。
- 注意：LLM-74 上的 `ai_botserver_sch` 当前不是正式任务执行入口。

### LLM-76

- 角色：正式定时任务 / 视频生成 scheduler / HyperFrames Docker runner / VoxCPM 容器池。
- SSH：`222.71.55.26:31222`，用户 `llm-76`。密码不要写入 Obsidian。
- 服务：`ai_botserver_sch`。
- 当前 scheduler 目录：`/data/project/prod_ai_botserver.20260629201403`。
- 日志：`/data/server_logs/supervisord/botserver_sch.out`。
- Jenkins：`Prod_Ai_BotServer_llm76 #4`，构建时间 `2026-06-29 20:14:09`。

### H20 测试服

- 角色：测试 scheduler / H20 网感视频验证环境。
- 当前记录中 `HF_MAX_CONCURRENCY=3`。
- 用来对照正式环境，但不要默认正式服和 H20 完全一致。

## 2. 今晚正式服出现的问题

### 2.1 VoxCPM 音色克隆容器启动后访问不到应用

现象：

- LLM-76 上 VoxCPM 容器已经起来，容器日志显示 Uvicorn 应用启动完成。
- 宿主机访问 `8110-8121` 不通，`docker ps` 中容器为 `unhealthy`。

根因：

- compose 端口映射是 `宿主机端口:8015`。
- 容器内应用实际监听 `8105`。
- 镜像 healthcheck 也检查了错误端口。

处理：

- 备份 compose。
- 把 `voxcpm-api-docker-compose1.yml` 到 `voxcpm-api-docker-compose15.yml` 的端口映射改为 `宿主机端口:8105`。
- healthcheck 改为 `http://127.0.0.1:8105/health`。
- 修正 14 号 compose 的重复 `container_name`。
- 重建当前运行的 1-12 号容器。

验证：

- `8110-8121 -> 8105/tcp`。
- 宿主机逐个访问 `/health` 返回 200。
- LLM-74 和 LLM-76 访问正式库 active VoxCPM 地址均可达。

### 2.2 网感视频被 `HYPERFRAMES_ROUTE_DISABLED` 拦截

现象：

- 正式任务失败，错误类似：
  `HYPERFRAMES_ROUTE_DISABLED: templates_style_id=2 template_id=video_diary`。

根因：

- `templates_style_id=1/2` 会进入 HyperFrames 路由。
- 该路由依赖 scheduler 进程环境变量 `H20_HYPERFRAMES_ROUTE_ENABLED=1`。
- LLM-76 的 `ai_botserver_sch` 初始缺少这个环境变量。

处理：

- 备份 `/etc/supervisord.d/ai_botserver_sch.conf`。
- 在 `environment=` 中追加 `H20_HYPERFRAMES_ROUTE_ENABLED="1"`。
- `supervisorctl reread`。
- `supervisorctl update ai_botserver_sch`。
- 重启 `ai_botserver_sch`。

验证：

- 新进程环境包含 `H20_HYPERFRAMES_ROUTE_ENABLED=1`。
- 修复后新增 `HYPERFRAMES_ROUTE_DISABLED` 数为 0。

### 2.3 声音克隆阶段 `HEYGEM_STANDARDIZE_FAILED`

现象：

- 正式网感视频任务失败，前端显示：
  `HEYGEM_STANDARDIZE_FAILED: 声音克隆阶段失败`。
- 日志中 `reference_audio_whisper` 阶段连接 `127.0.0.1:8188` 失败。

根因：

- LLM-76 是正式 scheduler 机器，但本机没有 Whisper 8188 服务。
- 代码默认 `WHISPER_SERVER_URL` 回退到 `http://127.0.0.1:8188/whisper/transcribe`。
- H20 本机有 8188，所以测试环境默认值能用；正式 LLM-76 不行。

处理：

- 在 LLM-76 的 `ai_botserver_sch` supervisor 环境中追加：
  `WHISPER_SERVER_URL="http://192.192.168.139:8188/whisper/transcribe"`。
- 重启 `ai_botserver_sch`。

验证：

- LLM-76 新进程环境包含 `WHISPER_SERVER_URL`。
- LLM-76 访问该地址返回 HTTP 400 且提示 `audio_url is required`，说明服务可达。
- 修复后新增 `HEYGEM_STANDARDIZE_FAILED` 数为 0。

### 2.4 `hf-docker` 缺 shebang 导致 Exec format error

现象：

- HyperFrames 任务失败为：
  `HYPERFRAMES_CLI_FAILED: [Errno 8] Exec format error: '/data/script/hf-docker'`。

根因：

- `/data/script/hf-docker` 是文本脚本，但没有 `#!/bin/sh`。
- Python `subprocess` 直接执行该文件时不能识别解释器。

处理：

- 给 `/data/script/hf-docker` 增加 `#!/bin/sh`。
- 保留实际命令：`sudo -n /usr/bin/docker "$@"`。

验证：

- `sudo -u joying /data/script/hf-docker --version` 正常。

### 2.5 HyperFrames 首次渲染慢，Chrome cache 不能复用

现象：

- 新容器首次运行 HyperFrames 时会下载 `chrome-headless-shell`。
- 渲染耗时被显著拉长，也更容易触发外部超时或任务 stale 判断。

根因：

- 每个临时容器都有自己的 `/root/.cache/hyperframes/chrome`。
- 容器退出后缓存丢失。

处理：

- 建立共享缓存目录：
  `/data/project/hyperframes-chrome-cache`。
- wrapper 对 `docker run` 增加挂载：
  `/data/project/hyperframes-chrome-cache:/root/.cache/hyperframes/chrome`。
- 从成功容器复制完整 Chrome cache 到宿主机共享目录。

验证：

- 新容器执行 `hyperframes browser path` 能直接命中共享 cache。

### 2.6 HyperFrames 长渲染任务被通用 stale 保护误杀

现象：

- 部分 `templates_style_id=1/2` 任务已经生成 `hf_result_path` 或 `hf_final_video_url` 前后，被通用 stale 保护标记失败。
- CRM 状态被回调成失败。

根因：

- `scheduler/collect_scheduler.py::_recover_stale_video_processing_tasks` 的旧逻辑只看：
  - `task_status == 2`
  - `updated_time < now - 35min`
  - `generate_video_url` 为空
- HyperFrames 长渲染期间本来就可能没有 `generate_video_url`。
- 旧逻辑没有排除 `templates_style_id=1/2`，导致网感长渲染被误认为卡死。

处理：

- 代码热修：通用 stale recover 排除 HyperFrames 风格：
  - `TEMPLATE_ID_SCIENCE_GUIDE`
  - `TEMPLATE_ID_VIDEO_DIARY`
- 极简旧链路 `templates_style_id=3` 的 stale 保护继续保留。
- 对已误标失败且已经产出结果的任务，手动修正正式库状态并补发 CRM 成功回调。

验证：

- 相关单测通过。
- 修复后网感长渲染不再被通用 stale 保护误杀。

### 2.7 极简风格视频倒置 / 旋转 180 度

现象：

- 极简风格正式服视频出现倒置，例如：
  - `https://videos.joyingai.cn/video/crm/20260630/user4_1782759813813_8ce1c915f553e7fb.mp4`
  - `https://videos.joyingai.cn/video/crm/20260630/user4_1782759845399_72898a5423cb81df.mp4`

根因：

- 输入源里存在 `rotate=90` 或 display matrix `rotation=-90` 这类元数据。
- display matrix 的方向需要按 `(-rotation) % 360` 标准化。
- 旧修复在正式服热修过程中被局部改动影响，导致原来极简链路的旋转烘焙逻辑没有完整保留。
- 正式服 ffmpeg `4.4.2` 不支持新参数 `-display_rotation`，导致清理旋转元数据的命令在正式环境不可用。

修复原则：

- display matrix side data：`(-rotation) % 360`。
- `rotate=90`：`transpose=1`。
- `rotate=270`：`transpose=2`。
- `rotate=180`：`hflip,vflip`。
- 只要标准化后的旋转为 `90/180/270`，就先烘焙画面，再清理旋转元数据。
- 清理旋转元数据时不要用正式 ffmpeg 不支持的 `-display_rotation`。
- 使用兼容命令：
  `-map 0 -map_metadata -1 -metadata:s:v:0 rotate=0 -c copy`。

处理：

- 热修 `router/service/video_server2/video_time_align.py`。
- 修复 `_extract_rotation()`、`_rotation_bake_filter()`、`probe_video_orientation_state()`、`_clear_rotation_metadata()`。
- 在正式服 LLM-76 当前 release 目录同步热修，并重启 `ai_botserver_sch`。

验证：

- 修复后生成的极简风格视频：
  `https://videos.joyingai.cn/video/crm/20260630/user4_1782761898493_4ecd9a36aa8c6af2.mp4`
- 对应任务：`task_id=17675`。
- 本地回归测试：
  `python -m unittest test.test_video_time_align_orientation test.test_video_model_busy_retry`
  结果：`Ran 16 tests`, `OK`。

### 2.8 模型池可用数被保护逻辑切低

现象：

- 正式库 `t_comfyui_config` 下午曾有多条可用配置，后续部分被切成不可用或运行中。
- 表象是视频任务卡住，容器池可用资源减少。

判断原则：

- 不要看到 `is_active=2` 就直接改回 `1`。
- 先确认是否有真实任务正在使用对应模型池。
- 再区分是：
  - 真实容器挂掉。
  - 任务长时间运行但仍活跃。
  - 被保护逻辑因为超时误切不可用。
  - 运维或同事主动下线。

处理原则：

1. 先查正式库配置和最近任务。
2. 对真实挂掉的容器，重启容器。
3. 对被误切且服务健康的配置，恢复调度可用。
4. 对有活跃任务的配置，先不要强制重置，避免一条任务被重复执行或重复回调。

### 2.9 视频模型默认超时仍是 30 分钟

现象：

- 领导要求视频模型任务最多等待 2 小时。
- 超过 2 小时后，再触发模型池隔离，把对应 `t_comfyui_config.is_active` 切成不可用。
- 检查 hotfix 版本时发现两个视频模型服务默认值仍是 `1800` 秒。

根因：

- 之前的热修只包含极简旋转和 HyperFrames stale 误杀修复。
- `router/service/video_server/video_gen_service.py` 和 `router/service/video_server2/video_gen_service.py` 的 `DEFAULT_HEYGEM_TIMEOUT_SECONDS` 没有改到 `7200`。

处理：

- 本地 hotfix 分支新增提交：
  `5a61a112 fix: extend video model timeout to two hours`
- 两个服务的默认 HeyGem / 视频模型轮询超时都改为 `7200` 秒。
- 新增回归测试锁住默认值，避免后续回退到 30 分钟。

验证：

- 新增测试先按 TDD 方式确认失败：`7200 != 1800`。
- 改完后运行：
  `python -m unittest test.test_video_time_align_orientation test.test_video_model_busy_retry`
  结果：`Ran 17 tests`, `OK`。

待办：

- 该提交已推送到 `hotfix/prod-video-orientation-stale-20260630`，并已 fast-forward 推送到 `origin/master`。

## 3. 当前正式服关键配置

### LLM-76 scheduler 必需环境变量

```text
H20_HYPERFRAMES_ROUTE_ENABLED=1
WHISPER_SERVER_URL=http://192.192.168.139:8188/whisper/transcribe
HF_RENDER_BACKEND=docker
HF_MAX_CONCURRENCY=7
HF_DOCKER_BINARY=/data/script/hf-docker
HF_DOCKER_IMAGE=h20-hyperframes-renderer:0.6.42-node22.22.2
HF_DOCKER_MOUNTS=/data:/data,/tmp:/tmp
HF_DOCKER_SHM_SIZE=2g
HF_RENDER_LOCK_TIMEOUT_SECONDS=60
```

注意：

- H20 当前记录是 `HF_MAX_CONCURRENCY=3`，正式 LLM-76 是 `7`。这不是配置一致状态。
- 如果正式服 CPU / IO / Chromium / ffmpeg 压力高，优先把正式并发降到 `3` 做灰度。
- `HF_MAX_CONCURRENCY` 控制 HyperFrames 同时渲染容器数，不是模型推理容器并发。

### 正式数据库关键表

- 库：`zhugedata`
- 任务表：`t_video_generate_task`
- 模型池表：`t_comfyui_config`

检查模型池：

```sql
SELECT id, config_key, config_value_audio, config_value, is_active, type, description, updated_time
FROM zhugedata.t_comfyui_config
WHERE config_key IN ('comfyui_url', 'voice_audition_url')
ORDER BY config_key, id;
```

检查最近失败：

```sql
SELECT id, task_id, job_id, templates_style_id, task_status, callback_status,
       fail_reason, generate_video_url, hf_final_video_url, updated_time
FROM zhugedata.t_video_generate_task
WHERE updated_time >= DATE_SUB(NOW(), INTERVAL 6 HOUR)
  AND (task_status = -1 OR callback_status = -1 OR fail_reason IS NOT NULL)
ORDER BY updated_time DESC
LIMIT 100;
```

检查疑似卡住任务：

```sql
SELECT id, task_id, job_id, templates_style_id, task_status, callback_status,
       generate_video_url, hf_result_path, hf_final_video_url, updated_time
FROM zhugedata.t_video_generate_task
WHERE task_status = 2
ORDER BY updated_time ASC
LIMIT 100;
```

## 4. 上线流程

### 4.1 分支策略

这次正式服差异不建议走：

```text
prod hotfix -> feature -> test -> feature -> master
```

原因：

- 功能分支是网感大功能分支，包含大量业务改动。
- 今晚生产热修是对已上 `master` 的正式事故修复，应保持最小差异。
- 把生产热修塞回功能分支，会扩大 review 面和合并风险。

推荐流程：

```text
hotfix branch from origin/master
  -> MR hotfix -> master
  -> Jenkins deploy master to LLM-74 / LLM-76
  -> smoke test production
  -> cherry-pick or merge master hotfix back to test / feature when needed
```

普通大功能流程仍然是：

```text
feature -> test
feature -> master
```

约束：

- 不要把 `test` 合到 `master`。
- 不要把今晚正式服热修混进大功能分支作为唯一来源。
- 如果 `test` 也需要验证同一热修，优先 cherry-pick 同一个 hotfix commit 或单独 MR hotfix -> test。

### 4.2 当前待合代码

当前待合代码包含 2 个 hotfix commit：

```text
5caa7b2ff8541a4967239eb9526f6c33debd2dd6 fix: repair prod video orientation handling
5a61a112 fix: extend video model timeout to two hours
```

包含文件：

```text
router/service/video_server2/video_time_align.py
router/service/video_server/video_gen_service.py
router/service/video_server2/video_gen_service.py
scheduler/collect_scheduler.py
test/test_video_time_align_orientation.py
test/test_video_model_busy_retry.py
```

验证：

```bash
python -m unittest test.test_video_time_align_orientation test.test_video_model_busy_retry
```

期望：

```text
Ran 16 tests
OK
```

### 4.3 合入 master 前检查

1. 确认待合内容只包含 2 个 hotfix commit。
2. 确认目标分支是 `master`。
3. 确认没有把 `test` 合入 `master`。
4. 确认测试结果通过。
5. 确认 diff 只包含上述 6 个文件。
6. 确认生产当前手动热修和 MR 代码一致。

### 4.4 Jenkins 部署后检查

部署完成后在 LLM-76 检查：

```bash
supervisorctl status ai_botserver_sch
readlink -f /proc/$(pgrep -f 'ai_botserver_sch' | head -1)/cwd
tr '\0' '\n' < /proc/$(pgrep -f 'ai_botserver_sch' | head -1)/environ | grep -E 'H20_HYPERFRAMES|WHISPER|HF_'
```

需要看到：

- 服务 `RUNNING`。
- cwd 指向最新 Jenkins release 目录。
- 环境变量包含：
  - `H20_HYPERFRAMES_ROUTE_ENABLED=1`
  - `WHISPER_SERVER_URL=...8188/whisper/transcribe`
  - `HF_RENDER_BACKEND=docker`
  - `HF_DOCKER_BINARY=/data/script/hf-docker`
  - `HF_DOCKER_IMAGE=h20-hyperframes-renderer:0.6.42-node22.22.2`

## 5. 上线后 smoke test

### 5.0 当前部署检查（2026-06-30 19:24 CST）

结论：`master=5a61a112` 已合入代码仓库，但截至 2026-06-30 19:24 CST 尚未部署到正式服 LLM-74 / LLM-76 的当前运行 release。

LLM-76 scheduler 检查结果：

```text
host: llm76-NF5280M6
service: ai_botserver_sch RUNNING
pid: 895381
cwd: /data/project/prod_ai_botserver.20260629201403
start: 2026-06-30 03:21:43 CST
symlink: /data/project/prod_ai_botserver -> /data/project/prod_ai_botserver.20260629201403
```

代码状态：

```text
router/service/video_server/video_gen_service.py:
DEFAULT_HEYGEM_TIMEOUT_SECONDS = 1800

router/service/video_server2/video_gen_service.py:
DEFAULT_HEYGEM_TIMEOUT_SECONDS = 1800

router/service/video_server2/video_time_align.py:
已包含 return (-int(rotation)) % 360
已包含 -map_metadata -1 / -metadata:s:v:0 rotate=0

scheduler/collect_scheduler.py:
已包含 templates_style_id=1/2 HyperFrames stale 排除逻辑
```

判断：

- LLM-76 当前运行目录仍是 2026-06-29 20:14 发布目录。
- 极简旋转和 stale 排除属于今晚直接热补丁，已经在当前目录内。
- 2 小时模型超时没有部署，当前仍是 30 分钟。

LLM-74 API 检查结果：

```text
host: LLM-74
service: ai_botserver_api RUNNING
service: ai_botserver_sch STOPPED
pid: 3080069
cwd: /data/project/prod_ai_botserver.20260629201345
start: 2026-06-29 20:13:52 CST
symlink: /data/project/prod_ai_botserver -> /data/project/prod_ai_botserver.20260629201345
```

代码状态：

```text
router/service/video_server/video_gen_service.py:
DEFAULT_HEYGEM_TIMEOUT_SECONDS = 1800

router/service/video_server2/video_gen_service.py:
DEFAULT_HEYGEM_TIMEOUT_SECONDS = 1800

router/service/video_server2/video_time_align.py:
仍包含 -display_rotation 0
未看到 return (-int(rotation)) % 360

scheduler/collect_scheduler.py:
未看到 HyperFrames stale 排除逻辑
```

判断：

- LLM-74 也没有部署 `master=5a61a112`。
- LLM-74 不是正式 scheduler 入口，但 API 当前目录仍不是最新 master 构建产物。

下一步：

1. 触发或等待 Jenkins 从 `master=5a61a112` 构建并部署：
   - `Prod_Ai_BotServer`
   - `Prod_Ai_BotServer_llm76`
2. 部署后重新检查 LLM-76 当前运行目录，确认两个 `video_gen_service.py` 都是 `7200`。
3. 部署后重新检查 LLM-74 当前运行目录，确认 `video_time_align.py` 不再包含 `-display_rotation`。
4. 再跑极简 / 科普指南 / 视频日记 smoke test。

至少跑 3 条：

1. 极简风格 `templates_style_id=3`。
2. 科普指南 `templates_style_id=1`。
3. 视频日记 `templates_style_id=2`。

极简风格重点看：

- 视频不倒置。
- rotate/display matrix 已正确烘焙。
- 混剪素材与文案时间段不明显错位。
- 任务成功回调 CRM。

网感 HyperFrames 重点看：

- 不再出现 `HYPERFRAMES_ROUTE_DISABLED`。
- 不再出现 `HEYGEM_STANDARDIZE_FAILED` 且日志指向 `127.0.0.1:8188`。
- 不再出现 `hf-docker Exec format error`。
- 长渲染不会被通用 stale 保护误杀。
- `hf_final_video_url` 和 `hf_cover_url` 正常回写。

## 6. 监控窗口

上线后至少观察 30-60 分钟：

1. `t_video_generate_task` 最近失败。
2. `t_comfyui_config` 中 `is_active=2` 是否长期不恢复。
3. LLM-76 上 HyperFrames 容器是否异常堆积。
4. LLM-76 CPU / IO / ffmpeg / Chromium 进程数。
5. CRM callback 是否持续成功。

常用日志：

```bash
tail -f /data/server_logs/supervisord/botserver_sch.out
```

常用关键字：

```text
HYPERFRAMES_ROUTE_DISABLED
HEYGEM_STANDARDIZE_FAILED
Exec format error
VIDEO_PROCESSING_STALE_TIMEOUT
orientation
display matrix
rotate
callback failed
```

## 7. 回滚方案

如果 master 合入后新版本异常：

1. 不要直接改库重跑所有失败任务。
2. 先判断失败是否已经回调 CRM，避免重复回调或重复结算。
3. 回滚代码：
   - revert hotfix commit，或重新部署上一版 release。
4. 回滚 supervisor 环境时要谨慎：
   - `H20_HYPERFRAMES_ROUTE_ENABLED=1` 是网感路由必需项。
   - `WHISPER_SERVER_URL` 是 LLM-76 调 LLM-74 Whisper 的必需项。
   - 不建议无脑恢复到缺环境变量的旧配置。
5. 若是并发压力问题，优先降低 `HF_MAX_CONCURRENCY`，不要直接关掉路由。

## 8. 仍需确认的事项

1. 确认 Jenkins 是否已经从 `master=5a61a112` 部署到 LLM-74 / LLM-76。
2. 部署后执行正式服 smoke test：极简、科普指南、视频日记各一条。
3. 正式 `HF_MAX_CONCURRENCY=7` 是否继续保留，还是先降到与 H20 当前一致的 `3`。
4. `voice_audition_url` 正式 active 配置是否应从占位值调整为真实 VoxCPM URL。
5. 已经失败且回调过 CRM 的历史任务是否需要业务侧重新发起，而不是直接改库重跑。

## 9. 相关记录

- [[projects/joying-bot-server/bugs/prod-voxcpm-port-mapping-healthcheck-fix-2026-06-29|正式服音色克隆容器启动后访问不到应用]]
- [[projects/joying-bot-server/bugs/prod-hyperframes-route-disabled-env-missing-2026-06-30|正式服 HYPERFRAMES_ROUTE_DISABLED]]
- [[projects/joying-bot-server/bugs/prod-whisper-server-url-missing-2026-06-30|正式服 HEYGEM_STANDARDIZE_FAILED 声音克隆阶段失败]]
- [[projects/joying-bot-server/bugs/prod-hyperframes-runtime-shebang-cache-stale-2026-06-30|正式服 Hyperframes hf-docker / Chrome cache / stale 误杀]]
- [[projects/joying-bot-server/docs/prod-test-hyperframes-runtime-config-check-2026-06-29|正式服 / 测试服 HyperFrames 配置对比]]
- [[projects/joying-bot-server/docs/prod-hyperframes-docker-runner-mount-check-2026-06-29|正式服 HyperFrames Docker runner 挂载检查]]
