---
date: "2026-06-09"
tags: [changelog, h20, hyperframes, video, cli]
---

# h20-hyperframes-cli-wrapper-phase-2026-06-09

## 改动类型

- [x] 新功能
- [ ] Bug 修复
- [x] 重构
- [x] 配置变更

## 改动内容

完成 H20 HyperFrames / 网感视频后端阶段 05：HyperFrames CLI wrapper。

新增 `router/service/video_server2/hyperframes_cli.py`：
- 构造并校验 Phase 05 manifest 必填字段：`job_id`、`task_id`、`templates_style_id`、`template_id`、`lip_sync_video_path`、`personal_video_path`、`script_text`、`whisper_timeline_path`、`analysis_path`、`output_dir`、`render_width=1080`、`render_height=1920`、`fps=30`。
- 支持可选字段：`bgm_path`、`cover_title`、`debug`。
- 写入 `manifest.json`。
- 调用 `node hyperframes-postprocess/index.js --input manifest.json --output result.json`。
- 解析 `result.json` 的 `success/final_video_path/cover_path/subtitle_timeline_path/render_ms/error`。
- 将 manifest 缺字段、CLI 超时、CLI 非 0 退出、result 缺失/非法转换为明确 `HyperFramesCliError`。
- 新增 `HyperFramesRenderLock`，默认按 `HF_MAX_CONCURRENCY=1` 保护 HyperFrames 渲染并发，并覆盖成功、失败、等待超时释放行为。

调度接入：
- `_prepare_hyperframes_video_task` 在结构化分析成功后调用 `render_hyperframes_video`。
- 写入 `hf_manifest_path`、`hf_result_path`、`hf_final_video_path`、`hf_cover_path`、`hf_subtitle_timeline_path`、`hf_render_ms`。
- CLI 运行异常返回 `HYPERFRAMES_CLI_FAILED`。
- result 失败返回 `HYPERFRAMES_RENDER_FAILED`。
- result 成功后仍返回 `HYPERFRAMES_UPLOAD_NOT_READY`，等待阶段 07 上传和回调；本阶段不上传、不回调、不回退 minimal。

持久化：
- `VideoGenerateTask` 增加本地 CLI 产物字段。
- 新增 SQL：`sql/h20_hyperframes_cli.sql`。

Apidoc 核对：
- 本阶段不新增 CRM/CSM 外部接口字段，不修改回调 payload。

## 影响范围

- `router/service/video_server2/hyperframes_cli.py`
- `scheduler/collect_scheduler.py`
- `pojo/models.py`
- `sql/h20_hyperframes_cli.sql`
- `test/test_hyperframes_cli.py`
- `test/test_hyperframes_analysis.py`
- `test/test_template_route.py`

验证结果：
- `python -m unittest test.test_hyperframes_cli -v` 通过。
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
- `python -m py_compile router/service/video_server2/hyperframes_cli.py router/service/video_server2/hyperframes_analysis.py router/service/video_server2/whisper_timeline.py router/service/video_server2/video_work.py scheduler/collect_scheduler.py pojo/models.py` 通过。
- `git diff --check` 通过，仅有工作区 LF/CRLF 提示。

遗留事项：
- 本轮未执行真实 Node/Chromium/HyperFrames 渲染，只用 fake runner 验证 Python wrapper 的命令、result、错误和锁行为。
- 当前 backend 工作区尚未包含可执行的 `hyperframes-postprocess/index.js` 模板实现。
- 阶段 06 需要落地模板视觉和 Node postprocess；阶段 08 需要在 H20 环境验证 Node、Chromium、FFmpeg。
- 上传、最终 URL、封面 URL 和成功回调仍属阶段 07。
