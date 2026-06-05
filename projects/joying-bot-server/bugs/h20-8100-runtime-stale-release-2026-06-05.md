---
date: "2026-06-05"
status: fixed
severity: high
tags: [bug, h20, runtime, deploy]
---

# h20-8100-runtime-stale-release-2026-06-05

## 问题描述

H20 测试服务检查时发现 `/data/project/test_ai_botserver` 已指向当前发布目录 `/data/project/test_ai_botserver.20260605120425`，但 8100 端口仍由旧进程提供服务。

- 旧 8100 PID: `3634774`
- 旧进程启动时间: `Fri Jun 5 10:54:20 2026`
- 旧进程 cwd: `/data/project/test_ai_botserver.20260605105110`
- 当前发布软链: `/data/project/test_ai_botserver -> /data/project/test_ai_botserver.20260605120425`
- 当前发布目录关键文件 mtime: `2026-06-05 11:57:39 +0800`

8017 和 18017 已经运行在当前发布目录：

- 8017 PID: `3742389`, cwd `/data/project/test_ai_botserver.20260605120425`
- 18017 PID: `3742390`, cwd `/data/project/test_ai_botserver.20260605120425`

## 复现步骤

1. 登录 H20: 跳板机 `developer@222.71.55.27:9527` 后进入 `root@h20:10019`。
2. 查看当前发布软链: `readlink -f /data/project/test_ai_botserver`。
3. 查看相关进程: `ps -eo pid,ppid,lstart,cmd | grep -E "8100|8017|18017|test_ai_botserver"`。
4. 对 8100 PID 检查 cwd: `readlink -f /proc/<pid>/cwd`。

## 期望行为

8100 / 8017 / 18017 均应运行在当前发布目录 `/data/project/test_ai_botserver.20260605120425`，避免不同端口加载不同版本代码。

## 实际行为

8100 仍运行在旧发布目录 `/data/project/test_ai_botserver.20260605105110`；8017 和 18017 已在当前发布目录。

## 环境信息

- 环境: H20 测试服务
- 主机: `root@hgx19`
- 项目软链: `/data/project/test_ai_botserver`
- 当前发布目录: `/data/project/test_ai_botserver.20260605120425`
- 进程管理: `supervisord` 管理 8017 / 18017；8100 未出现在 `supervisorctl status` 中
- 健康检查: `http://127.0.0.1:8100/status/check`, `http://127.0.0.1:8017/status/check`

## 原因

8100 是独立启动的 `app_server_api.py --env=dev --jobStatus=false --port=8100` 进程，没有随当前发布软链切换自动重启。发布目录切到 `20260605120425` 后，8100 旧进程仍持有旧 cwd，因此继续加载旧代码。

## 修复方案

只针对旧 8100 PID 做精确重启，没有重启 8017 / 18017：

```bash
kill 3634774
cd /data/project/test_ai_botserver
nohup /data/server/anaconda3/envs/botserver/bin/python app_server_api.py --env=dev --jobStatus=false --port=8100 >> logs/run.log 2>&1 &
```

修复后状态：

- 新 8100 PID: `3918518`
- 新进程启动时间: `Fri Jun 5 14:22:59 2026`
- 新进程 cwd: `/data/project/test_ai_botserver.20260605120425`
- 旧目录 `/data/project/test_ai_botserver.20260605105110` 无残留运行进程
- 8100 健康检查返回: `{"status":"ok"}`
- 8017 健康检查返回: `{"status":"ok"}`

## 解决方案

同“修复方案”。后续遇到 H20 服务“代码已部署但行为不变”时，必须同时核对发布软链和 `/proc/<pid>/cwd`，不能只看 Git 或目录文件。

## 优化点

- 给 8100 增加明确的 supervisor 配置，避免手动后台进程长期脱管。
- 部署完成后自动检查 8100 / 8017 / 18017 的 cwd 是否都指向当前发布目录。
- 发布包内增加 commit/version 标记；当前发布目录不是 Git 仓库，无法在 H20 上直接记录 `origin/test` commit hash。
- 在健康检查或状态接口中返回 build/release id，方便远程确认运行版本。

## 相关文件

- `/data/project/test_ai_botserver/app_server_api.py`
- `/data/project/test_ai_botserver/app_server_sch.py`
- `/data/project/test_ai_botserver/router/crm_server.py`
- `/data/project/test_ai_botserver/scheduler/collect_scheduler.py`
- `/data/project/test_ai_botserver/router/service/video_server2/video_task_status.py`
