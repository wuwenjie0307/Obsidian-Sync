---
date: "2026-06-30"
project: "joying-bot-server"
type: bug
status: mitigated
severity: high
tags: [bug, prod, hyperframes, scheduler, docker, crm-callback, stale-timeout]
aliases: ["正式服 Hyperframes hf-docker / Chrome cache / stale 误杀"]
---

# 正式服 Hyperframes hf-docker / Chrome cache / stale 误杀

## 问题描述

正式服网感视频链路在修复 `WHISPER_SERVER_URL` 后继续暴露三类运行时问题：

1. 部分任务失败为 `HYPERFRAMES_CLI_FAILED: [Errno 8] Exec format error: '/data/script/hf-docker'`。
2. Hyperframes 容器首次运行时下载 `chrome-headless-shell`，渲染耗时被明显拉长。
3. 长渲染任务已产出 `hf_result_path` / `hf_final_video_url` 前后，被通用 `VIDEO_PROCESSING_STALE_TIMEOUT` 保护误标失败，并把 CRM 状态回调成 `-1`。

## 影响任务

- `task_id=17632 / 17635`：历史失败原因为 `hf-docker` 无 shebang。
- `task_id=17636 / 17638 / 17639 / 17640`：本地已有最终视频后，被 stale 保护或 CRM 失败回调影响，已手动修正 DB 并补发 CRM 成功回调。
- `task_id=17642 / 17643 / 17645`：修复后已成功回写正式库。
- `task_id=17644`：2026-06-30 01:53 CST 仍在 Hyperframes 渲染中，暂不重启 scheduler。

## 根因

1. `/data/script/hf-docker` 是文本脚本但缺少 `#!/bin/sh`，Python `subprocess` 直接执行时触发 `Exec format error`。
2. Hyperframes Docker 镜像内没有预置 Chrome；每个新容器默认写入自己的 `/root/.cache/hyperframes/chrome`，导致首次下载耗时且不可复用。
3. `scheduler/collect_scheduler.py::_recover_stale_video_processing_tasks` 的通用保护只看：
   - `task_status == 2`
   - `updated_time < now - 35min`
   - `generate_video_url` 为空

   但 Hyperframes 路由在渲染期间本来就还没有 `generate_video_url`，并且可能已经有 `hf_result_path` 或正在 Docker 渲染。该保护没有排除 `templates_style_id=1/2`，会把长渲染误判为卡死。

## 线上处理

1. 修复 `/data/script/hf-docker`：
   - 增加 `#!/bin/sh`
   - 保留 `sudo -n /usr/bin/docker "$@"`
   - 验证 `sudo -u joying /data/script/hf-docker --version` 正常。
2. 为未来 Hyperframes 容器注入共享 Chrome cache：
   - wrapper 对 `docker run` 增加挂载：
     `/data/project/hyperframes-chrome-cache:/root/.cache/hyperframes/chrome`
   - 从已成功容器复制完整 Chrome cache 到宿主机共享目录。
   - 新容器执行 `hyperframes browser path` 时直接命中共享 cache，不再重新下载。
3. 修正已被误标失败的正式库记录：
   - `17636 / 17638 / 17639 / 17640` 本地 DB 回到成功态。
   - `17638 / 17639 / 17640` CRM 从 `task_status=-1` 补发成功回调到 `task_status=7`。
4. 代码补丁：
   - 本地功能分支已修改 `scheduler/collect_scheduler.py`，通用 stale recover 排除 Hyperframes 风格 `templates_style_id=1/2`。
   - 同步热补丁到正式发布目录：
     `/data/project/prod_ai_botserver.20260629201403/scheduler/collect_scheduler.py`
   - 正式服备份：
     `/data/project/prod_ai_botserver.20260629201403/scheduler/collect_scheduler.py.bak_stale_hyperframes_20260630015114`
   - 因 2026-06-30 01:53 CST 仍有活跃渲染容器，暂未重启 scheduler 加载补丁。

## 验证

- 本地测试：
  - `python -m pytest test/test_video_model_busy_retry.py -q`：通过。
  - `python -m pytest test/test_template_route.py test/test_video_model_busy_retry.py -q`：通过，`33 passed`。
- 正式服验证：
  - `hf-docker --version` 可执行。
  - 新 Hyperframes 容器挂载共享 Chrome cache。
  - `17642 / 17643 / 17645` 已成功生成并回写。
  - `17638 / 17639 / 17640` CRM 已由失败态补回成功态。

## 后续

1. 等正式服活跃视频任务清空后，重启 `ai_botserver_sch` 加载 stale recover 补丁。
2. 重启后再次确认：
   - `VIDEO_PROCESSING_STALE_TIMEOUT` 不再作用于 `templates_style_id=1/2`。
   - 极简旧链路 `templates_style_id=3` 的通用 stale 保护仍生效。
3. 将本地功能分支补丁提交并推送，避免下次 Jenkins 部署覆盖线上热补丁。

## 相关文件

- `scheduler/collect_scheduler.py`
- `router/service/video_server2/template_route.py`
- `/data/script/hf-docker`

## 相关记录

- [[projects/joying-bot-server/bugs/prod-hyperframes-route-disabled-env-missing-2026-06-30|正式服 HYPERFRAMES_ROUTE_DISABLED]]
- [[projects/joying-bot-server/bugs/prod-whisper-server-url-missing-2026-06-30|正式服 HEYGEM_STANDARDIZE_FAILED]]
- [[projects/joying-bot-server/docs/prod-hyperframes-docker-runner-mount-check-2026-06-29|正式服 Hyperframes Docker runner mount check]]
