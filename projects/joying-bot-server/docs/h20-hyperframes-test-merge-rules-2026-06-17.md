---
date: "2026-06-17"
project: "joying-bot-server"
type: doc
tags: [doc, git, h20-hyperframes, test-merge]
aliases: ["H20 HyperFrames test 合并规则"]
---

# H20 HyperFrames test 合并规则

## 图谱链接

- 项目: [[projects/joying-bot-server/00-项目概览|joying-bot-server]]
- 索引: [[projects/joying-bot-server/docs/00-docs-index|参考文档索引]]

## 背景

2026-06-17 复盘 `feature/ai_v6.3.3_vibevideo` 集成到 `test` 的历史时，发现 `test` 上出现了多条 `Merge remote-tracking branch 'origin/feature/ai_v6.3.3_vibevideo' into merge-check/...` 相关 merge 记录。虽然内容核对后主要仍是网感视频相关改动，但这个流程会污染 `test` 历史，也会让后续判断 `feature -> master` 是否与测试验收一致变复杂。

## 结论

这条规则必须作为后续网感视频开发的硬约束：测试服 bug 先修回 `feature/ai_v6.3.3_vibevideo`，再从功能分支干净集成到 `test`；任何临时冲突检查分支、`merge-check` 分支或模拟 merge commit 都不能进入共享分支。

## 关键内容

- `feature/ai_v6.3.3_vibevideo` 是网感视频功能开发源分支。
- `test` 只作为测试环境集成分支，不能在 `test` 上直接修网感 bug 后绕过 feature。
- 冲突检查必须使用非污染方式：优先 `git merge-tree origin/test origin/feature/ai_v6.3.3_vibevideo`，或使用本地临时 worktree/临时分支模拟。
- 本地临时分支名可以包含 `merge-check`，但该分支和它生成的 merge commit 不能 push、不能合入 `test`、不能作为后续 `test` 基线。
- 合入 `test` 时，只允许从干净的 `origin/feature/ai_v6.3.3_vibevideo` 合入当前最新 `origin/test`。
- 如果测试服发现新 bug：修复顺序必须是 `feature/ai_v6.3.3_vibevideo` 提交并推送，再重新集成到 `test` 验收。
- 不允许为了检查冲突而把 `origin/test` 合回功能分支，除非用户明确要求更新功能分支基线。
- 合并前必须展示：当前分支、目标分支、待合入 commit 列表、diff stat、测试结果，并获得明确确认。
- 已经进入 `test` 的历史不轻易强改；如需清理，必须单独评估测试服部署状态，并由用户明确确认回滚/重做方案。

## 相关文件

- `C:\Users\admin\Desktop\joyingbot-new-h20-hyperframes-dev`
- `C:\Users\admin\.codex\skills\pushing-gitlab-branches\SKILL.md`
- `C:\Users\admin\.codex\skills\h20-hyperframes-development\SKILL.md`

## 相关记录

- [[projects/joying-bot-server/docs/h20-hyperframes-runtime-automation-2026-06-16|h20-hyperframes-runtime-automation-2026-06-16]]
- [[projects/joying-bot-server/docs/h20-hyperframes-db-field-change-rules-2026-06-16|h20-hyperframes-db-field-change-rules-2026-06-16]]
