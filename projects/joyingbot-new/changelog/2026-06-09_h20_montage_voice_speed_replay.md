---
tags: [project, changelog, h20-test]
---

# 2026-06-09 H20 montage voice speed replay

## 测试目标
- 使用一条真实混剪任务的素材链，模拟后端调度任务。
- 分别验证 `voice_speed=1.5` 和 `voice_speed=3.0` 在 H20 当前 test release 上的实际处理结果。

## 样本来源
- 原始样本任务：`job_id=1160` / `task_id=1141`
- 样本状态：已成功生成过，1 条混剪视频素材，`is_mix_material=1`
- 样本素材：`material_id=633`，视频素材，原链路会先静音再叠加

## 测试任务 1：voice_speed=1.5
- 测试任务：`job_id=99116015` / `task_id=99114115`
- DB 输入：`voice_speed=1.5`
- 调度日志：`voice_speed_original=1.5` / `voice_speed_effective=1.5`
- 结果：`task_status=3`，`progress=100`，生成成功
- 输出视频：`https://videos-test.joyingai.cn/video/crm/20260609/user4_1780985407002_9aba480e360478fc.mp4`
- 生成耗时：`generate_total=195938ms`

## 测试任务 2：voice_speed=3.0
- 测试任务：`job_id=99116030` / `task_id=99114130`
- DB 输入：`voice_speed=3.0`
- 调度日志：`voice_speed_original=3.0` / `voice_speed_effective=1.5`
- 结果：`task_status=3`，`progress=100`，生成成功
- 输出视频：`https://videos-test.joyingai.cn/video/crm/20260609/user4_1780985894974_547cedd5c4dad7e5.mp4`
- 生成耗时：`generate_total=203934ms`

## 混剪链路证据
- 两条任务都进入了 `video_work_Heygem_Whisper`。
- 混剪素材日志显示先执行静音处理，再按字幕区间进行时长对齐和叠加。
- `3.0` 任务进入 `video_work` 时日志中的时间轴对齐参数为 `voice_speed=1.5`，说明调度层已完成降级。

## 收尾状态
- 两条测试任务均已成功生成。
- `t_video_generate_task` 没有 `0/1/2/5` 活动任务残留。
- `t_comfyui_config` 没有 `is_active=2` 模型池锁，4 个 `comfyui_url` 可用。

## 注意事项
- 测试任务使用的是复制出来的假 `job_id/task_id`，所以 CRM 回调返回 `record not found` 属于预期，不影响生成结论。
- 第一条测试任务复制了原任务发布字段，发布定时任务曾尝试调用本地 `8015` 并失败；后续已确认该任务 `publish_call_status=2`，没有待发布残留。
- 第二条测试任务创建时已将发布字段禁用，避免额外发布噪声。
