---
date: "2026-06-09"
status: deferred
priority: high
tags: [todo, deferred, production, montage, crm-sync, database, scheduler]
---

# 生产混剪素材同步大改延后待办

## 背景

2026-06-09 今日排期中，原本的第 1、2、3 项分别是：

1. 处理生产混剪素材同步的 CRM ID 阻断项。
2. 决定 AI 侧 `t_video_material_template.material_id` 是否从 `int` 改为 `BIGINT`。
3. 重新设计 scheduler 素材同步修复。

这三项互相耦合，并且涉及 CRM 数据修复、AI 数据库表结构变更、scheduler 同步逻辑和生产发布窗口，改动面偏大。当前先暂停，不进入今天主线；今天优先解决“混剪 + 倍速”策略问题。

## 暂停原因

- CRM 侧存在异常素材 ID：样例 `1780827482284` 形态接近毫秒时间戳，超过 MySQL signed int 最大值 `2147483647`。
- AI 本地表 `t_video_material_template.material_id` 当前为 `int`，如果 CRM 返回 bigint 或异常大 ID，素材同步入库可能失败。
- scheduler 素材同步修复不能孤立合并；如果 DB 字段和 CRM 数据没处理好，改成 `materialUsertaskList` 后仍可能因为素材 ID 入库失败导致纯口播。
- 原生产 hotfix `hotfix/prod-montage-material-sync` 已撤回，`master` 未合并；`test` 分支也已通过 revert 回退相关改动。

## 恢复处理前提

- [ ] CRM 确认异常素材 ID 为什么被写成毫秒时间戳。
- [ ] CRM 确认素材来源表真实表名，以及 `/materialUsertaskList` 返回的 `video_material.id` 来源。
- [ ] CRM 核对是否存在更多 `id > 2147483647` 的素材记录。
- [ ] CRM 确认素材表 `AUTO_INCREMENT` 是否被异常大 ID 顶高。
- [ ] CRM 修复异常数据和自增值，或明确这些 bigint ID 是业务允许的长期形态。

## 待办清单

- [ ] 查 AI 测试库和生产库 `t_video_material_template.material_id` 当前字段类型。
- [ ] 如果 CRM 素材 ID 长期为 bigint，AI 模型字段改为 `db.BigInteger`。
- [ ] 如果需要改 DB，准备并评审迁移 SQL：`ALTER TABLE t_video_material_template MODIFY COLUMN material_id BIGINT NOT NULL COMMENT '素材ID（materialUsertaskList 返回的 id）';`。
- [ ] 测试库先执行表结构变更并验证素材同步。
- [ ] 生产库安排维护窗口或低峰执行表结构变更。
- [ ] 重做 scheduler 素材同步修复：不再用 `video_category == 2` 作为混剪素材同步开关。
- [ ] scheduler 改为按 `company_id + job_id + task_id` 调 `materialUsertaskList` 同步用户任务素材。
- [ ] 入库时按接口返回行中的真实 `task_id` 隔离多任务素材。
- [ ] 不再硬性只保留 `is_mix_material=1`，优先看 `task_id`、`material_source_url`、`material_subtitle`、`material_type` 等有效字段。
- [ ] 增加日志：素材接口、`company_id/job_id/task_id`、返回 `total`、实际入库条数、跳过原因。
- [ ] 增加回归测试：`video_category=0` 但 `materialUsertaskList` 有素材时，素材能入本地表并进入后续混剪生成链路。
- [ ] 重新制作 hotfix 分支，先上 test 验证，再决定是否合生产 master。

## 当前沟通口径

这组问题先不并入今天主线。它不是单纯改一处 scheduler 逻辑，而是 CRM 数据、AI 表结构、scheduler 同步和生产发布共同组成的大改动。等 CRM 侧把异常 ID 和自增值问题确认清楚后，再整体恢复推进。

## 关联记录

- [[projects/joying-bot-server/bugs/prod-scheduler-montage-material-sync-2026-06-08|生产 scheduler 未同步用户混剪素材导致纯口播]]
- [[projects/joying-bot-server/docs/h20-montage-voice-speed-work-summary-2026-06-08|H20 混剪倍速字幕排查今日总结]]
