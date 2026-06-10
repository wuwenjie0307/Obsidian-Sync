---
tags: [changelog, h20, hyperframes]
---

# h20-hyperframes-upload-callback-phase-2026-06-10

## 改动类型
- [x] 新功能
- [ ] Bug 修复
- [ ] 重构
- [ ] 配置变更

## 改动内容
- 完成 H20 HyperFrames Phase 07：渲染成功后上传 HyperFrames `final_video_path` 和 `cover_path`，保存 `hf_final_video_url`、`hf_cover_url`，并同步写入原有 `generate_video_url`、`cover_image_url`。
- 调整 `_process_single_video_task` 的网感分支：`route_result.success=True` 时进入原成功状态链路，设置 `task_status=3`、`progress=100`，让原统一完成回调发送成功；失败时保留 `fail_reason` 并走原失败回调。
- 新增 `sql/h20_hyperframes_upload_callback.sql`，为 `t_video_generate_task` 增加最终上传 URL 字段。
- 新增 `test/test_hyperframes_upload_callback.py` 并同步更新 Phase 04/05/01 相关源测试，把旧的 `HYPERFRAMES_UPLOAD_NOT_READY` 护栏替换为 Phase 07 上传护栏。

## 影响范围
- 影响 `templates_style_id=1/2` 的 HyperFrames 路线；`minimal` 旧路线不改。
- HyperFrames 成功后不再停在上传未就绪，而是上传 final/cover 后进入原成功回调链路。
- HyperFrames 渲染失败、上传失败、路线冲突仍不会上传裸 HeyGem 视频，也不会回退 minimal。
- Callback payload 暂不新增模板字段；apidoc 当前 fetch failed，回调字段继续沿用生产代码 `task_status`。

## 验证
- TDD 红灯：新增/更新测试后，`python -m unittest test.test_hyperframes_upload_callback test.test_hyperframes_cli test.test_hyperframes_analysis test.test_template_route -v` 初次失败 7 项，失败点符合 Phase 07 未实现状态。
- 目标测试：同一命令实现后 50 项通过。
- 回归测试：`python -m unittest test.test_hyperframes_postprocess test.test_whisper_timeline test.test_scheduled_video_voice_params test.test_production_baseline_alignment test.test_hyperframes_upload_callback test.test_hyperframes_cli test.test_hyperframes_analysis test.test_template_route -v` 87 项通过。
- 语法检查：`python -m py_compile scheduler/collect_scheduler.py pojo/models.py` 通过。

## 遗留
- 需要 Phase 08 在 H20 环境跑真实或高保真模拟任务，验证 CRM 上传 final/cover、成功/失败回调、上传失败任务状态、锁释放与实际 URL 可访问性。
- apidoc 当前项目/分类/接口读取均 `fetch failed`，`status/task_status` 仍需联调确认。
