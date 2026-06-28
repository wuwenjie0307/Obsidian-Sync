---
tags: [bug, h20, vibevideo, montage, fixed]
date: 2026-06-28
status: fixed
severity: high
---

# H20 网感混剪素材与口播文案边界偏移

## 问题描述
测试服网感视频链路中，用户选择的混剪素材与对应口播文案存在边界偏移。典型表现是口播已经进入下一段素材文案，例如“目前均价19875元/㎡”，画面仍停留在上一段混剪素材；另有任务出现素材存在时间少半句或末段素材未按预期生效。

## 原因
网感 HyperFrames 链路中，混剪素材 timing 使用素材字幕/素材文案去最终字幕时间轴里反查时间。旧逻辑优先依赖 subtitle cue 匹配，cue 文本与素材文案在 TTS/ASR 改写、数字单位表达、断句合并或重复文本场景下不完全一致时，会退回整段文本线性比例估算，导致素材切换点偏晚或偏早。

极简风格没有复现，核心差异是极简链路使用 Whisper word-level 时间戳对齐到原文字符时间轴，再按用户选择文案定位时间段，不依赖 cue 断句必须干净。

## 解决方案
在网感链路 `_apply_hyperframes_overlay_timings` 中迁入极简链路的核心定位方式：

- 优先使用 `whisper_timeline.words` 构建原文字符级时间轴。
- 按素材字幕在原文中的 start/end 位置直接取真实 word/char 时间。
- 保留原 cue 匹配与线性估算作为兜底，避免没有 word timestamps 的旧路径被破坏。
- 用原文位置匹配而不是重新搜索素材字幕，避免重复文案匹配到错误段落。

相关提交：`b869e54a fix: align vibevideo montage timing from whisper words`

## 验证
- 新增失败复现测试：cue 文本与素材文案不一致时，旧逻辑会把第一段结束从真实 `7.0s` 算到 `8.716s`，修复后使用 word alignment 回到 `7.0s`。
- 新增重复文案/图片素材顺序测试：两段重复文案和一段图片素材按真实时间依次生效。
- `python -m unittest test.test_video_material_montage_sync`：24 tests OK。
- `python -m unittest test.test_hyperframes_analysis`：21 tests OK。
- `python -m unittest test.test_hyperframes_cli`：38 tests OK。
- `python -m unittest -v test.test_hyperframes_postprocess`：55 tests OK。
- `python -m unittest test.test_hyperframes_subtitle_translation test.test_hyperframes_upload_callback test.test_montage_material_audio_policy`：14 tests OK。
- `git diff --check`：OK。

## 影响范围
只影响网感 HyperFrames 链路的混剪素材时间定位。极简风格旧链路未改动；没有 `whisper_timeline.words` 的任务仍走原 cue/线性兜底。

## 追加问题：稀疏选择素材仍走旧 cue 匹配
2026-06-28 追加发现：任务 `1623` 中三段混剪素材只覆盖原文约 48.5%，不属于 full-cover/high-density selected span。旧修复只在 full-cover 路径优先使用 word-level 对齐，导致这种稀疏选择场景仍会回到 cue 匹配；当第二段素材开头“都说成都电动车乱穿窜得快...”在 cue 文本中被改写或拆分时，旧 cue 匹配会从下一句“哪一辆车后面...”开始，表现为第二段混剪少了前面一句口播。

追加修复：

- 只要素材文案能在原文中定位，并且 `whisper_timeline.words` 可用，就优先使用 word-level 字符时间轴。
- coverage 阈值只继续约束没有 words 或 word alignment 失败时的 cue/linear fallback。
- 保留 `repair_time_gaps_func` 写回路径，避免相邻素材露原视频的问题再次复现。

追加提交：`2a3b73fe fix: use word timing for sparse vibevideo montage`

追加验证：
- 新增稀疏选择回归测试：第二段 cue 开头被改写时，必须从真实 word time `20.0s` 开始，而不是从下一句 `22.0s` 开始。
- `python -m unittest test.test_video_material_montage_sync`：26 tests OK。
- `python -m unittest test.test_hyperframes_analysis test.test_hyperframes_cli`：59 tests OK。
- `python -m unittest test.test_hyperframes_subtitle_translation test.test_hyperframes_upload_callback test.test_montage_material_audio_policy`：14 tests OK。
- `python -m unittest -v test.test_hyperframes_postprocess`：55 tests OK。
- `git diff --check`：OK。
