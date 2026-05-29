---
date: "2026-05-29"
status: fixed
severity: medium
tags: [bug, h20, config, mysql]
---

# h20 config-dev 整文件覆盖导致 MySQL 地址错误

## 问题描述

部署 h20 CRM Bot 端口配置时，第一次把本地 `config/config-dev.json` 整文件上传覆盖到 h20，导致 h20 Bot 启动失败。

## 原因

本地 `config-dev.json` 和 h20 服务器实际运行配置不完全一致。h20 原配置中的 `mysql_connection_ip` 是 `222.71.55.27`，本地文件中是 `127.0.0.1`。整文件覆盖后，Bot 初始化时连接 `127.0.0.1:3306`，而 h20 本机没有 MySQL，导致启动失败。

错误日志关键点：

```text
pymysql.err.OperationalError: (2003, "Can't connect to MySQL server on '127.0.0.1' ([Errno 111] Connection refused)")
```

## 复现步骤

1. 用本地 `config/config-dev.json` 整文件覆盖 h20 `/data/projects/joyingbot-new/config/config-dev.json`。
2. 启动 Bot：`python app_server_api.py --env dev --jobStatus false --port 48100`。
3. Bot 初始化 `agent.pprice` 时尝试连接 MySQL。
4. 连接 `127.0.0.1:3306` 失败，服务无法监听端口。

## 期望行为

h20 Bot 使用 h20 原有数据库配置连接 `222.71.55.27:3306`，同时只变更 CRM 端口和模型 API 内部地址。

## 实际行为

Bot 使用被覆盖后的 `127.0.0.1:3306`，启动失败。

## 环境信息

- 分支: `feature/ai_v1_api_merge`
- 本地仓库: `C:\Users\admin\Desktop\joyingbot-new`
- h20 项目路径: `/data/projects/joyingbot-new/`
- h20 主机名: `hgx19`
- h20 内网 IP: `172.16.220.119`
- h20 服务用户: `root`
- h20 conda env: `joyingbot`

## 修复方案

- 使用首次部署前自动备份恢复 h20 专用配置基底：`config/config-dev.json.bak.20260529114339`。
- 只对远端配置打补丁：
  - `server_port = 48100`
  - `h20_api_base = http://127.0.0.1:8100`
  - `voxcpm_api_base = http://127.0.0.1:8100`
  - `latentsync_api_base = http://127.0.0.1:8101`
- 保留 h20 原来的 `mysql_connection_ip = 222.71.55.27`。
- 在 README 中补充提醒：h20 服务器上的 `config-dev.json` 包含服务器专用 DB/Redis 等地址，不要直接用本地配置整文件覆盖。

## 验证结果

- 修复后 h20 Bot 启动成功并监听 `0.0.0.0:48100`。
- `curl http://127.0.0.1:48100/status/check` 返回 `HTTP 200`。
- `/crm/voice_clone_audition` 空 JSON 返回预期 `HTTP 400`，说明 CRM 路由已加载。
- 日志显示 MySQL pool 初始化目标为 `222.71.55.27:3306`。

## 优化点

- 后续部署配置优先用“远端备份 + 字段级补丁”，不要直接覆盖环境配置文件。
- 可以考虑把环境差异字段拆到单独的 server-local 配置或环境变量，降低误覆盖风险。

## 相关文件

- `C:\Users\admin\Desktop\joyingbot-new\config\config-dev.json`
- `C:\Users\admin\Desktop\joyingbot-new\README.md`
- `/data/projects/joyingbot-new/config/config-dev.json`
- `/data/projects/joyingbot-new/config/config-dev.json.bak.20260529114339`