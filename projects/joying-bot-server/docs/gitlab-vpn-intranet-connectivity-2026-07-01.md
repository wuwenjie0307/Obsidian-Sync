---
date: "2026-07-01"
project: joying-bot-server
type: doc
tags: [doc, gitlab, vpn, intranet, troubleshooting]
aliases: ["GitLab VPN 内网访问差异记录"]
---

# GitLab VPN 内网访问差异记录

## 现象

用户电脑同时连接 VPN 节点和公司内网时，浏览器打不开 GitLab；关闭 VPN 后再开公司内网可以打开。

同一环境下，PowerShell 和 Git 命令可以访问 GitLab。

## 本次证据

`Test-NetConnection git.joyingai.cn -Port 443` 结果：

```text
RemoteAddress    : 172.30.3.157
RemotePort       : 443
InterfaceAlias   : 以太网 2
SourceAddress    : 10.8.0.238
TcpTestSucceeded : True
```

`git ls-remote https://git.joyingai.cn/services/crm.ai.joyingbot.git HEAD` 返回：

```text
356bf16223b41eab3f0d37c0e8392455160863e7        HEAD
```

说明命令行侧可以把 `git.joyingai.cn` 解析到内网 IP，并通过 `以太网 2` 成功访问 GitLab HTTPS。

## 判断

这不是 GitLab 或 Git HTTPS 整体不通。更像是浏览器层代理、DNS 缓存、VPN 插件、SSO 页面资源或路由策略被 VPN 干扰。

Git 命令和浏览器可能走不同的 DNS、代理或路由策略。因此浏览器打不开，不代表 `git fetch` / `git push` 一定不通；反过来也一样。

## 快速验证

```powershell
Test-NetConnection git.joyingai.cn -Port 443
git ls-remote https://git.joyingai.cn/services/crm.ai.joyingbot.git HEAD
```

如果命令行通但浏览器不通，优先排查浏览器代理、VPN 插件、DNS 缓存，并尝试无痕窗口或另一浏览器。

可先执行：

```powershell
ipconfig /flushdns
```

## 图谱链接

- 项目: [[projects/joying-bot-server/00-项目概览|joying-bot-server]]
- 索引: [[projects/joying-bot-server/docs/00-docs-index|参考文档索引]]
