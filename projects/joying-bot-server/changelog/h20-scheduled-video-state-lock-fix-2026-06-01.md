---
date: "2026-06-01"
tags: [changelog, h20, video-generation, scheduler]
---

# h20 视频调度最终状态和锁释放修复

## 改动类型

- [x] Bug 修复
- [ ] 新功能
- [ ] 重构
- [x] 配置变更

## 改动内容

- 修正测试库任务 `job_id=1006 / task_id=997 / id=1209`：
  - 本地任务状态更新为成功。
  - 写入最终视频 URL。
  - 释放 `t_comfyui_config.id=1` 为可用。
- 修复调度代码：
  - 最终状态保存增加 rollback + 直接 update 兜底。
  - 释放配置时使用预保存的 `config_id_to_release`，不再依赖异常 session 下的 ORM 对象属性读取。
  - 视频生成结束后清理 session 并重新加载任务记录。
- 同步 `router/service/video_server/latentsync_api.py` 中 `guidance_scale=1.7` 到 GitLab `test`。
- 推送 GitLab `test` 分支后，Jenkins 已部署到 `/data/project/test_ai_botserver.20260601183331`。
- 已重启 `ai_botserver_sch`，当前调度进程工作目录为新部署目录。

## 影响范围

- h20 测试服视频生成调度链路。
- 影响 `/crm/generate_video_task` 入库后的定时调度生成流程。
- 不影响生产服。
- 不涉及 `master` 分支。

## 验证结果

- 本地：
  - `python -m unittest test.test_production_baseline_alignment`
  - `python -m unittest test.test_scheduled_video_voice_params test.test_voice_clone_upload test.test_production_baseline_alignment`
  - `python -m py_compile scheduler/collect_scheduler.py`
  - `git diff --check`
- h20：
  - `ai_botserver` RUNNING。
  - `ai_botserver_sch` RUNNING，PID 已更新。
  - `127.0.0.1:8017/status/check` 返回 `{"status":"ok"}`。
  - `127.0.0.1:8100/status/check` 返回 `{"status":"ok"}`。
  - `127.0.0.1:8110/health` 返回 `{"status":"ok"}`。
  - `127.0.0.1:8101/health` 返回 `{"status":"ok"}`。
  - `t_video_generate_task.id=1209` 已成功落库。
  - `t_comfyui_config.id=1 is_active=1`。

## 相关 Commit

- `238a2f96 fix: persist scheduled video completion state`
