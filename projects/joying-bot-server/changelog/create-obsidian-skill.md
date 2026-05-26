---
date: "2026-05-25"
tags: [changelog]
---

# 创建 Obsidian 管理 Skill

## 改动类型

- [x] 新功能
- [ ] Bug 修复
- [ ] 重构
- [ ] 配置变更

## 改动内容

在 Claude Code 全局 skills 中新增 obsidian skill，支持三个核心操作：
1. 新项目添加 — 自动扫描项目结构，在 Vault 中创建项目概览
2. Bug 记录 — 按模板格式记录问题描述、原因、解决方案、优化点
3. 更新日志 — 按模板格式记录改动类型、内容、影响范围、关联 commit

Skill 放在 `~/.claude/skills/obsidian/SKILL.md`，所有项目通用。

## 影响范围

- Vault: `C:\Users\admin\Desktop\Obsidian`
- 后续所有项目的 bug 和更新都会写入此处
- 与项目代码物理隔离，不污染 git 仓库

## 相关 Commit

-
