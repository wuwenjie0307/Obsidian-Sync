---
tags: [bug, tool]
date: 2026-05-28
status: known-issue
severity: low
---

# MySQL UPDATE 在 VSCode 插件中执行"卡住"

## 问题描述

在 VSCode MySQL 插件中执行 UPDATE 语句，执行了超过一分钟还在转圈，看起来像卡住了。但实际上 `SHOW PROCESSLIST` 显示所有连接都是 `Sleep` 状态，并没有锁或阻塞。

## 原因

UPDATE 实际上已经执行完成了，但 VSCode MySQL 插件没有及时刷新执行状态，UI 上仍显示为"运行中"。

## 排查步骤

1. 跑 `SHOW PROCESSLIST;` 检查是否有锁或长时间运行的查询
2. 如果全部是 `Sleep` → UPDATE 已完成，直接跑 SELECT 验证
3. 如果某条 Command 不是 Sleep 且 Time 很大 → 可能被锁，`KILL <Id>` 杀掉

## 解决方案

- 点红色停止按钮取消当前执行
- 新建一个查询窗口跑 SELECT 验证结果
- 如果确实没更新成功，关闭所有查询窗口，重新连接后再执行

## 优化点

- 关键操作后立即用 SELECT 验证，不要依赖插件的执行状态显示
- 学习使用 `SHOW PROCESSLIST` 判断数据库真实状态
