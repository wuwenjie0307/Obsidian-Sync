---
date: "2026-06-09"
tags: [changelog, bugfix, h20, montage, audio, ffmpeg]
---

# H20 混剪插入视频原声混音

## 改动类型

- [ ] 新功能
- [x] Bug 修复
- [ ] 重构
- [ ] 配置变更

## 改动内容

针对“混剪视频插入的时候没声音”，后端增加普通混剪视频素材原声混音：

- `video_work.py` 在混剪视频素材下载后，记录普通混剪素材的原始文件路径到 `montage_audio_dict`。
- `video_work.py` 在最终 overlay 前，基于实际参与叠加的路径构建 `overlay_audio_dict` 并传给 `overlay_videos_with_timing()`。
- `video_select_overlay.py` 新增可选 `overlay_audio_dict` / `overlay_audio_volume` 参数。
- overlay 阶段对素材原声音轨执行 `atrim + apad + adelay + volume`，按字幕命中的时间段低音量混入主视频音轨。
- 默认无素材音频时保留旧行为：只叠加画面，并复制主视频音轨。
- 口型同步素材不混入原始素材音频，避免与主口播冲突。

## 影响范围

- 影响 H20 `video_server2` 混剪视频素材叠加链路。
- 不影响图片混剪素材。
- 不修改数据库结构，不修改 CRM 参数协议。
- 需要 H20 真实混剪任务进一步验证最终听感和音量。

## 验证

```text
python -m unittest test.test_montage_overlay_audio_mix
Ran 2 tests OK
```

```text
python -m py_compile router\service\video_server2\video_select_overlay.py router\service\video_server2\video_work.py
exit 0
```

```text
python -m unittest test.test_scheduled_video_voice_params test.test_montage_overlay_audio_mix test.test_video_material_montage_sync test.test_voxcpm_voice_style_prompt test.test_voice_clone_upload test.test_production_baseline_alignment
Ran 49 tests OK
```

说明：本地 Windows PATH 没有 `ffmpeg`，媒体级烟测未在本机跑成；后续应在 H20 环境跑真实任务验收。

## 相关记录

- [[projects/joying-bot-server/bugs/h20-montage-insert-audio-muted-2026-06-09|H20 混剪插入视频原声被静音]]
- [[projects/joying-bot-server/docs/h20-montage-voice-speed-status-2026-06-09|H20 混剪倍速与插入音频当前状态]]

## 2026-06-09 口径撤回

根据最新确认，如果原链路本来就是静音混剪素材，本轮也继续静音素材。因此本 changelog 记录的“普通混剪素材原声混入主音轨”方案已撤回，代码已回到只保留主视频音轨、不混素材原声的策略。

当前有效口径见：[[projects/joying-bot-server/changelog/h20-montage-material-audio-muted-policy-2026-06-09|H20 混剪素材继续静音口径]]。
