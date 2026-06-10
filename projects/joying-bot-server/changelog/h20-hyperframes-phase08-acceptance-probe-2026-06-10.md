---
tags: [changelog, h20, hyperframes, acceptance]
---

# h20-hyperframes-phase08-acceptance-probe-2026-06-10

## 改动类型
- [ ] 新功能
- [ ] Bug 修复
- [ ] 重构
- [ ] 配置变更
- [x] 验收记录

## 改动内容
- 启动 Phase 08 测试与验收，梳理 T54-T64。
- 本地单元/集成验收已覆盖 T54-T58，并完成 87 项回归测试。
- 已进入 H20 测试机做只读探测：`8100`、`8017` 健康检查均返回 ok；`8017/18017` live cwd 为 `/data/project/test_ai_botserver.20260609233154`，`8100` live cwd 为 `/data/project/test_ai_botserver.20260609180518`。
- 探测发现 H20 live cwd 尚未包含本地 Phase 06/07 代码：未找到 `hyperframes-postprocess`，也未找到 `hf_final_video_url`、`HYPERFRAMES_UPLOAD_FAILED` 等 Phase 07 marker。

## 影响范围
- Phase 08 暂不能标记完成。现在跑真实任务会验证 H20 当前旧部署，而不是本地 `feature/h20-hyperframes-postprocess-dev` 工作区的新实现。
- 下一步应先部署/同步当前分支到 H20 测试服务，再执行 `science_guide`、`video_diary`、`minimal` 三条真实任务验收和 ffprobe/抽帧质量检查。
- 未记录、未保存任何 SSH 密码。

## 验证
- `python -m unittest test.test_hyperframes_postprocess test.test_whisper_timeline test.test_scheduled_video_voice_params test.test_production_baseline_alignment test.test_hyperframes_upload_callback test.test_hyperframes_cli test.test_hyperframes_analysis test.test_template_route -v`：87 项通过。
- `python -m py_compile scheduler/collect_scheduler.py pojo/models.py router/service/video_server2/hyperframes_cli.py router/service/video_server2/hyperframes_analysis.py router/service/video_server2/whisper_timeline.py router/service/video_server2/video_work.py`：通过。
- `node --check hyperframes-postprocess\index.js`：通过。
- `git diff --check`：退出 0，仅有 LF/CRLF 提示。

## 遗留
- 部署当前工作区到 H20 测试服务。
- 应用 Phase 01-07 SQL migration，至少包含 `sql/h20_hyperframes_upload_callback.sql`。
- 跑 T59-T64：中文 science guide、中文 video diary、minimal 旧路线、英文 smoke、ffprobe、人工抽帧。
