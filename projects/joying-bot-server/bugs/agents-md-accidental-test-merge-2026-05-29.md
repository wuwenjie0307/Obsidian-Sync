---
date: "2026-05-29"
status: fixed
severity: medium
tags: [bug, git, test, deployment]
---

# AGENTS.md 误合入 test

## 问题描述

在将 h20 端口方案合入远端 `test` 时，提交 `45b4e66d docs: update h20 bot 48100 gateway plan` 误带入了 `AGENTS.md`。

该文件不应作为本次业务/配置变更进入 `test`。

## 原因

本次为了避免把基于 `master` 路径的历史直接合到 `test`，从 `origin/test` 新建了 `h20-bot-48100-gateway-test` 分支，并 cherry-pick 旧提交 `241d73e3`。

旧提交本身包含新增 `AGENTS.md`。执行时只排除了后续本地 stash 中的命名规则修改，没有在 cherry-pick 后额外排除整个 `AGENTS.md` 文件，导致该文件随 `45b4e66d` 一起进入 `origin/test`。

## 解决方案

已在 `h20-bot-48100-gateway-test` 上新增修正提交：

```text
a62f3391 chore: remove accidental local notes from test
```

该提交删除 `AGENTS.md`，并已推送到远端 `test`：

```text
45b4e66d..a62f3391  HEAD -> test
```

修正后确认：

```powershell
git ls-tree -r --name-only origin/test | rg "^AGENTS\.md$"
```

无输出，表示 `origin/test` 当前已不包含 `AGENTS.md`。

## 优化点

后续从旧提交 cherry-pick 到 `test` 前，需要先用以下命令检查将要带入的文件列表：

```powershell
git show --name-status <commit>
```

如果旧提交包含本次不应进入远端分支的文件，应该在 cherry-pick 后、提交前执行：

```powershell
git restore --staged <file>
git restore <file>
```

或者在提交后但推送前用新提交或 amend 移除，不能只检查文件内容是否包含敏感字样。

## 相关分支与提交

- 目标分支：`origin/test`
- 工作分支：`h20-bot-48100-gateway-test`
- 误带入提交：`45b4e66d docs: update h20 bot 48100 gateway plan`
- 修正提交：`a62f3391 chore: remove accidental local notes from test`
