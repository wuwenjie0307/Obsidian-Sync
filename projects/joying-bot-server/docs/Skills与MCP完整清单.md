---
tags: [reference, tools, config]
date: 2026-05-28
---

# Skills 与 MCP 完整清单

---

## 一、自建 Skill（3 个）

以下 Skill 由 Claude 在本地创建，非开源，详细信息记录在此。

### 1. image-vision（图片识别）

| 项 | 值 |
|------|-----|
| 创建日期 | 2026-05-28 |
| 用途 | 调用硅基流动 Qwen/Qwen3.6-35B-A3B 视觉模型识别图片，弥补 DeepSeek-V4-Pro 无视觉能力的缺陷 |
| API 平台 | 硅基流动（SiliconFlow） |
| 模型 | Qwen/Qwen3.6-35B-A3B |
| 路径 | `C:\Users\admin\.claude\skills\image-vision\` |
| 文件 | `SKILL.md`、`vision.py` |
| 密钥 | `SILICONFLOW_API_KEY`（环境变量，Windows 注册表） |

使用：
```bash
python C:/Users/admin/.claude/skills/image-vision/vision.py "图片路径" "可选提示词"
```

### 2. obsidian（Obsidian 笔记管理）

| 项 | 值 |
|------|-----|
| 创建日期 | 2026-05-27 |
| 用途 | 管理 Obsidian 知识库：记录 bug、changelog、项目概览、每日工作 |
| 路径 | `C:\Users\admin\.claude\skills\obsidian\` |
| 文件 | `SKILL.md`、`obsidian`（脚本） |
| Obsidian 路径 | `C:\Users\admin\Desktop\Obsidian\` |

触发词："记个 bug"、"记录到 Obsidian"、"添加项目"、"写 changelog"

### 3. mysql-query（MySQL 查询）

| 项 | 值 |
|------|-----|
| 创建日期 | 2026-05-27 |
| 用途 | 直接查询 MySQL 数据库，MySQL MCP 不可用时的备选方案，使用 Node.js mysql2 |
| 路径 | `C:\Users\admin\.claude\skills\mysql-query\` |
| 文件 | `SKILL.md`、`mysql-query`（脚本） |

---

## 二、开源 Skill（24 个）

来源：[https://github.com/obra/superpowers](https://github.com/obra/superpowers)，安装方式：`npx superpowers install`

| Skill | 用途 |
|-------|------|
| brainstorming | 创意/功能开发前探索需求与设计 |
| claude-config-sync | 同步 Claude Code 配置推送到 GitHub |
| dispatching-parallel-agents | 独立任务并行派发子 agent |
| executing-plans | 按计划分步执行实现 |
| finishing-a-development-branch | 功能完成后整合分支（merge/PR/cleanup） |
| receiving-code-review | 处理 code review 反馈 |
| requesting-code-review | 完成功能后请求 code review |
| subagent-driven-development | 当前会话独立任务并行开发 |
| systematic-debugging | 遇到 bug 先分析再修复 |
| test-driven-development | 测试驱动开发 |
| understand | 分析代码库生成知识图谱 |
| understand-chat | 基于知识图谱对话 |
| understand-dashboard | 知识图谱可视化仪表板 |
| understand-diff | 分析 git diff/PR 的影响面 |
| understand-domain | 提取业务领域知识 |
| understand-explain | 深度解释文件/函数/模块 |
| understand-knowledge | 分析 LLM wiki 知识库 |
| understand-onboard | 生成新人入职指南 |
| using-git-worktrees | Git worktree 隔离开发 |
| using-superpowers | Superpowers 技能系统使用指南 |
| verification-before-completion | 声称完成前必须验证 |
| writing-plans | 编写实现计划 |
| writing-skills | 编写新 skill（TDD 方法论） |
| update-config | 配置 settings.json |
| keybindings-help | 自定义键盘快捷键 |
| verify | 验证代码变更 |
| code-review | Review diff 找 bug |
| fewer-permission-prompts | 减少权限提示 |
| loop | 定时重复执行 |
| claude-api | Claude API / Anthropic SDK 开发 |
| run | 启动并验证应用 |
| review | Review Pull Request |
| security-review | 安全审查 |

### 安装/更新方式

```bash
# 安装所有 superpowers skills
npx superpowers install

# 或单独安装
npx superpowers install <skill-name>
```

---

## 三、MCP Server

### 内置（VS Code 扩展自带）

| MCP | 来源 | 版本 | 工具数 |
|-----|------|------|--------|
| codegraph | VS Code 扩展内置 | — | 10（search/context/explore/node/trace/impact...） |
| pencil | VS Code 扩展内置 | — | 15+（.pen 设计文件编辑） |

### 新安装（npm 包）

| MCP | npm 包 | 版本 | 用途 | 需要 API Key |
|-----|--------|------|------|-------------|
| playwright | `@playwright/mcp` | 0.0.75 | 浏览器自动化/抓数据/跑测试 | 否 |
| filesystem | `@modelcontextprotocol/server-filesystem` | 2026.1.14 | 桌面文件读写（限定 `Desktop` 目录） | 否 |
| sequential-thinking | `@modelcontextprotocol/server-sequential-thinking` | 2025.12.18 | AI 分步推理，自我验证修正 | 否 |
| context7 | `@upstash/context7-mcp` | 3.0.0 | 实时最新 API 文档（React/Next.js 等） | 否 |
| github | `@modelcontextprotocol/server-github` | 2025.4.8 | GitHub 仓库操作/Issue/PR | 是（已配 Token） |
| postgres | `@modelcontextprotocol/server-postgres` | 0.6.2 | PostgreSQL 数据库查询 | 是（未配，项目用 MySQL 暂不需要） |
| brave-search | `@modelcontextprotocol/server-brave-search` | latest | Brave 搜索引擎 | 是（已配置，Token 待填） |
| api-lab | `api-lab-mcp` | latest | API 调试 | 否 |

### MCP 配置文件

`C:\Users\admin\.claude\mcp.json`

---

## 四、自建 vs 开源统计

| 分类 | 数量 |
|------|------|
| 自建 Skill | 3（image-vision、obsidian、mysql-query） |
| 开源 Skill | ~27（来自 superpowers + Claude Code 内置） |
| 内置 MCP | 2（codegraph、pencil） |
| npm MCP | 8（playwright/filesystem/sequential-thinking/context7/github/postgres/brave-search/api-lab） |
