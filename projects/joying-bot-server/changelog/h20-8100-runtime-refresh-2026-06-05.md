---
date: "2026-06-05"
tags: [changelog, h20, runtime]
---

# h20-8100-runtime-refresh-2026-06-05

## 改动类型

- [ ] 新功能
- [x] Bug 修复
- [ ] 重构
- [ ] 配置变更

## 改动内容

检查 H20 测试服务是否运行当前发布代码，并修复 8100 端口仍运行旧发布目录的问题。

- 当前发布软链: `/data/project/test_ai_botserver -> /data/project/test_ai_botserver.20260605120425`
- 重启前 8100 PID: `3634774`, cwd `/data/project/test_ai_botserver.20260605105110`
- 重启后 8100 PID: `3918518`, cwd `/data/project/test_ai_botserver.20260605120425`
- 8017 PID: `3742389`, cwd `/data/project/test_ai_botserver.20260605120425`
- 18017 PID: `3742390`, cwd `/data/project/test_ai_botserver.20260605120425`

执行方式：只停止旧 8100 PID，并从当前软链目录使用同一 Python 环境与参数启动 8100。未重启 8017 / 18017。

## 影响范围

- H20 测试服务 8100 端口已切到当前发布目录。
- 8017 / 18017 原本已在当前发布目录，保持运行。
- 8100 和 8017 `/status/check` 均返回 `{"status":"ok"}`。
- 发现发布目录不是 Git 仓库，H20 上无法直接用 `origin/test` commit hash 做运行版本确认；后续建议在发布包或状态接口中暴露 release id。

## 相关 Commit

- H20 发布包无 `.git` 信息，未能在服务器侧取得 commit hash。

## 关联记录

- [[projects/joying-bot-server/bugs/h20-8100-runtime-stale-release-2026-06-05|h20-8100-runtime-stale-release-2026-06-05]]
