---
date: "2026-06-01"
status: fixed
severity: high
tags: [bug, h20, video-generation, scheduler, db-session]
---

# h20 视频任务生成成功但本地状态和资源锁卡住

## 问题描述

2026-06-01 17:43 左右提交的视频任务 `job_id=1006 / task_id=997 / id=1209`，产品侧反馈前端长时间显示生成中。

排查后确认视频实际已在 h20 生成成功并回调 CRM 成功，但 Bot 本地测试库没有保存最终状态，`t_comfyui_config.id=1` 也没有释放。

## 复现步骤

1. CRM 创建视频任务并触发 `/crm/generate_video_task`。
2. 调度服务 `ai_botserver_sch` 领取 `t_comfyui_config.id=1`。
3. VoxCPM、LatentSync、字幕、BGM、封面和上传都成功。
4. 生成链路中的阶段状态回调出现 DB session 异常后，最终本地状态保存和锁释放受影响。

## 期望行为

- 视频生成成功后，本地 `t_video_generate_task` 应更新为 `task_status=3`、`progress=100`，并保存最终视频 URL。
- CRM 最终回调成功后，`callback_status=1`。
- 无论任务成功或失败，`t_comfyui_config.id=1` 都必须释放为 `is_active=1`。

## 实际行为

- 日志显示最终视频已生成并回调 CRM 成功：
  - `task_status=7`
  - `progress=100`
  - CRM 回调响应 `code=200`
- 但测试库仍停留在：
  - `t_video_generate_task.id=1209 task_status=2 progress=0 generate_video_url=''`
  - `t_comfyui_config.id=1 is_active=2`
- 日志关键错误：
  - `MySQL Connection not available`
  - `Can't reconnect until invalid transaction is rolled back`

## 环境信息

- 分支: `test`
- h20 部署目录: `/data/project/test_ai_botserver.20260601183331`
- 调度进程: `ai_botserver_sch`
- 相关任务: `job_id=1006 / task_id=997`

## 原因

视频生成过程中的阶段状态回调会调用 CRM 侧状态接口。该回调过程中 DB session 进入异常事务状态后，后续本地最终状态保存仍复用同一个 session，导致普通 `commit()` 失败。

同时，释放 `t_comfyui_config` 时原逻辑在 `finally` 中读取 ORM 对象 `config_model.id`。如果 session 已经处于异常状态，读取 ORM 对象属性也可能失败，导致真正的 `_release_comfyui_config(...)` 没有执行。

## 修复方案

- 人工修正测试库已完成任务：
  - `t_video_generate_task.id=1209` 更新为成功，写入最终视频 URL。
  - `t_comfyui_config.id=1` 释放为 `is_active=1`。
- 代码修复：
  - 新增 `_rollback_session_safely(...)`，在关键保存/释放前清理异常事务状态。
  - 新增 `_save_video_task_final_state(...)`，普通 `commit()` 失败时，先 `rollback()`，再按任务主键直接 `update(...)` 保存最终状态。
  - `_process_single_video_task_with_config(...)` 预先保存 `config_id_to_release`，避免 `finally` 里依赖已污染的 ORM 对象读取 `config_model.id`。
  - 视频生成返回后先清理 session 并重新加载任务记录，再写最终状态。

## 验证结果

- 本地测试：
  - `python -m unittest test.test_production_baseline_alignment`
  - `python -m unittest test.test_scheduled_video_voice_params test.test_voice_clone_upload test.test_production_baseline_alignment`
  - `python -m py_compile scheduler/collect_scheduler.py`
  - `git diff --check`
- h20 验证：
  - `ai_botserver` 运行正常。
  - `ai_botserver_sch` 已重启并加载新目录 `/data/project/test_ai_botserver.20260601183331`。
  - `8017/status/check`、`8100/status/check`、`8110/health`、`8101/health` 均返回 `{"status":"ok"}`。
  - 测试库确认 `t_video_generate_task.id=1209 task_status=3 progress=100 callback_status=1`。
  - 测试库确认 `t_comfyui_config.id=1 is_active=1`。

## 相关文件

- `scheduler/collect_scheduler.py`
- `test/test_production_baseline_alignment.py`

## 相关 Commit

- `238a2f96 fix: persist scheduled video completion state`
