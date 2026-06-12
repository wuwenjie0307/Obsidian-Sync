---
date: "2026-06-12"
project: joyingbot-new
type: doc
tags: [doc, runbook, test-server, 3090, supervisor, deployment]
aliases: ["3090 测试服运行手册", "3090 test server runbook"]
---

# 3090 测试服运行手册

## 图谱链接

- 项目: [[projects/joyingbot-new/00-项目概览|joyingbot-new]]
- 索引: [[projects/joyingbot-new/docs/00-docs-index|参考文档索引]]

## 背景

2026-06-12 确认测试服已迁到一台本地 3090 机器，用户在 Windows PowerShell 中通过 `wsl` 进入 Linux 环境操作。旧 H20 路径 `/data/project/test_ai_botserver` 在新机器不存在，新测试服实际运行在 `/data/project/crm.ai.joyingbot`。

本记录作为新的测试服运维分支入口，记录服务位置、如何确认是否为最新 `test` 分支代码、如何查看日志、如何重启服务，以及 2026-06-12 10:20 任务排查线索。

## 结论

- 代码目录: `/data/project/crm.ai.joyingbot`
- 当前服务进程由 `supervisor` 管理。
- `ai_botserver` 运行接口服务，端口参数为 `--port=8017`。
- `ai_botserver_sch` 运行调度服务，端口参数为 `--port=18017`。
- 2026-06-12 已确认本机 `test` 分支与 GitLab `origin/test` 一致:
  - commit: `81374ebe`
  - commit message: `Merge branch 'phone_activate_bug' into test`
  - commit time: `2026-06-12 09:18:18 +0800`
  - `git rev-list --left-right --count HEAD...origin/test` 输出 `0 0`
- 已重启服务加载该版本:
  - `ai_botserver` 新 PID: `282083`
  - `ai_botserver_sch` 新 PID: `282084`

## 登录与基础操作

在 Windows PowerShell 中进入 WSL:

```powershell
wsl
```

进入项目目录:

```bash
cd /data/project/crm.ai.joyingbot
```

查看机器上的项目目录:

```bash
ls -lah /data
ls -lah /data/project
```

已观察到的新机器目录包括:

```text
/data/project/crm.ai.admin
/data/project/crm.ai.joyingbot
/data/project/video_server_model_overseas
/data/server_logs
```

## Supervisor 服务

查看服务状态:

```bash
sudo supervisorctl status
```

已观察到的服务:

```text
ai_admin
ai_botserver
ai_botserver_sch
```

查看指定服务 PID:

```bash
sudo supervisorctl pid ai_botserver
sudo supervisorctl pid ai_botserver_sch
```

确认服务实际运行目录:

```bash
sudo readlink -f /proc/$(sudo supervisorctl pid ai_botserver)/cwd
sudo readlink -f /proc/$(sudo supervisorctl pid ai_botserver_sch)/cwd
```

期望输出:

```text
/data/project/crm.ai.joyingbot
/data/project/crm.ai.joyingbot
```

查看启动命令:

```bash
sudo tr '\0' ' ' < /proc/$(sudo supervisorctl pid ai_botserver)/cmdline; echo
sudo tr '\0' ' ' < /proc/$(sudo supervisorctl pid ai_botserver_sch)/cmdline; echo
```

已观察到的启动命令:

```text
/data/server/anaconda3/envs/botserver/bin/python app_server_api.py --env=dev --jobStatus=false --port=8017
/data/server/anaconda3/envs/botserver/bin/python app_server_sch.py --env=dev --jobStatus=true --port=18017
```

查看进程启动时间:

```bash
ps -p $(sudo supervisorctl pid ai_botserver) -o pid,lstart,cmd
ps -p $(sudo supervisorctl pid ai_botserver_sch) -o pid,lstart,cmd
```

## 判断是否为最新 test 分支代码

进入项目目录:

```bash
cd /data/project/crm.ai.joyingbot
```

查看远端、分支和工作区:

```bash
git remote -v
git status -sb
git branch --show-current
```

已观察到远端:

```text
origin git@git.joyingai.cn:services/crm.ai.joyingbot.git
```

拉取最新 `test` 状态:

```bash
git fetch origin test --prune
```

对比本地与远端:

```bash
echo "HEAD:        $(git rev-parse --short HEAD)"
echo "origin/test: $(git rev-parse --short origin/test)"
git log -1 --format='HEAD commit:        %h %ci %s'
git log -1 origin/test --format='origin/test commit: %h %ci %s'
git rev-list --left-right --count HEAD...origin/test
```

判断规则:

```text
0 0 = 本地就是最新 origin/test
0 N = 本地落后 origin/test，需要拉代码
N 0 = 本地有远端 test 没有的提交
N M = 本地和 origin/test 分叉
```

如果 `git fetch` 报错 `Could not resolve hostname git.joyingai.cn`，说明当前机器 DNS 或网络不能访问 GitLab。此时只能证明本机代码等于上一次成功拉取到的 `origin/test`，不能证明等于 GitLab 当前最新 `test`。

网络恢复后重新执行:

```bash
git fetch origin test --prune
git rev-list --left-right --count HEAD...origin/test
```

## 更新代码并重启服务

如果本地落后远端，并且没有需要保留的本地改动，更新:

```bash
cd /data/project/crm.ai.joyingbot
git pull --ff-only origin test
```

重启接口服务和调度服务:

```bash
sudo supervisorctl restart ai_botserver ai_botserver_sch
sudo supervisorctl status
```

重启后再次确认运行目录:

```bash
sudo readlink -f /proc/$(sudo supervisorctl pid ai_botserver)/cwd
sudo readlink -f /proc/$(sudo supervisorctl pid ai_botserver_sch)/cwd
```

注意: 仅确认 Git 目录最新还不够，还需要确认正在运行的进程 `cwd` 指向该目录，并且进程启动时间晚于代码更新/拉取时间。

## 查看日志

主日志目录:

```bash
/data/server_logs/supervisord
```

查看日志文件:

```bash
cd /data/server_logs/supervisord
ls -lh
```

实时查看接口服务日志:

```bash
tail -n 200 -f /data/server_logs/supervisord/ai_botserver.out
```

按时间查日志。示例: 查 2026-06-12 10:20 附近:

```bash
grep -RniC 80 "2026-06-12.*10:20" /data/server_logs/supervisord
grep -RniC 80 "10:20:" /data/server_logs/supervisord
```

按任务查日志。示例: 查 `job_id=1216` / `task_id=1190`:

```bash
grep -RniC 80 "job_id=1216\|task_id=1190\|1190\|1216" /data/server_logs/supervisord
grep -Rni "job_id=1216\|task_id=1190\|1190\|1216" /data/server_logs/supervisord | tail -n 300
```

查错误:

```bash
grep -RniC 80 "error\|exception\|traceback\|failed\|失败" /data/server_logs/supervisord
```

## 2026-06-12 10:20 任务排查记录

已从日志看到 10:20 的任务进入接口链路:

```text
job_id=1216
task_id=1190
templates_style_id=2
```

关键时间线:

```text
10:20:33 /crm/rewrite_video_desc 200
10:20:40 拉取 CRM 工作组 job_id=1216
10:20:41 拉取素材任务 task_id=1190
10:20:42 同步数据完成并提交数据库 tasks=1
10:20:42 /crm/generate_video_task 200
10:20:42 异步处理开始 job_id=1216 task_id=1190
10:20:42 materialSubtitleCallback 回调成功 resp_code=200
10:20:42 异步处理结束 cost_ms=190
```

这证明接口侧任务同步、数据写入和字幕回调成功。若要确认视频是否真正生成完成，需要继续查调度进程 `ai_botserver_sch` 是否捞到并处理 `task_id=1190`。

相关素材字段:

```text
imagery_video=https://files.joyingai.cn/crm/20260605/user4_1780637795609_4832260309e54bcb.mp4
cover_image_url=https://videos-test.joyingai.cn/video/crm/20260612/user4_1781230829124_a2a09c11fb1eca03.png
hot_video_audio_url=https://videos.joyingai.cn/video/crm/bgm/调频/舒缓-Sunrise-new.mp3
```

同时看到一条看似无关的外部 CRM 超时:

```text
10:21:29 /crm/open_wechat_accounts 500
crm2.yunkecn.com/open/wechat/accounts connect timeout
10:25:28 之后 /crm/open_wechat_accounts 连续返回 200
```

初步判断该错误更像外部 CRM 网络短暂超时，不是 10:20 视频生成任务主链路。

## 常用一键检查脚本

```bash
cd /data/project/crm.ai.joyingbot || exit 1

echo "== Git =="
git fetch origin test --prune
echo "branch: $(git branch --show-current)"
echo "HEAD:        $(git rev-parse --short HEAD)"
echo "origin/test: $(git rev-parse --short origin/test)"
git log -1 --format='%h %ci %s'
git rev-list --left-right --count HEAD...origin/test

echo
echo "== Supervisor =="
sudo supervisorctl status

echo
echo "== Runtime =="
for svc in ai_botserver ai_botserver_sch; do
  pid=$(sudo supervisorctl pid "$svc")
  echo "$svc pid=$pid"
  sudo readlink -f "/proc/$pid/cwd"
  sudo tr '\0' ' ' < "/proc/$pid/cmdline"; echo
  ps -p "$pid" -o pid,lstart,cmd
  echo
done
```

## 相关记录

- 2026-06-12 会话中确认新 3090 测试服路径与运行态。
- 旧 H20 路径 `/data/project/test_ai_botserver` 不适用于这台新机器。
