---
date: 2026-06-11
project: joyingbot-new
type: bug
status: investigation
severity: medium
tags: [bug, h20, voice-clone, audio-noise, video-generation]
aliases: [H20 生成视频口播嗡嗡噪音]
---

# H20 生成视频口播嗡嗡噪音

## 问题描述

2026-06-11 用户反馈最新生成的视频中，口播出现“嗡嗡”的背景噪音。噪音只在视频有人声口播时出现；口播间隙、没有说话的静音片段没有该噪音。

该现象初步指向噪音跟人声链路绑定，而不是整条视频音轨中持续存在的底噪。需要继续验证噪音是在试听生成的参考音频、VoxCPM 克隆生成音频、LatentSync 输出、BGM 混音、字幕/导出或最终 mux 的哪一层引入。

## 影响范围

- H20 测试服视频生成链路。
- 语音克隆链路，尤其是“前端试听接口生成音频 -> 保存为原音色 -> 生成视频复用该音频做克隆参考”的流程。
- 可能影响最终视频口播观感和可用性。


## 新增证据

- 2026-06-11 用户补充：试听接口生成后的原音频本身也能听到同类嗡嗡背景噪音。
- 这说明最终视频中的噪音大概率不是视频 mux、字幕烧录、BGM 混音或对嘴阶段首次引入，而是更早出现在试听音频生成阶段，后续保存为原音色后被视频生成链路继续复用。
- 当前排查重心前移到 `voice_clone_audition` 调用 VoxCPM 生成试听音频的输出质量、VoxCPM clone 模式、参考音频预处理和输出后处理。
## 已知上下文

- 当前已对齐的链路：前端使用试听接口生成音频，并把试听音频作为克隆音色的原音频保存到形象。
- 进入视频生成任务时，后端使用保存下来的 `voice_file_url` 作为原音频进行音色克隆。
- 因为情绪、语速、音量等参数已经在试听阶段选择并生成过参考音频，为避免生成视频时二次传参导致二次处理，视频生成阶段的音色克隆不额外上传试听参数，而是走默认参数，例如 `voice_emotion=1`、`voice_speed=1.0`、`voice_volume=50`。
- 相关链路改动记录：[[projects/joyingbot-new/changelog/2026-06-11_h20_preview_audio_reuse_flat_payload|H20 试听音频复用 flat payload]]。


## 排查结果（2026-06-11）

- 用户补充试听接口生成后的原音频本身已有同类嗡嗡噪音后，排查重心从视频生成阶段前移到试听生成阶段。
- H20 日志确认，最新相关试听音频 `user4_1781158803929_bfaaa76c278a0cc6.wav` 在 2026-06-11 14:18:59 调用 VoxCPM 生成：`emotion=4`、`speed=1.0`、`volume=70`、`text_len=16`、`reference_text_len=20`，生成后上传为保存到形象的原音频。
- 同一任务后续视频生成阶段因 `voice_file_url` 是试听生成的 wav，后端按既定策略重置为默认克隆参数：`voice_emotion=1`、`voice_speed=1.0`、`voice_volume=50`，没有二次传入试听情绪/音量参数。
- 对比 14:08~14:19 多条试听 wav：`emotion=1/2/8, volume=70` 均未出现满幅削波；最新 `emotion=4, volume=70` 的 wav 峰值达到 `0 dBFS`，存在满幅样本，说明某些情绪模式输出电平偏热，被 `voice_volume=70` 放大后会发生硬削波/饱和。
- 因为该过载音频被保存为原音色，最终视频只是继承并可能在 BGM 混音时略微放大该噪声，第一现场在 `voice_clone_audition -> VoxCPM 输出后处理`。

## 当前修复

- 本地代码在 `router/service/video_server/voxcpm_api.py` 的 `apply_audio_effects` 中增加 `limit_audio_peak`，在 `np.clip(-1, 1)` 前将超过 `0.92` 的生成音频整体压回安全峰值，避免写 WAV 前发生硬削波。
- 该修复不需要前端新增字段，也不改变试听音频作为原音色保存和视频生成复用的链路。
- 已新增单测覆盖：超过满幅风险的输出会被限制在目标峰值内；本来安全的音频不会被改变。

## 验证结果

- `python -m unittest test.test_voxcpm_voice_style_prompt`：通过，17 个测试中 2 个因系统 Python 无 numpy 跳过。
- `Codex bundled Python -m unittest test.test_voxcpm_voice_style_prompt`：通过，17 个测试全跑过。
## 排查计划

1. 确认用户所说“最新生成的视频”对应的 H20 任务 ID、最终视频 URL、参考音频 URL、克隆生成音频 URL。
2. 分别检查参考试听音频、克隆生成音频、最终视频抽取音轨，确认噪音首次出现的层级。
3. 如果参考音频已有噪音，回查试听接口输出和保存音频质量。
4. 如果参考音频干净但克隆生成音频有噪音，重点检查 VoxCPM 克隆输入、默认参数、参考文本和音频预处理。
5. 如果克隆音频干净但最终视频有噪音，重点检查 LatentSync、BGM 混音、音量/压缩器、编码和最终 mux。

## 原因

待调查。当前不能确定根因，只能确认噪音现象与“有人声口播片段”强相关。

## 解决方案

待根因确认后补充。修复方向必须基于分层音频证据，避免只靠调参掩盖问题。

## 优化点

- 建议后续在视频生成日志中保留或记录关键中间音频产物：参考音频、克隆生成音频、LatentSync 输出音频、BGM 混音后音频，方便快速定位音频质量问题。
- 对口播音频增加基础质量检测指标，例如静音段 RMS、语音段高频/低频异常能量、峰值、响度和是否存在固定频率嗡声。

## 图谱链接

- [[projects/joyingbot-new/00-项目概览|joyingbot-new 项目概览]]
- [[projects/joyingbot-new/bugs/00-bugs-index|Bug 记录索引]]
- [[projects/joyingbot-new/changelog/2026-06-11_h20_preview_audio_reuse_flat_payload|H20 试听音频复用 flat payload]]