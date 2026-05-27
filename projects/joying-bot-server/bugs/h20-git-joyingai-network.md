---
date: 2026-05-27
status: open
severity: medium
tags: [bug, network, deploy]
---

# h20 无法访问 git.joyingai.cn

## 问题描述

h20 服务器无法连接公司 GitLab `git.joyingai.cn`：

```bash
# DNS 解析失败
$ nslookup git.joyingai.cn
Server: 223.6.6.6
** server can't find git.joyingai.cn: NXDOMAIN

# SSH 连接超时
$ ssh -T git@git.joyingai.cn
ssh: connect to host git.joyingai.cn port 22: Connection timed out

# HTTPS 也不通
$ curl -s --connect-timeout 5 https://git.joyingai.cn
HTTPS FAIL
```

## 原因

`git.joyingai.cn` 是公司内网域名，公网 DNS（223.6.6.6 阿里公共 DNS）无法解析。h20 不在公司内网，无法访问内网服务。

## 解决方案（当前）

通过跳板机中转代码：
1. **上传**：本地 Windows → SCP → 222.71.55.27 → SCP → h20
2. **推送**：在本地 Windows clone 代码 + push（不在 h20 上 push）

## 优化点

- 找程伟/晋良获取 `git.joyingai.cn` 的内网 IP，加到 h20 `/etc/hosts`
