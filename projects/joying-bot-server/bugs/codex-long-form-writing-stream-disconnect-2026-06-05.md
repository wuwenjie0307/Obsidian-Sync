---
date: "2026-06-05"
status: mitigated
severity: medium
tags: [codex, workflow, long-form-writing, stream-disconnect, prd, markdown]
---

# Codex 长文本写入时流中断和重复重连

## 问题描述

在为 H20 网感视频模板后端融合方案写一份较长 AI-PRD Markdown 文档时，Codex 一次性输出/写入内容过长，界面出现反复重连和流中断现象：

```text
正在重新连接
0
1
2
3
4
5
6
7
8
9
/5
stream disconnected before completion: stream closed before response.completed
```

表面现象是工具调用和写入动作看起来被重复触发，多次显示相似的检查/写入输出。虽然最终文档成功落盘，但过程中用户侧体验很差，也增加了重复写入、覆盖、截断或误判文件状态的风险。

## 原因

直接原因是长文档内容一次性生成和写入过大，导致响应流在 `response.completed` 之前关闭。

更具体地说：

- 长 PRD/Markdown 文档如果一次性通过一个巨大 patch 或长消息输出，容易触发流式传输断开。
- 断开后模型可能继续重试或重新检查，造成用户看到“正在重新连接”和重复步骤。
- 如果没有先检查文件是否已写入成功，就再次写入，可能产生重复内容或覆盖风险。
- 当前项目 `AGENTS.md` 此前没有专门约束“长文本分块写入”的操作方式。

## 解决方案

已做三项缓解：

1. 在当前项目根目录新增 `AGENTS.md`，加入“Long Markdown / PRD Writing”规则，要求长文档必须分块写入、分段验证，避免一次性巨大输出。
2. 新增个人 Codex skill：`long-form-writing`，路径：

```text
C:\Users\admin\.codex\skills\long-form-writing\SKILL.md
```

3. 该 skill 规定在用户要求写长 Markdown、PRD、AI-PRD、需求文档、runbook、设计说明等长文本时触发，采用“先大纲、再分块、每批验证、最终只给文件链接和摘要”的方式。

## 优化点

- 后续写长文档时，不要把 800 行以上内容放进一次 patch。
- 每次写入后先用 `Get-Content -TotalCount`、`Select-Object -Last`、`Select-String '^## '` 检查文件。
- 如果发生流中断，先检查文件状态，再决定是否继续补写，不能默认重写整份文档。
- 最终回复只给文件路径和简短摘要，不要把完整长文档再次贴回聊天。
- 对跨工作区写入，例如 Obsidian 或 `.codex/skills`，如果沙箱限制写入，应按权限流程申请，而不是反复尝试。

## 相关文件

- `C:\Users\admin\Desktop\AIGCVideo_副本\AGENTS.md`
- `C:\Users\admin\.codex\skills\long-form-writing\SKILL.md`
- `C:\Users\admin\Desktop\AIGCVideo_副本\docs\h20-hyperframes-viral-template-ai-prd.md`
