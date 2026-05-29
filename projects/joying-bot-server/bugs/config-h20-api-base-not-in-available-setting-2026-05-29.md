---
date: "2026-05-29"
status: fixed
severity: high
tags: [bug, config, test, h20, botserver]
---

# h20_api_base 不在 available_setting 导致 botserver 启动失败

## 问题描述

测试服 botserver 启动时报错：

```text
Exception: key h20_api_base not in available_setting
```

报错路径：

```text
/data/project/test_ai_botserver.20260529155139/app_config/config.py
```

h20 项目日志路径：

```text
/data/server_logs/supervisord/ai_botserver.out
```

## 原因

`origin/test` 之前只合入了 h20 端口方案的配置和文档：

- `config/config-dev.json` 增加了 `h20_api_base`
- `config/config-dev.json` 增加了 `voxcpm_api_base`
- `config/config-dev.json` 增加了 `latentsync_api_base`

但 `test` 分支当时没有合入新模型集成代码，导致：

- `app_config/config.py` 的 `available_setting` 缺少上述三个 key
- VoxCPM / LatentSync API 和客户端代码也没有进入 `test`

因此服务在加载配置阶段直接失败，还没进入业务代码。

## 解决方案

已把新模型集成分支内容合入当前 `test`，包含：

- `app_config/config.py` 增加 `h20_api_base`、`voxcpm_api_base`、`latentsync_api_base`
- `router/crm_server.py` 中音色试听接口相关逻辑
- `router/service/video_server/voxcpm_api.py`
- `router/service/video_server/voxcpm_tts.py`
- `router/service/video_server/latentsync_api.py`
- `router/service/video_server/latentsync_service.py`
- `router/service/video_server2/*` 对应客户端改动
- LatentSync Docker 部署文档与脚本

修复提交：

```text
9c03efbd merge: bring video model integration into test
```

已推送到远端：

```text
origin/test
```

## 验证

本地验证通过：

```powershell
python -m json.tool config/config-dev.json > $null
```

配置白名单加载验证通过：

```text
config ok
```

确认 `available_setting` 已包含：

```text
h20_api_base
voxcpm_api_base
latentsync_api_base
```

确认 `HEAD` 不包含 `AGENTS.md`。

## 优化点

后续如果向配置文件新增 key，必须同步修改：

```text
app_config/config.py -> available_setting
```

同时不能只合配置文件，必须确认对应业务代码、客户端代码和服务文件一起进入目标分支。

## 2026-05-29 16:08 h20 日志复查

已通过 h20 日志确认：

```text
/data/server_logs/supervisord/ai_botserver.out
```

结论：

- 16:01 之前日志中持续出现 `Exception: key h20_api_base not in available_setting`。
- 16:01:54 后配置加载成功，`h20_api_base`、`voxcpm_api_base`、`latentsync_api_base` 均已进入运行配置。
- supervisor 管理的 `ai_botserver` 当前监听 `8017`，`/status/check` 返回 `{"status":"ok"}`。
- h20 手动部署的 Bot 仍监听 `8100`，`/status/check` 返回 `{"status":"ok"}`。
- VoxCPM `8110` 和 LatentSync `8101` 健康检查均返回 `{"status":"ok"}`。

当前运行端口：

| 服务 | 端口 | 状态 |
|---|---:|---|
| supervisor ai_botserver | 8017 | ok |
| h20 CRM Bot 公网映射入口对应服务 | 8100 | ok |
| VoxCPM | 8110 | ok |
| LatentSync | 8101 | ok |

注意：日志会打印完整配置，其中包含敏感字段。后续应考虑避免在 INFO/DEBUG 日志中输出完整配置，或对密码、token、key 做脱敏。

## ai_botserver 服务说明

h20 上 supervisor 管理的 `ai_botserver` 是测试 Bot API 服务，不是 VoxCPM/LatentSync 模型服务。

当前确认：

```text
supervisor program: ai_botserver
cwd: /data/project/test_ai_botserver.20260529160246
symlink: /data/project/test_ai_botserver -> /data/project/test_ai_botserver.20260529160246
command: app_server_api.py --env=dev --jobStatus=false --port=8017
health: http://127.0.0.1:8017/status/check -> ok
log: /data/server_logs/supervisord/ai_botserver.out
```

同机还存在手动启动的 h20 CRM Bot：

```text
cwd: /data/projects/joyingbot-new
command: app_server_api.py --env dev --jobStatus false --port 8100
health: http://127.0.0.1:8100/status/check -> ok
```

当前端口关系：

| 服务 | 端口 | 说明 |
|---|---:|---|
| supervisor `ai_botserver` | 8017 | 自动部署的测试 Bot API 服务 |
| 手动 h20 CRM Bot | 8100 | 当前 `223.112.222.90:48100` 对应的外部联调入口 |
| VoxCPM API | 8110 | Bot 本机调用 |
| LatentSync API | 8101 | Bot 本机调用 |

注意：当前 h20 同时存在两个 `app_server_api.py` Bot 进程，联调时要明确使用哪个入口。
