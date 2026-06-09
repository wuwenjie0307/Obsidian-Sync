---
date: "2026-06-09"
tags: [changelog, h20, hyperframes, video, whisper]
---

# h20-hyperframes-routing-whisper-phases-2026-06-09

## 改动类型

- [x] 新功能
- [ ] Bug 修复
- [x] 重构
- [x] 配置变更

## 改动内容

H20 HyperFrames / 网感视频后端开发已完成阶段 01-03，并同步记录到 `C:\Users\admin\Desktop\h20-hyperframes-development-order\TODO.md` 与 `DONE.md`。

阶段 01 模板字段与路线分流：
- 新增 `t_video_generate_task.templates_style_id`，默认 `3=minimal`。
- 新增 `router/service/video_server2/template_route.py`，固定映射 `1=science_guide`、`2=video_diary`、`3=minimal`。
- `science_guide/video_diary` 会跳过旧混剪、旧 ASS、旧封面、旧 BGM 路线，不回退 minimal。
- `minimal` 旧路线保持兼容。

阶段 02 任务同步与调度接入：
- CSM Task 同步优先读取 `templates_style_id`。
- Task 缺失或非法时支持合法 Job fallback；Task/Job 都无合法值时默认 `3=minimal`。
- 本地任务已进入生成中或终态时保护既有模板字段，避免后续同步改路由。
- `/crm/generate_video_task` 与 scheduler 同步入口使用同一套模板字段选择逻辑。

阶段 03 Whisper 打轴：
- 新增 `router/service/video_server2/whisper_timeline.py`。
- 从 HeyGem 标准化视频抽取 16kHz 单声道 WAV，上传为 Whisper `audio_url`。
- 调用 8188 Whisper，固定 `word_timestamps=True`，校验词级 `start/end`。
- 保存 `whisper_timeline.json`，包含 `text`、`segments`、`words`、`subtitle_segments`。
- `video_work_Heygem_Whisper` 增加 `return_standardized_result` 受控出口，默认旧路线不变；网感路线可只跑到 HeyGem 标准化产物，不进入旧 ASS/混剪/BGM/封面。
- 网感准备函数先生成 HeyGem 标准化视频，再生成 Whisper timeline；失败时明确 `HEYGEM_STANDARDIZE_FAILED` 或 `WHISPER_TIMELINE_FAILED`，成功打轴后仍以 `HYPERFRAMES_ROUTE_NOT_READY` 停在渲染前，等待阶段 04/05。

Apidoc 核对结果：
- CSM `/csm/agent/pc/video/generateTaskList` 当前响应样例包含 `templates_style_id`，V1 以 Task 字段为主。
- CSM `/csm/agent/pc/video/generateJobList` 样例未展示 `templates_style_id`，代码仅作为合法 Job fallback 兼容。
- CRM `/crm/agent/pc/video/generateJobBatchCreate` 与 `/crm/agent/pc/video/generateJobUserCreate` 当前样例均包含 `templates_style_id`。
- CRM `/crm/agent/pc/video/templatesStyleList` 当前只展示 `id=1 科普指南`，完整 `1/2/3` 枚举仍需 CRM/CSM 或前端确认。
- CSM `/csm/agent/pc/video/generateTaskCallback` 文档样例使用 `status`，但 H20 现有代码透传 `task_status`，本轮未改回调字段。

## 影响范围

- `pojo/models.py`
- `scheduler/collect_scheduler.py`
- `router/crm_server.py`
- `router/service/video_server2/template_route.py`
- `router/service/video_server2/whisper_timeline.py`
- `router/service/video_server2/video_work.py`
- `sql/h20_hyperframes_template_routing.sql`
- `sql/h20_hyperframes_whisper_timeline.sql`
- `test/test_template_route.py`
- `test/test_whisper_timeline.py`

验证结果：
- 阶段测试与相关回归均通过，包括 `test_template_route`、`test_whisper_timeline`、`test_scheduled_video_voice_params`、`test_production_baseline_alignment`、`test_video_model_busy_retry`、`test_voice_speed_timeline_alignment`、`test_voice_clone_upload`、`test_audio_conversion_ffmpeg_binary`、`test_montage_material_audio_policy`、`test_video_material_montage_sync`。
- `py_compile` 通过。
- `git diff --check` 通过，仅有 LF/CRLF 提示。
- 全量 `python -m unittest discover -s test -p test_*.py` 当前仍有 4 个前置导入错误：缺 `pytest`，以及 unittest discovery 下 `common` 包名冲突；这是既有基线阻塞。

遗留事项：
- 未在当前环境直连 8188 跑中文/英文真实音频样本，阶段 08 真实任务验收需补跑。
- `templatesStyleList` 完整枚举仍需确认。
- `status` vs `task_status` 回调字段仍需联调确认。
- 下一阶段进入 04 结构化分析：基于任务 ID、模板 ID、文案、Whisper 文本和句级片段生成结构化 JSON。

## 相关 Commit

- 尚未提交；当前工作区在 `feature/h20-hyperframes-postprocess-dev` 上保留未提交改动。
