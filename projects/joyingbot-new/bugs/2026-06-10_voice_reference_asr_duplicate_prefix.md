---
date: "2026-06-10"
status: fixed
severity: high
tags: [bug, h20-test, voice-clone, video-generation]
---

# 试听音频作为原音色后视频开头重复口播

## 问题描述
使用“试听生成的音频”作为个人形象的原始音频样本后，再生成正式视频时，成片开头可能多出一段原文案后半段口播。随后正式正文又从头开始播放，导致视频内容和口播重复；多出来的开头段没有字幕。

本次用户反馈的重复段示例包含：`满100就能直接减10块...死蹲这波羊毛别错过`，随后正文又从 `骆驼这次618羊毛不薅真的亏大了` 开始。

## 复现步骤
1. 在测试服个人形象里选择声音样本，情绪选择愤怒，生成试听音频。
2. 将这次试听返回的音频作为新的原始音频样本保存。
3. 用该个人形象生成正式视频。
4. 检查生成视频开头是否出现正文尾段的额外口播，且该口播没有对应字幕。

## 期望行为
正式视频的生成音频应只包含本次视频文案内容，不能把试听参考音频中的尾段文案插入到视频开头。

## 实际行为
修复前，正式视频开头可能先播放参考音频转写文本中的尾段，再播放正式视频文案，形成无字幕的重复口播。

## 原因
`router/service/video_server2/video_work.py` 中视频生成链路对参考音频的处理顺序不一致：

- `reference_text` 使用 Whisper 从原始/完整参考音频转写得到。
- 后续真正传给 VoxCPM 的 `reference_audio_url` 又经过转换/裁剪处理。
- 当参考音频本身是较长的试听生成音频时，`reference_text` 与实际传入 VoxCPM 的参考音频内容不完全对应，容易让 VoxCPM 把参考文本内容泄漏到生成口播里。

## 解决方案
- 调整 `video_work.py` 中参考音频处理顺序：先下载参考音频，再转换/裁剪，再上传处理后的参考音频。
- Whisper 转写和 VoxCPM 克隆统一使用同一个处理后音频 URL。
- 避免 Whisper 对原始长参考音频转写，而 VoxCPM 使用另一份处理后音频，导致 `reference_text` 和 `reference_audio_url` 不一致。
- 增加回归测试，约束 `reference_audio_convert` 必须发生在 `reference_audio_upload_for_whisper` / `reference_audio_whisper` 之前，并验证 Whisper 使用的是处理后上传 URL。

## 优化点
- 后续可在声音克隆请求日志中继续保留 `reference_text_len`、`reference_audio_url` 来源、处理后参考音频时长，方便排查类似问题。
- 对“试听音频作为原始样本”的链路保留独立回归用例，避免后续改动再次让参考文本和参考音频不一致。
- 本次复测里，之前的“开头多出正文尾段”已消失；但 ASR 仍检测到靠后有一句 `还支持先享后付` 的短句重复，这更像模型生成中的局部口播重复，不是同一个开头泄漏问题。

## 验证结果
- 本地回归测试：`python -m unittest test.test_production_baseline_alignment test.test_video_perf_logging test.test_scheduled_video_voice_params test.test_voice_speed_timeline_alignment test.test_voice_clone_upload test.test_voice_audition_pool_service test.test_voxcpm_voice_style_prompt`
- 结果：`Ran 76 tests in 0.766s`，`OK`
- 编译检查：`python -m py_compile router\service\video_server2\video_work.py test\test_production_baseline_alignment.py` 通过。
- 空白检查：`git diff --check` 通过。
- H20 复测任务判定：`duplicate_prefix_before_start=false`。

## H20 复测信息
- H20 release：`/data/project/test_ai_botserver.20260610165052`
- 复测素材记录：`t_video_generate_task.id=1375`
- 试听参数：`voice_emotion=8`，`voice_speed=1.0`，`voice_volume=50`
- 视频生成使用 `reference_sample` 默认参数：`voice_emotion=1`，`voice_speed=1.0`，`voice_volume=50`
- 试听音频：`https://videos-test.joyingai.cn/video/crm/20260610/user4_1781081981835_00d96d93eccd2f96.wav`
- 生成视频：`https://videos-test.joyingai.cn/video/crm/20260610/user4_1781082131348_02150714edcbfc21.mp4`
- 原视频：`https://files.joyingai.cn/crm/20260605/user4_1780637795609_4832260309e54bcb.mp4`
- H20 健康状态：`8100` / `8017` 返回 `{"status":"ok"}`，`8100` / `8017` / `18017` 均指向当前 release。
- 任务和模型池状态：无 `task_status IN (0,1,2)` 活跃视频任务，无 `is_active=2` 模型锁。

## 提交与合并
- Commit：`926dc204 fix: align voice reference transcription audio`
- 已推送：`origin/feature/ai_v6.3.1_video`
- 已合并并推送：`origin/test`
- 远端确认：`feature/ai_v6.3.1_video` 与 `test` 均指向 `926dc204513864bd3c33d8806a7cd08436e029ad`。

## 相关文件
- `router/service/video_server2/video_work.py`
- `test/test_production_baseline_alignment.py`
- `projects/joyingbot-new/changelog/2026-06-10_voice_audition_reference_sample.md`
