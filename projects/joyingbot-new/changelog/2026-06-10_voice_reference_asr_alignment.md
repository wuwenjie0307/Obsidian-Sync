---
date: "2026-06-10"
tags: [changelog, h20-test, voice-clone, video-generation]
---

# 2026-06-10 voice reference ASR alignment

## 改动类型

- [ ] 新功能
- [x] Bug 修复
- [ ] 重构
- [ ] 配置变更

## 改动内容

- 修复视频生成链路里参考音频转写与实际克隆音频不一致的问题。
- `video_work.py` 现在先对参考音频做下载、转换/裁剪、上传，再用同一个处理后音频 URL 同时给 Whisper 和 VoxCPM 使用。
- 避免“试听生成音频作为原始样本”时，Whisper 转写完整长参考音频，而 VoxCPM 使用处理后音频，导致参考文案泄漏到正式生成口播开头。
- 新增回归测试 `WhisperServiceAlignmentTest.test_video_work_transcribes_same_reference_audio_sent_to_clone`，锁定参考音频处理顺序和 Whisper 入参。
- 推送个人分支 `feature/ai_v6.3.1_video`，并合并到 `test`。
- 重启 H20 测试服服务并复测愤怒试听样本链路。

## 影响范围

- 视频生成中的声音克隆参考音频处理。
- 使用试听音频作为个人形象原始音色样本的链路。
- 不新增接口，不改前端参数，不改试听/视频生成的 API 结构。

## 验证结果

- 本地回归：`Ran 76 tests in 0.766s`，`OK`。
- `py_compile` 通过。
- `git diff --check` 通过。
- H20 release：`/data/project/test_ai_botserver.20260610165052`。
- H20 健康检查：`8100` / `8017` 均返回 `{"status":"ok"}`。
- H20 任务表：无活跃视频任务。
- H20 模型池：无 `is_active=2` 占用锁。
- 复测结论：之前的“视频开头多出参考音频尾段口播”未再出现，脚本判定 `duplicate_prefix_before_start=false`。

## 复测产物

- 试听音频：`https://videos-test.joyingai.cn/video/crm/20260610/user4_1781081981835_00d96d93eccd2f96.wav`
- 生成视频：`https://videos-test.joyingai.cn/video/crm/20260610/user4_1781082131348_02150714edcbfc21.mp4`
- 原视频：`https://files.joyingai.cn/crm/20260605/user4_1780637795609_4832260309e54bcb.mp4`

## 相关 Commit

- `926dc204 fix: align voice reference transcription audio`
