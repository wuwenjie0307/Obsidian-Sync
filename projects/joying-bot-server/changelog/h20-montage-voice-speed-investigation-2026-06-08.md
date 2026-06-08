---
date: "2026-06-08"
tags: [changelog, investigation, h20, montage, voice-clone]
---

# H20 混剪倍速字幕问题排查记录

## 改动类型

- [ ] 新功能
- [ ] Bug 修复
- [ ] 重构
- [ ] 配置变更
- [x] 排查记录

## 改动内容

本次没有修改项目代码，完成了一次 H20 测试服混剪视频任务的只读排查：

- 通过最终视频 URL 反查到测试库任务 `id=1350`、`job_id=1156`、`task_id=1138`。
- 确认任务参数为 `voice_emotion=8`、`voice_speed=3.0`、`voice_volume=77`。
- 确认任务确实有混剪素材，素材表 `t_video_material_template` 中存在 1 条 `material_type=1`、`is_mix_material=1` 的视频素材。
- 确认素材时长为 `13` 秒，绑定素材文案约 `165` 字。
- 追踪代码链路，确认字幕 ASS 先按高倍速合成音频生成，再做混剪画面覆盖，最后烧录字幕。
- 判断问题更偏参数策略/体验约束：混剪场景允许 `3.0` 倍速，导致长文案被压进过短时间窗。

## 影响范围

- 影响 H20 视频生成链路中的混剪任务。
- 普通视频链路不一定受同等影响，因为没有混剪素材覆盖和素材绑定长文案带来的视觉负担。
- 建议调整范围优先限定为“存在混剪素材时”的倍速上限，不要影响普通视频的 3 倍速能力。

## 相关 Commit

- 暂无，本次为只读排查。

## 关联记录

- [[projects/joying-bot-server/bugs/h20-montage-voice-speed-subtitle-2026-06-08|H20 混剪视频 3 倍速导致字幕体感跟不上]]
- [[projects/joying-bot-server/docs/h20-montage-voice-speed-work-summary-2026-06-08|H20 混剪倍速字幕排查今日总结]]
