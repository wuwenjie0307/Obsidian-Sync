---
tags: [changelog]
date: 2026-05-28
---

# AI 客户激活提示词更新

## 改动类型
- [x] 配置变更

## 改动内容

更新 `t_agent_prompt_config` 表中 `type = 'AI_CLIENT_ACTIVATE'`（id=149）的提示词内容。

需求方：欣心（国内 CRM）

**主要变更点：**

1. **Constraints 第2条**：政策时间范围从"最好是所在周度时间的政策"改为"政策优先所在时间内的政策"
2. **Constraints 第4条**：无数据时的处理从"可用当月或者近期热点事件和动态代替"改为"可省略此板块的分析"，新增约束"不要出现暂未检索出…等类似表述"

## 影响范围

- `/crm/doubao_question` 接口，当用户问"楼市周报"时使用此提示词

## 备注

- 提示词内容存在 DB 不在代码文件中，本次无代码变更
- Redis 缓存 key `prompt:COMMON:AI_CLIENT_ACTIVATE` 1小时后自动过期
