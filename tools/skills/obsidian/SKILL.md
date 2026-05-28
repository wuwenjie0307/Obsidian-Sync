---
name: obsidian
description: Use when the user asks to record a bug, log a changelog, add a new project to Obsidian, or manage their Obsidian vault. Also use proactively when starting work on a project (debugging, features, code review) — load context from the vault first to check past bugs, changelogs, and project notes at C:\Users\admin\Desktop\Obsidian
---

# Obsidian Vault Manager

> ⚠️ **跨设备迁移**：本 skill 含硬编码路径，换设备后需修改以下值：
>
> | 硬编码值 | 位置（行关键词） | 新设备应改为 |
> |----------|-----------------|-------------|
> | `C:\Users\admin\Desktop\Obsidian` | 全文多处（Vault 路径） | 新设备的 Obsidian vault 路径 |
> | `C:\Users\admin\Desktop\Obsidian/projects/` | Core Operations 各节 | 对应项目子目录 |
> | `C:\Users\admin\Desktop\Obsidian/` | Common Mistakes | vault 根路径 |
>
> 替换方法：全文搜索 `C:\\Users\\admin\\Desktop\\Obsidian` → 替换为新路径。

## Overview

Manage the user's Obsidian vault through direct markdown file operations. The vault is a local knowledge base that tracks projects, bugs, and changelogs independently of any project repository.

**Vault location:** `C:\Users\admin\Desktop\Obsidian`

## Vault Structure

```
Obsidian/
  00-总览.md                    ← Entry page, links to all projects
  _templates/
    bug-report.md               ← Bug report template
    changelog.md                ← Changelog entry template
  projects/
    {project-name}/
      00-项目概览.md            ← Project overview (path, modules, config)
      bugs/                     ← Bug records
      changelog/                ← Changelog entries
  daily/                        ← Daily notes (future use)
```

## When to Use

- **Proactive:** starting ANY work on a project (debugging, feature dev, code review, refactoring)
- User says "add this project to Obsidian" or starts a new project
- User mentions fixing a bug, debugging, or asks to record a bug
- User says "log this update", "record this change", or completes a feature
- User asks about past issues, project history, or "what happened with X"

## Core Operations

### 0. Load Context from Vault (PROACTIVE)

**Do this FIRST before any project work** — debugging, feature dev, code review, refactoring. The vault is the project's long-term memory; skip this and you miss past lessons.

**Step 1 — Check if project exists in vault:**
```bash
ls "C:/Users/admin/Desktop/Obsidian/projects/{project-name}/" 2>/dev/null
```

**Step 2 — If found, read the overview and scan recent records:**
1. Read `projects/{project-name}/00-项目概览.md` — understand module layout
2. Glob `projects/{project-name}/bugs/*.md` — past bugs, their causes, and fixes
3. Glob `projects/{project-name}/changelog/*.md` — recent changes and patterns

**Step 3 — Use the context:**
- When debugging: search bug records for similar symptoms or related files
- When coding: check changelogs for recent changes in the same area (avoid conflicts)
- When reviewing: cross-reference with known past issues

**If the project doesn't exist in the vault yet** → ask the user if they want to add it (Operation 1).

### 1. Add a New Project

When the user starts a new project or asks to add one:

1. Scan the project root directory to identify top-level directories and key files
2. Create `projects/{project-name}/` with `bugs/` and `changelog/` subdirectories
3. Write `00-项目概览.md` with a table of modules (directories) and their inferred purpose
4. Append a link to `00-总览.md` in the project list section

The project overview should include: path on disk, git branch (if available), project type, a module table, and key config files.

### 2. Record a Bug

When the user reports or fixes a bug:

1. Identify which project the bug belongs to (ask if ambiguous)
2. Read `_templates/bug-report.md` for the template structure
3. Create `projects/{project-name}/bugs/{bug-title}.md` with:
   - Date, status, severity
   - Problem description (what happened)
   - Root cause (why it happened)
   - Reproduction steps (if relevant)
   - Solution (how it was fixed)
   - Optimization points (what could be improved)
   - Related files (file paths in the project)
4. Set status to `open` for new bugs, `fixed` for resolved ones

### 3. Record a Changelog

When the user makes a functional change:

1. Identify which project (ask if ambiguous)
2. Read `_templates/changelog.md` for the template structure
3. Create `projects/{project-name}/changelog/{change-title}.md` with:
   - Date, change type (new feature / bug fix / refactor / config change)
   - What was changed
   - Scope of impact
   - Related commits (if available from git log)
4. Use `_` as filename separator for spaces

## Quick Reference

| Trigger | Action | Target |
|---------|--------|--------|
| 开始 debug / 做功能 / review 代码 | 读 vault → 加载历史 bug + changelog + 项目概览 | Context loading (Operation 0) |
| "记个 bug" / "fix了 X" | Copy bug template → `projects/{project}/bugs/` | Bug record |
| "记录一下这个更新" | Copy changelog template → `projects/{project}/changelog/` | Changelog entry |
| "新项目" / "加到 Obsidian" | Create project dir + overview + update 00-总览.md | Project entry |

## Implementation

### Project overview template

```markdown
---
tags: [project, overview]
---

# {project-name}

## 基本信息
- 路径: `{absolute-path}`
- 分支: `{branch}`
- 类型: {Python/Node.js/...}

## 核心模块
| 目录 | 用途 |
|---|---|
| ... | ... |

## 配置
- ...
```

### Bug record key fields

Every bug record MUST include: **问题描述**, **原因**, **解决方案**, **优化点**. These are the four mandatory sections beyond the template boilerplate.

### Changelog key fields

Every changelog MUST include: **改动类型** (checked), **改动内容**, **影响范围**.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Putting vault files inside the project directory | Always write to `C:\Users\admin\Desktop\Obsidian/`, never inside the project |
| Forgetting to update `00-总览.md` when adding a project | Always append the project link to the entry page |
| Skipping root cause in bug reports | Always include WHY the bug happened, not just the fix |
| Using spaces in filenames | Use hyphens: `login-timeout-fix.md` not `login timeout fix.md` |
| Not asking which project when ambiguous | When the user has multiple projects, confirm which one |

## Red Flags

- Writing to the wrong path (project dir instead of vault) — double-check the path starts with `C:\Users\admin\Desktop\Obsidian\`
- Creating a bug record without root cause — wait and ask the user if cause is unknown
- Adding a project without scanning its actual directory structure first
- Jumping into debugging without checking vault for related past bugs — always load context first (Operation 0)
- Skipping vault context because "this problem is different" — past bugs in the same files are always relevant
