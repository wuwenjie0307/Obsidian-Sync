---
date: "2026-05-29"
tags: [changelog, h20, crm, deploy, correction]
---

# h20 Bot 端口恢复为 8018

## 改动类型

- [ ] 新功能
- [x] Bug 修复
- [ ] 重构
- [x] 配置变更

## 背景

后续聊天记录中，张晋良确认：`你项目启动的端口不用改`。因此前一版“让 Bot 直接监听公网可访问端口 48100”的方案需要修正。

最新口径：

- Bot 项目内部启动端口保持 `8018`。
- 公网端口 `48100/48101` 只作为外部入口或上游 NAT 映射端口处理，不写进项目启动端口。
- CRM 需要访问 Bot `/crm/*` 接口时，应由上游把某个公网端口映射到 h20 内部 `172.16.220.119:8018`。
- VoxCPM/LatentSync 仍由 Bot 在 h20 本机通过 `127.0.0.1:8100/8101` 调用。

## 改动内容

- 本地 `config/config-dev.json` 已将 `server_port` 恢复为 `8018`。
- 本地 `config/config-dev.json` 保留 h20 模型服务内部地址：
  - `h20_api_base`: `http://127.0.0.1:8100`
  - `voxcpm_api_base`: `http://127.0.0.1:8100`
  - `latentsync_api_base`: `http://127.0.0.1:8101`
- 本地 README 已修正为：Bot 内部监听 `8018`，公网端口由上游映射到 h20 内部 `8018`。
- h20 远端配置已备份为：`/data/projects/joyingbot-new/config/config-dev.json.bak.20260529125312`。
- h20 远端 `config-dev.json` 已恢复：
  - `server_port = 8018`
  - `mysql_connection_ip = 222.71.55.27` 保持服务器原配置
  - 三个模型 API base URL 保持 `127.0.0.1:8100/8101`
- h20 root 下 dev Bot 已从 `48100` 停止并重启为：
  - `python app_server_api.py --env dev --jobStatus false --port 8018`

## 验证结果

- h20 本机 `http://127.0.0.1:8018/status/check` 返回 `HTTP 200`，响应 `{"status":"ok"}`。
- h20 当前监听：
  - Bot: `0.0.0.0:8018`
  - VoxCPM: `0.0.0.0:8100`
  - LatentSync: `0.0.0.0:8101`
- 之前 root 下 `48100` Bot 进程已停止。

## 当前仍需外部确认

- 需要晋良或运营商确认公网端口到底映射到 h20 哪个内部端口。
- 如果 CRM 用 `223.112.222.90:48100`，则应该确认它是否转发到 h20 内部 `172.16.220.119:8018`。
- 不要再把 `48100/48101` 当作项目启动端口。

## 影响范围

- CRM 测试服 Bot base URL 仍取决于公网映射结果，例如 `http://223.112.222.90:<公网映射端口>`。
- h20 项目启动命令应保持 `--port 8018`。
- 模型服务端口保持 `8100/8101`，不暴露给 CRM 直接调用。

## 相关文件

- `C:\Users\admin\Desktop\joyingbot-new\config\config-dev.json`
- `C:\Users\admin\Desktop\joyingbot-new\README.md`
- `/data/projects/joyingbot-new/config/config-dev.json`
- `/data/projects/joyingbot-new/config/config-dev.json.bak.20260529125312`

## 相关 Commit

- 未提交，本地工作区改动：`AGENTS.md`、`README.md`、`config/config-dev.json`
## 2026-05-29 端口语义补充

张晋良前序信息：`223.112.222.90:48100`、`223.112.222.90:48101`，`通过这俩端口可以访问了`。结合后续 `项目启动的端口不用改`，当前更合理的解释是：公网端口是网络层入口，项目内部端口仍保持 `8018`。

仍需确认：

- `48100/48101` 分别映射到 h20 内部哪个端口。
- 如果某个公网端口映射到 `172.16.220.119:8018`，CRM Bot base URL 就用这个公网端口。
- 如果 `48100/48101` 实际映射到 `8100/8101`，那它们只能访问 VoxCPM/LatentSync 模型 API，CRM `/crm/*` 仍不能用，需要另一个公网端口映射到 `8018`。
- 判断方式：访问 `http://223.112.222.90:<port>/status/check`，返回 `{"status":"ok"}` 才是 Bot；访问 `/health` 返回 ok 更可能是模型 API。
## 2026-05-29 48100 映射确认

张晋良进一步回复：`他是把你的端口映射到 48100 了`。当前解释：公网 `223.112.222.90:48100` 应该映射到 h20 Bot 内部端口 `172.16.220.119:8018`，项目启动端口仍保持 `8018`。

本地外部验证结果：

```bash
curl http://223.112.222.90:48100/status/check
curl -X POST http://223.112.222.90:48100/crm/voice_clone_audition -H "Content-Type: application/json" -d "{}"
```

从当前本机网络执行仍为 TCP timeout，`HTTP:000`。可能原因：公网映射仅放行 CRM 测试服或指定来源 IP，或映射尚未对当前网络生效。下一步应让 CRM 测试服机器执行 `/status/check` 验证，或让晋良确认是否存在来源 IP 白名单。

CRM 侧如果能访问，Bot base URL 应使用：`http://223.112.222.90:48100`。
## 2026-05-29 最终端口映射修正

张晋良最新明确：`内部端口 8100、8101，对应的外部端口是 48100、48101`，并补充 `在 h20 内部使用 8100、A800 那机器使用 48100 调用`。

因此前面“48100 映射到 Bot 8018”的理解不成立。最终结论：

- `223.112.222.90:48100` -> h20 内部 `8100`，VoxCPM 模型 API。
- `223.112.222.90:48101` -> h20 内部 `8101`，LatentSync 模型 API。
- Bot `/crm/*` 内部仍是 `8018`，目前没有确认公网映射。
- CRM 如果要直接访问 Bot，需要再申请一个公网端口映射到 `172.16.220.119:8018`。