---
date: "2026-06-09"
tags: [changelog, h20, montage, audio, policy]
---

# H20 混剪素材继续静音口径

## 改动类型

- [ ] 新功能
- [x] Bug 修复
- [ ] 重构
- [x] 配置变更

## 改动内容

根据最新口径确认：如果旧链路本来就静音混剪素材，本轮继续静音素材，不把插入素材自己的原声混进最终视频。

本次调整：

- 撤回 `video_select_overlay.py` 中新增的 `overlay_audio_dict` / `overlay_audio_volume` 混音接口。
- 撤回 `video_work.py` 中的 `montage_audio_dict` 和素材原始音频源传递逻辑。
- 删除“素材原声混入”回归测试。
- 新增 `test/test_montage_material_audio_policy.py`，明确策略：混剪素材继续静音，overlay 只保留主视频音轨。

## 影响范围

- 混剪视频素材继续只用画面，不使用素材自身声音。
- 最终视频仍应保留主视频口播音轨。
- 如果后续出现“插入片段期间主口播也没声音”，需要按音轨丢失 bug 单独排查。

## 验证

```text
python -m unittest test.test_montage_material_audio_policy
Ran 2 tests OK
```

```text
python -m py_compile router\service\video_server2\video_select_overlay.py router\service\video_server2\video_work.py
exit 0
```

```text
python -m unittest test.test_scheduled_video_voice_params test.test_montage_material_audio_policy test.test_video_material_montage_sync test.test_voxcpm_voice_style_prompt test.test_voice_clone_upload test.test_production_baseline_alignment
Ran 49 tests OK
```

## 相关记录

- [[projects/joying-bot-server/docs/h20-montage-voice-speed-status-2026-06-09|H20 混剪倍速与插入音频当前状态]]
- [[projects/joying-bot-server/bugs/h20-montage-insert-audio-muted-2026-06-09|H20 混剪插入视频原声被静音]]
- [[projects/joying-bot-server/changelog/h20-montage-insert-audio-mix-2026-06-09|已撤回：H20 混剪插入视频原声混音]]
