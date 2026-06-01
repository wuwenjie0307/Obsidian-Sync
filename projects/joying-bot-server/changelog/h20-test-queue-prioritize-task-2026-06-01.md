---
tags: [changelog, h20, crm, video-generation, queue]
---

# h20 测试库队列清理并优先处理 16:36:22 任务

## 时间

- 2026-06-01 17:01-17:05

## 背景

测试环境视频生成队列积压，并且 `t_comfyui_config.id=1` 处于 `is_active=2` 锁定状态。用户要求清理后台排队任务，只保留 `2026-06-01 16:36:22` 的任务优先处理。

## 操作内容

目标任务唯一确认：

- `t_video_generate_task.id = 1208`
- `job_id = 1005`
- `task_id = 996`
- `job_name = C1T117U4T20260601163622`
- `task_created_time = 2026-06-01 16:36:22`
- `cover_title = 上海房价直接锁死了！核心地段再也捡不了漏`

执行测试库更新：

- 将除 `id=1208` 外的 `task_status in (0,1,2,5,6)` 任务统一标记为 `task_status=4`。
- 影响任务数：`104`。
- `fail_reason` 设置为：`测试手动取消：仅保留 2026-06-01 16:36:22 任务优先处理`。
- 释放调度锁：`UPDATE t_comfyui_config SET is_active=1 WHERE id=1`。

## 验证结果

清理后状态：

- `task_status=0` 只剩 `1` 条，即目标任务 `id=1208`。
- 下一轮调度已领取目标任务：`id=1208` 变为 `task_status=2`。
- `t_comfyui_config.id=1` 重新变为 `is_active=2`，说明配置已被该任务占用。
- VoxCPM 日志显示本次声音克隆已开始并完成，耗时约 `69.28s`。
- 截至 `2026-06-01 17:05:35`，目标任务仍在处理中，尚未生成最终 `generate_video_url`。

## 注意

本次是测试库人工清理队列操作，不是代码变更。被标记失败的任务没有逐条触发 CRM 失败回调，主要目的是清空测试调度队列，让指定任务优先跑通。
