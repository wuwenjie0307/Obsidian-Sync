---
date: "2026-06-16"
project: joyingbot-new
type: doc
tags: [doc, h20, gitlab, branch-merge, test, master, docker, gpu, runtime]
aliases: ["H20 分支合并与运行状态复查 2026-06-16"]
---

# H20 分支合并与运行状态复查 2026-06-16

## 图谱链接

- 项目: [[projects/joyingbot-new/00-项目概览|joyingbot-new]]
- 索引: [[projects/joyingbot-new/docs/00-docs-index|参考文档索引]]

## 背景

2026-06-16 对 `feature/ai_v6.3.1_video_new`、`test`、`master` 的合并关系做了复查，并在 H20 测试机重启 bot 服务、确认 Docker/GPU 模型服务状态。

本记录不包含 SSH 密码、数据库连接、token 等敏感信息。

## 结论

- `feature/ai_v6.3.1_video_new` 已合入 `test`，合并时保留了 `test` 上的 README 内容，没有把 `test` 反向合入功能分支。
- 后续如果将 `feature/ai_v6.3.1_video_new` 合入 `master`，不会把 `test` 上别人改的几百个提交带入 `master`。
- H20 上 `8100`、`8017`、`18017` 已重启到当前 release 目录 `/data/project/test_ai_botserver.20260616093915`。
- 昨天停掉的旧 1-4 卡测试容器仍在 Docker 列表里，但都是 `Exited`，没有运行。
- 当前另有新容器在跑：GPU 1/2/3 上有 VoxCPM 容器，GPU 1 上还有 Duix 容器，GPU 4 基本空闲。
- VoxCPM 新容器虽然 `Up`，但 Docker health 为 `unhealthy`，`8110-8120` 的 `/health` 无响应；调度日志显示模型配置健康检查失败，模型池仍需单独处理。

## Git 分支证据

### feature -> test

目标: 将 `origin/feature/ai_v6.3.1_video_new` 合入 `origin/test`，但不污染功能分支。

执行方式:

- 从 `origin/test` 创建临时 worktree/本地合并分支。
- 在目标侧合入 `origin/feature/ai_v6.3.1_video_new`。
- 冲突文件为 `README.md`，按要求保留 `test` 版本。
- 推送 `HEAD:test`，当时生成的 merge commit 为 `bf01685d`。
- 随后远端 `test` 又前进到 `a6f6db4a`，但 `feature_is_ancestor_of_test=yes` 仍成立。

关键原则:

- 只做 `source branch -> target branch`。
- 不为了查冲突或合并而把 `test`/`master` 反向合进功能分支。
- 冲突检查用 `git merge-tree <target> <source>` 或目标侧临时 worktree。

### feature -> master 风险判断

最新复查时的远端:

- `origin/master`: `3d20eb7e`
- `origin/test`: `a6f6db4a`
- `origin/feature/ai_v6.3.1_video_new`: `93d0bfd4`

证据:

```text
git rev-list --left-right --count origin/master...origin/feature/ai_v6.3.1_video_new
=> 4    78

git rev-list --left-right --count origin/test...origin/feature/ai_v6.3.1_video_new
=> 898  0

git merge-base --is-ancestor origin/test origin/feature/ai_v6.3.1_video_new
=> no

git merge-base --is-ancestor origin/feature/ai_v6.3.1_video_new origin/test
=> yes

git log --oneline --merges origin/master..origin/feature/ai_v6.3.1_video_new
=> empty
```

解释:

- 功能分支相对 `master` 只多 78 个整理过的功能提交。
- `test` 有 898 个功能分支没有的提交，说明功能分支没有吸收 `test` 的别人代码。
- `test` 不是功能分支祖先，功能分支是 `test` 的祖先，是因为功能分支已合入 `test`。
- 功能分支相对 `master` 没有 merge commit，因此没有把 `test` 合进来的历史痕迹。
- `git merge-tree origin/master origin/feature/ai_v6.3.1_video_new` 模拟成功，未报冲突。

## H20 运行状态

### Release 与进程

当前 release symlink:

```text
/data/project/test_ai_botserver -> /data/project/test_ai_botserver.20260616093915
```

重启前:

- `8100` 跑在旧目录 `/data/project/test_ai_botserver.20260615161623`。
- `8017` 跑在 `/data/project/test_ai_botserver.20260616093915`。
- `18017` 跑在 `/data/project/test_ai_botserver.20260616093915`。

重启后:

- `8100` PID `152366`，cwd `/data/project/test_ai_botserver.20260616093915`，`/status/check` 返回 `{"status":"ok"}`。
- `8017` PID `152245`，cwd `/data/project/test_ai_botserver.20260616093915`，`/status/check` 返回 `{"status":"ok"}`。
- `18017` PID `152282`，cwd `/data/project/test_ai_botserver.20260616093915`。该 scheduler 进程 `/status/check` 返回 404，但进程运行正常。
- Supervisor: `ai_botserver`、`ai_botserver_sch` 均为 `RUNNING`。

### Docker / GPU 1-4

旧测试容器状态:

```text
voxcpm-api-h20-test*              Exited 12 hours ago
voxcpm-audition-api-h20-test-1..4 Exited 12 hours ago
latentsync-api-h20-test*          Exited 12 hours ago
duix-avatar-h20-test-6004..6007   Exited 12 hours ago
```

当前运行中的新容器:

- GPU 1:
  - `voxcpm-api-h20-1..4`，端口 `8110-8113`，状态 `Up`，health `unhealthy`。
  - `duix-avatar-gen-video-1..6`，端口 `8103-8108`，状态 `Up`。
- GPU 2:
  - `voxcpm-api-h20-5..8`，端口 `8114-8117`，状态 `Up`，health `unhealthy`。
- GPU 3:
  - `voxcpm-api-h20-9..11`，端口 `8118-8120`，状态 `Up`，health `unhealthy`。
- GPU 4:
  - 显存约 `1 MiB`，未看到我们的运行中 Docker 进程。

GPU 显存复查:

```text
gpu=1 util=0 mem=26858/97871MiB
gpu=2 util=0 mem=26858/97871MiB
gpu=3 util=0 mem=20145/97871MiB
gpu=4 util=0 mem=1/97871MiB
```

### 模型池风险

服务重启后，调度日志中 `generate_video_and_callback` 正常触发，但模型健康检查显示多项失败，例如:

- `config_id=17` VoxCPM `8129/health` 连接失败，HeyGem `6005/easy/query` 连接失败。
- `config_id=18` VoxCPM `8122/health` 连接失败，HeyGem `6006/easy/query` 连接失败。
- `config_id=19` VoxCPM `8130/health` 连接失败，HeyGem `6007/easy/query` 连接失败。
- `config_id=20` VoxCPM `8120/health` connection reset，HeyGem `6004/easy/query` 连接失败。
- 调度日志出现“无健康可用配置”，本轮未处理待生成任务。

判断:

- Bot 服务已重启并健康。
- 模型池/Docker 端口健康仍不完整，需要另行恢复或调整模型配置。

## 相关文件

- Git 分支: `origin/feature/ai_v6.3.1_video_new`, `origin/test`, `origin/master`
- H20 release: `/data/project/test_ai_botserver.20260616093915`
- H20 app: `app_server_api.py --env=dev --jobStatus=false --port=8100`
- H20 API supervisor: `ai_botserver` / port `8017`
- H20 scheduler supervisor: `ai_botserver_sch` / port `18017`
- 调度日志: `/data/project/test_ai_botserver/logs/run.log`

## 相关记录

- [[projects/joyingbot-new/docs/2026-06-15_prod_voice_clone_release_db_ops|正式服音色克隆上线表变更与接口记录]]
- [[projects/joyingbot-new/docs/2026-06-12_3090_test_server_runbook|3090 测试服运行手册]]
- [[projects/joyingbot-new/docs/2026-06-11_voxcpm_noise_fix_deploy_runbook|VoxCPM 试听噪音修复部署 Runbook]]

## 2026-06-16 GPU5/6/7 线上唇形容器误停与恢复

### 事故与恢复

- 线上唇形容器 `duix-avatar-gen-video-1..6` 原本是约 3 天前启动、运行在 GPU5/6/7 上的线上服务。
- 2026-06-16 中午排查 1/2/3/4 测试环境时，这批线上容器被误停，状态曾为 `Exited (137)`。
- 已在 H20 上只恢复精确匹配的线上容器 `duix-avatar-gen-video-1..6`，未再操作测试容器。
- 恢复后状态：全部 `Up`。
- 端口映射：`8103..8108 -> 8383/tcp`。
- GPU 绑定：`duix-avatar-gen-video-1/2` 使用 GPU7，`duix-avatar-gen-video-3/4` 使用 GPU6，`duix-avatar-gen-video-5/6` 使用 GPU5。
- 启动日志出现 `TransDhServer服务启动` 与 `av_transfer load success`，GPU5/6/7 均恢复 Python 进程与显存占用。

### 长期操作红线

- GPU5/6/7 视为线上/保留服务区域，默认不做任何 stop/start/restart/rm/update 操作。
- 用户只要求处理 GPU1/2/3/4 测试环境时，不得顺带操作 GPU5/6/7 的 Docker 容器、GPU 进程或数据库配置。
- 任何涉及 GPU5/6/7 的动作必须先明确列出容器名、GPU 绑定、端口、影响范围，并获得用户单独确认。
- H20 Docker 操作前必须先只读核对：`docker ps -a`、`docker inspect` GPU 绑定、`nvidia-smi pmon -i <gpu>`，再决定是否执行。
