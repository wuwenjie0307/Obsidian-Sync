---
date: "2026-06-09"
tags: [changelog, h20, hyperframes, video, analysis]
---

# h20-hyperframes-structured-analysis-phase-2026-06-09

## 改动类型

- [x] 新功能
- [ ] Bug 修复
- [x] 重构
- [x] 配置变更

## 改动内容

完成 H20 HyperFrames / 网感视频后端阶段 04：结构化分析。

新增 `router/service/video_server2/hyperframes_analysis.py`：
- 构造 LLM 输入，包含 `job_id`、`task_id`、`template_id`、文案、Whisper 文本与句级 `subtitle_segments`。
- 解析 LLM JSON，schema 固定为 `cover_title`、`subtitle_keywords`、`action_candidates`、`fallback_flags`。
- 代码层裁剪封面标题，中文标题不超过 16 个字符。
- 每条字幕最多保留 1 个关键词，过滤虚词、无意义词和过短词。
- 动作时间轴全部绑定 Whisper `subtitle_segments`，LLM 不生成时间。
- 支持 `push_in` 和 `zoom_in`，Push 优先，动作不重叠，3 分钟内总数上限 12。
- 非法 JSON 或 schema 错误会抛出 `HyperFramesAnalysisError`，不会进入 render-ready 输出。

调度接入：
- `_prepare_hyperframes_video_task` 在 Whisper timeline 成功后调用 `build_hyperframes_analysis`。
- 写入 `task_record.analysis_path` 和 `task_record.analysis_ms`。
- 分析失败时返回 `STRUCTURED_ANALYSIS_FAILED`。
- 分析成功后仍返回 `HYPERFRAMES_ROUTE_NOT_READY`，等待阶段 05 CLI wrapper；本阶段不调用 Node CLI、不渲染、不上传、不回调。

持久化：
- `VideoGenerateTask` 增加 `analysis_path`、`analysis_ms`。
- 新增 SQL：`sql/h20_hyperframes_analysis.sql`。

Apidoc 核对：
- 本阶段不新增外部接口字段，不修改回调 payload。
- `crm` 项目 699/701 可读，创建入参仍包含 `templates_style_id`。
- 本次读取 712/713 返回“token有误”，后续回调/状态阶段需在 token 修复后复核。

## 影响范围

- `router/service/video_server2/hyperframes_analysis.py`
- `scheduler/collect_scheduler.py`
- `pojo/models.py`
- `sql/h20_hyperframes_analysis.sql`
- `test/test_hyperframes_analysis.py`

验证结果：
- `python -m unittest test.test_hyperframes_analysis -v` 通过。
- `python -m unittest test.test_whisper_timeline -v` 通过。
- `python -m unittest test.test_template_route -v` 通过。
- `python -m unittest test.test_scheduled_video_voice_params -v` 通过。
- `python -m unittest test.test_production_baseline_alignment -v` 通过。
- `python -m unittest test.test_video_model_busy_retry -v` 通过。
- `python -m unittest test.test_voice_speed_timeline_alignment -v` 通过。
- `python -m unittest test.test_voice_clone_upload -v` 通过。
- `python -m unittest test.test_audio_conversion_ffmpeg_binary -v` 通过。
- `python -m unittest test.test_montage_material_audio_policy -v` 通过。
- `python -m unittest test.test_video_material_montage_sync -v` 通过。
- `python -m py_compile router/service/video_server2/hyperframes_analysis.py router/service/video_server2/whisper_timeline.py router/service/video_server2/video_work.py scheduler/collect_scheduler.py pojo/models.py` 通过。
- `git diff --check` 通过，仅有工作区 LF/CRLF 提示。

遗留事项：
- 未在当前环境直连真实 LLM 与真实 8188 Whisper 样本跑端到端。
- 阶段 08 需要用中文/英文真实任务验收关键词、动作节奏、manifest 和渲染结果。
- `templatesStyleList` 完整 1/2/3 枚举、回调字段 `status` vs `task_status` 仍需联调确认。
