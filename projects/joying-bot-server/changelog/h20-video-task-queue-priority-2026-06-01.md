---
tags: [changelog, h20, crm, video-generation, scheduler]
---

# h20 测试库视频任务队列清理并保留 16:36:22 任务

## 时间

- 2026-06-01 17:01 左右

## 背景

产品/测试希望优先处理 `2026-06-01 16:36:22` 提交的视频任务，测试库此前存在大量历史排队和卡住任务，且 `t_comfyui_config.id=1` 一直处于 `is_active=2`，导致新任务无法继续领取。

## 保留任务

- `t_video_generate_task.id = 1208`
- `job_id = 1005`
- `task_id = 996`
- `job_name = C1T117U4T20260601163622`
- `task_created_time = 2026-06-01 16:36:22`
- `cover_title = 上海房价直接锁死了！核心地段再也捡不了漏`

## 执行内容

- 将除 `id=1208` 外的 `task_status in (0,1,2,5,6)` 测试任务统一标记为失败：`task_status=4`。
- 影响行数：`104`。
- 失败原因统一写入：`测试手动取消：仅保留 2026-06-01 16:36:22 任务优先处理`。
- 释放 `t_comfyui_config.id=1`：`is_active=2 -> 1`。

## 执行后状态

- 队列中只剩目标任务 `id=1208`。
- 下一轮调度已领取目标任务：`task_status=2`。
- `t_comfyui_config.id=1` 已重新变为 `is_active=2`，说明目标任务已占用生成槽位。
- h20 VoxCPM 日志显示该任务声音克隆已实际开始并完成一次合成，耗时约 `69.28s`。

## 最终结果

- 2026-06-01 17:20 复查，目标任务已完成：
  - `task_status=3`
  - `progress=100`
  - `callback_status=1`
  - `t_comfyui_config.id=1 is_active=1`，调度锁已释放。
- 最终视频：
  - `https://videos-test.joyingai.cn/video/crm/20260601/user4_1780305603883_2f6ba608cc01aee8.mp4`
- CRM 完成回调成功：
  - 回调 `task_status=7`
  - `generate_video_duration=69`
  - CRM 返回 `code=200`
- 生成链路确认：
  - VoxCPM 声音克隆完成，耗时约 `69.28s`。
  - LatentSync 已调用 `/v1/lip-sync` 并返回 `200 OK`。
  - 本地出现 `latentsync_996_*` 中间文件和 ASS 字幕文件。
  - 最终视频上传成功并回调 CRM。
- 注意：生成完成后定时任务 3 尝试调用本机 `127.0.0.1:8015/publish_video_task` 发布接口失败，原因是该发布服务未启动或未监听 8015；但 CRM 视频生成结果已成功回调，不影响本次“生成视频”验收。

## 注意

- 本次是测试库人工清队操作，不应照搬到生产库。
- 被清理任务未逐条触发 CRM 失败回调，只是测试库本地任务状态清理。
- 后续如果要产品端同步看到失败，需要另行确认是否要补发 CRM 回调。
