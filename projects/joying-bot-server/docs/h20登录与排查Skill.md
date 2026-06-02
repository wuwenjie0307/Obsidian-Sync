---
tags: [skill, h20, ssh, deployment, logs]
updated: 2026-06-02
---

# h20 登录与排查 Skill

## Codex 记忆锚点

- 后续只要问题涉及 h20 / hgx19 / `223.112.222.90:48100` / `48101` / h20 Docker / h20 内部模型服务，先读本文件。
- 当前 Codex 本机 `C:/Users/admin/.codex/skills` 未发现已安装的独立 `h20-login`/`h20 登录` Skill；这份 Obsidian 笔记是当前可用的 h20 登录 runbook。
- 不保存、不复述密码；远程只读检查优先使用本次临时环境变量 `H20_JUMP_PASSWORD`。

## 触发条件

当用户的问题涉及以下内容时，先启用这份流程：

- h20 / hgx19 机器状态
- `223.112.222.90:48100` / `48101` 外部访问
- Bot、VoxCPM、LatentSync 服务状态
- `/data/projects/joyingbot-new`
- `/data/project/test_ai_botserver*`
- supervisor / `ai_botserver`
- h20 日志排查
- CRM 联调接口访问不通

## 密码处理原则

不要把密码写入 Obsidian、Git、代码文件、日志或最终回复。

需要登录 h20 时，优先在对话中向用户索要本次临时密码：

```text
需要登录 h20 做只读检查，请提供本次跳板/ sudo 密码；我不会写入文件或最终回复。
```

如果用户希望用环境变量，可以让用户在当前 PowerShell 会话临时设置：

```powershell
$env:H20_JUMP_PASSWORD = "用户本次提供的密码"
```

不推荐持久化保存密码。如果用户明确要求持久化，才使用：

```powershell
[Environment]::SetEnvironmentVariable("H20_JUMP_PASSWORD", "用户本次提供的密码", "User")
```

持久化后需要提醒用户：这会把密码保存在本机用户环境变量中，后续应手动清除：

```powershell
[Environment]::SetEnvironmentVariable("H20_JUMP_PASSWORD", $null, "User")
```

## 连接拓扑

本地不能直接登录 h20，需要先到跳板机：

```text
本地 -> developer@222.71.55.27:9527 -> sudo -> root@h20:10019
```

手动登录流程：

```bash
ssh developer@222.71.55.27 -p 9527
sudo su
ssh root@h20 -p 10019
```

h20 主机名：

```text
hgx19
```

## 常用目录

| 路径 | 说明 |
|---|---|
| `/data/projects/joyingbot-new` | 手动部署的新仓库 Bot，当前 CRM 外部联调使用这套 |
| `/data/project/test_ai_botserver` | supervisor 自动部署的测试 Bot 软链 |
| `/data/project/test_ai_botserver.*` | 自动部署生成的时间戳版本目录 |
| `/data/server_logs/supervisord/ai_botserver.out` | supervisor `ai_botserver` 日志 |
| `/tmp/bot_dev.log` | 手动启动 Bot 常用日志 |
| `/tmp/voxcpm.log` | VoxCPM 常用日志 |
| `/tmp/latentsync.log` | LatentSync 常用日志 |

## 当前端口关系

| 服务 | 端口 | 说明 |
|---|---:|---|
| supervisor `ai_botserver` | 8017 | 自动部署的测试 Bot API 服务 |
| h20 CRM Bot 公网入口 | 8100 | `223.112.222.90:48100` 对应的外部联调入口；2026-05-29 已切到 `/data/project/test_ai_botserver` 当前 Jenkins 部署代码，手动 nohup 运行 |
| VoxCPM API | 8110 | Bot 本机调用 |
| LatentSync API | 8101 | Bot 本机调用 |

注意：h20 当前可能同时存在两个 `app_server_api.py` 进程：

- `8017`：supervisor 管理的 `ai_botserver`，工作目录为 `/data/project/test_ai_botserver`。
- `8100`：公网入口 `48100` 对应的 Bot，2026-05-29 已从旧 `/data/projects/joyingbot-new` 切到 `/data/project/test_ai_botserver` 当前部署代码，但仍是手动 nohup 进程，不归 supervisor 管理。

CRM 外部联调口径以 `48100 -> 8100` 为准；排查时必须确认 8100 进程的 cwd 是 `/data/project/test_ai_botserver.*`，否则可能又跑回旧手动代码。

## 只读检查命令

进入 h20 后，常用只读检查：

```bash
hostname
supervisorctl status | grep -i ai_botserver
ps -ef | grep -E "app_server_api.py|voxcpm_api.py|latentsync_api.py" | grep -v grep
ss -ltnp | grep -E ':8017|:8100|:8101|:8110'
```

健康检查：

```bash
curl -s --max-time 5 http://127.0.0.1:8017/status/check
curl -s --max-time 5 http://127.0.0.1:8100/status/check
curl -s --max-time 5 http://127.0.0.1:8110/health
curl -s --max-time 5 http://127.0.0.1:8101/health
```

查看 supervisor Bot 日志：

```bash
tail -120 /data/server_logs/supervisord/ai_botserver.out
```

查看 8100 公网入口 Bot 日志：

```bash
tail -120 /tmp/bot_8100_test_ai_botserver.log
```

按错误关键字筛日志：

```bash
grep -nE "Traceback|Exception|ERROR|Error|available_setting|h20_api_base|voxcpm_api_base|latentsync_api_base|ModuleNotFoundError|ImportError" \
  /data/server_logs/supervisord/ai_botserver.out | tail -100
```

查看进程工作目录：

```bash
for p in $(pgrep -f 'app_server_api.py'); do
  echo PID=$p
  readlink -f /proc/$p/cwd 2>/dev/null || true
  xargs -0 echo < /proc/$p/cmdline 2>/dev/null || true
done
```

## Paramiko 自动化模板

在 Codex 本地用 Python/Paramiko 做只读检查时，密码从环境变量读取，不要写死到脚本里。

PowerShell 当前会话设置密码：

```powershell
$env:H20_JUMP_PASSWORD = "用户本次提供的密码"
```

Python 模板：

```python
import os
import shlex
import paramiko

password = os.environ.get("H20_JUMP_PASSWORD")
if not password:
    raise RuntimeError("H20_JUMP_PASSWORD is not set; ask the user for the password first.")

remote_script = r"""
hostname
supervisorctl status 2>/dev/null | grep -i ai_botserver || true
ps -ef | grep -E "app_server_api.py|voxcpm_api.py|latentsync_api.py" | grep -v grep || true
ss -ltnp | grep -E ':8017|:8100|:8101|:8110' || true
curl -s --max-time 5 http://127.0.0.1:8017/status/check || true; echo
curl -s --max-time 5 http://127.0.0.1:8100/status/check || true; echo
curl -s --max-time 5 http://127.0.0.1:8110/health || true; echo
curl -s --max-time 5 http://127.0.0.1:8101/health || true; echo
"""

inner = "bash -lc " + shlex.quote(remote_script)
cmd = "sudo -S -p '' ssh -o BatchMode=yes -o StrictHostKeyChecking=no -p 10019 root@h20 " + shlex.quote(inner)

client = paramiko.SSHClient()
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(
    "222.71.55.27",
    port=9527,
    username="developer",
    password=password,
    timeout=20,
    banner_timeout=20,
    auth_timeout=20,
)
stdin, stdout, stderr = client.exec_command(cmd, timeout=90)
stdin.write(password + "\n")
stdin.flush()
out = stdout.read().decode("utf-8", errors="replace")
err = stderr.read().decode("utf-8", errors="replace")
code = stdout.channel.recv_exit_status()
client.close()
print(out)
if err.strip():
    print("=== stderr ===")
    print(err)
print(f"=== exit {code} ===")
```

如果 Windows 控制台因为日志里的特殊字符报编码错误，输出前做替换：

```python
print(text.encode("gbk", errors="replace").decode("gbk"))
```

## 日志安全注意事项

`ai_botserver.out` 当前会打印完整配置，其中可能包含密码、token、key。排查时：

- 不要把完整日志原文贴到最终回复。
- 不要把完整配置写进 Obsidian。
- 汇报时只说字段名、错误类型、端口状态，不复述敏感值。
- 后续应推动代码改造：配置日志输出需要脱敏。

## 写操作安全规则

默认只做只读检查。涉及以下操作时必须先说明并确认：

- 重启 supervisor 服务
- kill 业务进程
- 修改配置文件
- 覆盖部署目录
- 修改端口
- 推送 Git 分支或部署代码

如果必须改 h20 配置，先备份：

```bash
cd /data/projects/joyingbot-new
cp config/config-dev.json config/config-dev.json.bak.$(date +%Y%m%d%H%M%S)
```

远程 `config-dev.json` 包含服务器专用 MySQL、Redis 等配置，不能用本地文件整文件覆盖，只能补丁式修改必要字段。

## 常见判断

### `key h20_api_base not in available_setting`

原因：`config-dev.json` 已有新 key，但 `app_config/config.py -> available_setting` 没同步。

修复方向：把新模型集成代码完整合入目标分支，不能只合配置文件。

### `8017` 与 `8100` 混淆

- `8017`：supervisor 自动部署的 `ai_botserver`
- `8100`：外部 `48100` 指向它；当前应从 `/data/project/test_ai_botserver` Jenkins 部署目录启动

CRM 联调优先使用：

```text
http://223.112.222.90:48100
```

2026-05-29 修正记录：

- 发现 `48100 -> 8100` 仍打到旧目录 `/data/projects/joyingbot-new`，导致外部入口没有新调度代码。
- 已停止旧 8100，并从 `/data/project/test_ai_botserver` 重新启动 8100。
- 当前验证：外部 `GET /status/check` 返回 200；`POST /crm/submit_heygem_whisper_video_task` 返回 410。

### `/crm/voice_clone_audition` 500

如果 botserver 的 `/crm/voice_clone_audition` 返回 500，优先查看：

```text
/data/server_logs/supervisord/ai_botserver.out
```

筛选命令：

```bash
grep -nE "voice_clone_audition|Traceback|Exception|ERROR|Error" /data/server_logs/supervisord/ai_botserver.out | tail -120
```

注意不要把日志里的完整配置、密码、token、key 复制到回复或 Obsidian。

## h20 Docker 状态（2026-05-29）

h20 上 Docker CLI 不在默认 PATH，实际路径：

```bash
/cm/local/apps/docker/current/bin/docker
```

Docker daemon 使用的数据目录：

```text
/data/docker
```

2026-05-29 只读检查结果：

- `docker ps`：没有运行中的容器。
- `docker ps -a`：只有两个历史退出容器。
- 当前 Bot / VoxCPM / LatentSync 链路不是通过 Docker 容器运行。

历史退出容器：

| 容器名 | 镜像 | 状态 |
|---|---|---|
| `comfyui` | `registry.hd-04.alayanew.com:8443/.../comtext/comfyui-0.3.75:1.53` | Exited 4 months ago |
| `vllm_server` | `vllm/vllm-openai:v0.10.0` | Exited 4 months ago |

截图里的镜像当前没有运行中容器使用。若要清理镜像，需先确认没有历史回滚或离线启动需求；不要未经确认执行 `docker rm` / `docker rmi` / `docker system prune`。

## 代码同步原则（2026-06-01 更新）

用户已确认：后续如果只是代码修复需要同步到 h20，优先提交并推送到 GitLab `test` 分支，让 Jenkins/测试部署链路同步。

默认不要手动覆盖 h20 文件；只有用户明确要求“直接同步到 h20/手动部署/临时验证”时，才按上面的跳板机流程做远程写操作。

执行原则：

- 只推 `test`，上线前不推 `master`。
- 提交信息和分支名不要带 Codex/助手名字。
- 推送前必须跑本地验证命令。
- h20 手动写操作前先说明会改哪些目录、是否重启服务，并获得授权。
