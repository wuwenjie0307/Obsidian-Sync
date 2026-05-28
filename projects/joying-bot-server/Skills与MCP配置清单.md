---
tags: [reference, tools, config]
date: 2026-05-28
---

# Skills 与 MCP 配置清单

## Skills（共 27 个）

### 项目管理
| Skill | 用途 |
|-------|------|
| brainstorming | 创意/功能开发前探索需求与设计 |
| writing-plans | 编写实现计划 |
| executing-plans | 按计划分步执行实现 |
| subagent-driven-development | 独立任务并行开发 |
| finishing-a-development-branch | 功能完成后决定如何合并推送到远程仓库 |

### 代码质量
| Skill | 用途 |
|-------|------|
| test-driven-development | 测试驱动开发 |
| systematic-debugging | 遇到 bug 先分析再修复 |
| code-review | Review diff 找 bug 和简化点 |
| simplify | 自动应用 code-review 建议 |
| requesting-code-review | 完成功能后请求 code review |
| receiving-code-review | 收到 review 反馈后处理 |
| verification-before-completion | 完成后验证功能是否真正工作 |
| verify | 验证代码变更是否达到预期效果 |
| security-review | 安全审查 |

### 知识管理
| Skill | 用途 |
|-------|------|
| obsidian | Obsidian 记录 bug/changelog/项目概览 |
| understand | 分析代码库生成交互式知识图谱 |
| understand-chat | 基于知识图谱的对话 |
| understand-dashboard | 知识图谱仪表板 |
| understand-diff | 分析 diff 的知识图谱变化 |
| understand-domain | 提取业务领域知识 |
| understand-explain | 解释代码架构 |
| understand-knowledge | 查询知识图谱 |
| understand-onboard | 新人入门引导 |

### 工具类
| Skill | 用途 |
|-------|------|
| image-vision | 调用硅基流动 Qwen 视觉模型看图 |
| mysql-query | 直接查询 MySQL 数据库 |
| dispatching-parallel-agents | 并行派发子 agent 处理独立任务 |
| update-config | 配置 settings.json |
| keybindings-help | 自定义键盘快捷键 |
| fewer-permission-prompts | 减少权限提示 |
| loop | 定时重复执行任务 |
| claude-api | Claude API / Anthropic SDK 开发 |
| run | 启动并验证应用 |
| review | Review Pull Request |
| using-superpowers | Superpowers 系统使用指南 |

### Git
| Skill | 用途 |
|-------|------|
| using-git-worktrees | Git worktree 隔离开发 |
| claude-config-sync | 同步 Claude Code 配置到 GitHub |

### 写作
| Skill | 用途 |
|-------|------|
| writing-skills | 编写新 skill |

---

## MCP Servers

### 已启用

| MCP | 包名 | 用途 | 状态 |
|-----|------|------|------|
| codegraph | (内置) | 代码知识图谱，符号搜索/调用链追踪 | 运行中 |
| pencil | (内置) | .pen 设计文件编辑器 | 运行中 |
| playwright | `@playwright/mcp` v0.0.75 | 浏览器自动化，自动登录/抓数据/跑测试 | 新安装 |
| filesystem | `@modelcontextprotocol/server-filesystem` | 文件系统读写，限定 `C:\Users\admin\Desktop` | 新安装 |
| sequential-thinking | `@modelcontextprotocol/server-sequential-thinking` | AI 分步推理，自我验证修正 | 新安装 |
| context7 | `@upstash/context7-mcp` v3.0.0 | 实时最新 API 文档（React/Next.js 等） | 新安装 |

### 需要额外配置才能启用

| MCP | 包名 | 需要什么 | 
|-----|------|----------|
| postgres | `@modelcontextprotocol/server-postgres` | 数据库连接字符串 `POSTGRES_URL`（⚠️ 项目用 MySQL 非 Postgres，可能不需要） |
| github | `@modelcontextprotocol/server-github` | GitHub Personal Access Token `GITHUB_PERSONAL_ACCESS_TOKEN` |
| brave-search | `@modelcontextprotocol/server-brave-search` | Brave Search API Key（已有配置，key 待填） |

### 配置文件位置

- MCP 配置：`C:\Users\admin\.claude\mcp.json`
- Claude 设置：`C:\Users\admin\.claude\settings.json`
- Skills 目录：`C:\Users\admin\.claude\skills\`

---

## 启用 GitHub MCP 的方法

1. 去 https://github.com/settings/tokens → Generate new token (classic)
2. 勾选权限：`repo`、`read:org`、`read:user`
3. 复制生成的 token（`ghp_xxx`）
4. 编辑 `C:\Users\admin\.claude\mcp.json`，把 `ghp_xxxxxxxxxxxxxxxxxxxx` 替换为你的 token
5. 重启 Claude Code

## 启用 Postgres MCP 的方法

编辑 mcp.json 中的 `POSTGRES_URL` 为实际连接串：
```
postgresql://用户名:密码@主机:端口/数据库名
```
⚠️ 当前项目使用 MySQL，Postgres MCP 可能暂无用途。
