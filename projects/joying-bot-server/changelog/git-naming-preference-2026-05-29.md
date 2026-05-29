---
date: "2026-05-29"
tags: [changelog, git, preference]
---

# Git 命名偏好

## 改动类型

- [ ] 新功能
- [ ] Bug 修复
- [ ] 重构
- [x] 配置变更

## 改动内容

用户明确要求：下次提交 Git 的时候不要带 `codex` 这个名字。

后续项目 Git 操作偏好：

- 分支名不要包含 `codex`。
- commit message 不要包含 `codex`。
- MR 标题、描述、其他 Git 可见命名默认不要包含 `codex`。
- 只有用户明确要求时才使用 `codex`。

## 影响范围

适用于 `joyingbot-new` / `crm.ai.joyingbot` 后续本地分支、提交、push 和 MR 操作。
