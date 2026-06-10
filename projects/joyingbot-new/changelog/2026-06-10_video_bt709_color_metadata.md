---
date: "2026-06-10"
tags: [project, changelog, h20-test, video-quality]
---

# 2026-06-10 video bt709 color metadata

## 改动类型
- Bug fix
- video pipeline

## 改动内容
- 新增 `router/service/video_server2/video_color.py`，用于探测视频颜色元数据，并在缺失时优先通过 H.264 bitstream copy 补齐 `bt709` / `tv` 标签，失败时降级为 `libx264 + crf 18` 重编码。
- 视频生成主流程在唇形模型输出后、9:16 标准化前新增 `bt709_color_fix` 阶段，避免 HeyGem/duix 输出丢失颜色标签后继续传递到最终视频。
- `video_server2` 中会重新编码视频的主要阶段统一显式写入 `-color_range tv -colorspace bt709 -color_trc bt709 -color_primaries bt709`，覆盖标准化、字幕烧录、封面合成、时长对齐、横转竖、图片转视频和叠加混剪。
- 未调整 `HDR_TO_SDR.py` 的 tone mapping 主观色彩参数，本次只做保守的颜色元数据保留修复。

## 影响范围
- `router/service/video_server2/video_work.py`
- `router/service/video_server2/video_color.py`
- `router/service/video_server2/video_format_keep.py`
- `router/service/video_server2/add_subtitle.py`
- `router/service/video_server2/video_cover.py`
- `router/service/video_server2/video_time_align.py`
- `router/service/video_server2/video_portrait_screen.py`
- `router/service/video_server2/video_select_overlay.py`
- `router/service/video_server2/Photo_video.py`
- `test/test_video_quality_pipeline.py`

## 验证结果
- RED：新增的 3 条视频颜色元数据回归测试先失败，失败点为缺少 `video_color.py`、主流程未调用颜色修复、重编码模块未声明 bt709 参数。
- GREEN：`python -m unittest test.test_video_quality_pipeline.VideoQualityPipelineSourceTest.test_bt709_color_helper_prefers_stream_copy_metadata_fix test.test_video_quality_pipeline.VideoQualityPipelineSourceTest.test_video_server2_repairs_lip_sync_color_metadata_before_standardize test.test_video_quality_pipeline.VideoQualityPipelineSourceTest.test_video_server2_reencode_commands_declare_bt709_output_metadata`，结果 `Ran 3 tests`，`OK`。
- `python -m unittest test.test_video_quality_pipeline`，结果 `Ran 12 tests`，`OK`。
- `python -m py_compile router\service\video_server2\video_color.py router\service\video_server2\video_work.py router\service\video_server2\video_format_keep.py router\service\video_server2\add_subtitle.py router\service\video_server2\video_cover.py router\service\video_server2\video_time_align.py router\service\video_server2\Photo_video.py router\service\video_server2\video_select_overlay.py router\service\video_server2\video_portrait_screen.py test\test_video_quality_pipeline.py`，退出码 0。
- `python -m unittest test.test_video_quality_pipeline test.test_voice_speed_timeline_alignment test.test_video_perf_logging test.test_bgm_volume_mix test.test_video_material_montage_sync test.test_montage_material_audio_policy test.test_production_baseline_alignment test.test_video_model_busy_retry test.test_heygem_timeout test.test_latentsync_timeout`，结果 `Ran 49 tests`，`OK`；仍有历史 `DeprecationWarning: invalid escape sequence '\s'`。

## 相关 Commit
- 待提交
