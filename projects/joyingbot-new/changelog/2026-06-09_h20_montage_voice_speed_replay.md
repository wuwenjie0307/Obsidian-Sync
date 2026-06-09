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

## 补充测试：正常视频链路 voice_speed=1.5
- 时间：2026-06-09 14:45 左右（H20 日志时间）
- 目标：验证不走混剪时，`voice_speed=1.5` 是否也会出现口播、字幕、视频时长不一致。
- 样本来源：正常视频已成功任务 `job_id=1152` / `task_id=1135`，本地记录 `id=1347`。
- 样本特征：`material_count=0`，`mix_count=0`，`voice_speed=1.5`，不走混剪素材分支。
- 已有完整对照片：`https://videos-test.joyingai.cn/video/crm/20260608/user4_1780907037964_96656e186535dee0.mp4`
- 对照片 ffprobe：video `45.111979s`，audio `45.119333s`，format `45.133008s`，音视频时长基本一致。

### 新 replay 任务
- 新建 replay 任务：`job_id=99115252` / `task_id=99113352`，本地记录 `id=1361`。
- 调度日志：`has_montage=False`，`voice_speed_original=1.5`，`voice_speed_effective=1.5`。
- VoxCPM 入参：`speed=1.5`。
- 克隆音频：`https://videos-test.joyingai.cn/video/crm/20260609/user4_1780987602487_a281c5c8a01aaac7.wav`，ffprobe `40.426667s`。
- 源视频原始时长：`12.400s`。
- 正常链路时间轴对齐：将模板视频对齐到克隆音频时长，输出 `https://videos-test.joyingai.cn/video/crm/20260609/user4_1780987610949_1aa15e2970c52721.mp4`，ffprobe `40.433333s`。
- 结论证据：正常链路在 HeyGem 前已把视频对齐到 1.5 倍速后的口播时长，误差约 `0.0067s`；并且字幕生成函数 `video_to_ass` 是从最终视频抽音频后用 Whisper word timestamps 对齐原文生成 ASS。

### 当前卡点
- 新 replay 没拿到最终成片：`duix-avatar-h20-test-6004` / `http://127.0.0.1:6004/easy/query?code=99113352` 持续返回 `msg=视频特征提取完成`，`progress=20`，`status=1`，`result=""`。
- DB 当前有 1 条活动测试任务：`task_status=2`，`job_id=99115252` / `task_id=99113352`。
- 模型池当前锁：`t_comfyui_config.id=16`，`config_value=http://127.0.0.1:6004`，`is_active=2`。
- 这次卡点属于 HeyGem/duix 6004 容器内部未推进，不是调度层语速裁剪或正常链路时间轴对齐失败。

### 暂定结论
- 从已有完整对照片和新 replay 的中间产物看，正常视频链路不应复现“视频仍按原长度、口播变短、字幕跟不上”的混剪类问题。
- 新 replay 的最终视觉确认需要先处理 6004 卡住或改用 6005/6006/6007 重跑。
