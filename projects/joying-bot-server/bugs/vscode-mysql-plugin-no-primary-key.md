---
tags: [bug, tool]
date: 2026-05-28
status: known-issue
severity: low
---

# VSCode MySQL 插件双击编辑报"没有主键"

## 问题描述

在 VSCode MySQL 插件中 SELECT 查询 `t_agent_prompt_config` 表后，双击结果表格的 `prompt` 单元格编辑内容，Ctrl+S 保存时弹出错误："没有主键，此改动可能会比预想的更多"。

## 原因

VSCode MySQL 插件在执行 SELECT 查询结果中，如果 SQL 不是 `SELECT *` 而是 `SELECT id, model, type, prompt` 等指定列，且插件无法确定主键列，就会拒绝直接编辑。

## 解决方案

**不要用表格编辑功能**，直接写 SQL UPDATE 语句：

```sql
UPDATE t_agent_prompt_config 
SET prompt = '新内容' 
WHERE id = 149;
```

## 优化点

- 涉及数据库修改的操作优先用 SQL 语句，避免依赖 GUI 插件的编辑功能
- GUI 插件适合查看数据，不适合修改数据
