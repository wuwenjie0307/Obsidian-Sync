---
date: "2026-05-28"
status: fixed
severity: medium
tags: [bug]
---

# 代理拦截 SSH 导致 Git 推送失败

## 问题描述

Git 推送到 GitHub 时报错 `Connection closed by 198.18.0.11 port 22`，SSH 连接被代理软件拦截断开。

## 复现步骤

1. 开启代理软件（TUN 模式）
2. 执行 `git push` 到 GitHub
3. 报错 `ssh: connect to host github.com port 22: Connection closed by 198.18.0.11 port 22`

## 原因

代理软件的 TUN 模式接管了所有网络流量，SSH 到 GitHub 22 端口的连接被代理服务器 `198.18.0.11` 拦截后关闭。GitHub 不支持通过该代理连接。

## 解决方案

关闭代理软件和 TUN 模式，让 SSH 直连 GitHub。Git push/pull/ssh -T 操作均恢复正常。

## 影响范围

- Obsidian-Git 插件同步失败（同一根因）
- claude-config-sync 推送失败
- 任何通过 SSH 22 端口连接 GitHub 的操作

## 相关文件

- `C:/Users/admin/Desktop/claude-config-sync/`
- `C:/Users/admin/Desktop/Obsidian/`
