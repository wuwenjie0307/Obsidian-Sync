---
date: "2026-05-29"
tags: [changelog, h20, crm, video, voice-clone]
---

# h20 scheduled video voice params

## 改动类型

- [x] 新功能
- [x] Bug 修复
- [ ] 重构
- [x] 配置变更

## 改动内容

- 本地分支 `h20-scheduled-video-voice-params` 已提交并推送，提交为 `99694f14 fix: route video generation through scheduled flow`。
- 远端 `test` 已合并并推送，最新合并提交为 `687405a2 merge h20 scheduled video voice params into test`，未推送 `master`。
- `/crm/generate_video_task` 继续作为 CRM 视频任务入口，按 `job_id` 同步任务入库。
- 同步 task 时写入新增音色字段：`voice_emotion`、`voice_speed`、`voice_volume`。
- 新增校验范围：
  - `voice_emotion`: 1-8，默认 1
  - `voice_speed`: 仅允许 0.75、1.0、1.25、1.5、2.0、3.0，默认 1.0
  - `voice_volume`: 0-100，默认 50
- 调度链路 `scheduler.collect_scheduler._process_single_video_task` 调用 `video_work_Heygem_Whisper` 时传入三个音色参数。
- `/crm/submit_heygem_whisper_video_task` 已禁用，返回 HTTP 410，避免绕过旧调度链路直接开线程生成视频。
- h20 测试库 `t_video_generate_task` 已确认包含三个字段，并将旧的 `voice_emotion varchar(20) default 'normal'` 规范为 `INT DEFAULT 1`；历史 `normal` 值按 VoxCPM 等价关系归一为 `1`。
- h20 当前实际视频调度服务是 `ai_botserver_sch`，运行 `app_server_sch.py`，已在周期执行 `generate_video_and_callback`；`ai_botserver_sch_video` 仍为 stopped，且其 `JOBS` 当前为空，不是主调度入口。
- h20 外部入口 `223.112.222.90:48100` 映射到内部 `8100`。原 `8100` 是 `/data/projects/joyingbot-new` 旧手动进程，已切换为从 `/data/project/test_ai_botserver` 当前 Jenkins 部署目录启动的新代码进程。

## 影响范围

- CRM 视频主流程应继续调用：
  - `POST http://223.112.222.90:48100/crm/generate_video_task`
  - 请求只传 `job_id`，由 Bot 反查 CRM task 列表。
- CRM 音色试听接口保留：
  - `POST http://223.112.222.90:48100/crm/voice_clone_audition`
  - 可用于产品测试 `voice_emotion`、`voice_speed`、`voice_volume` 不同取值效果。
- 不再使用 `/crm/submit_heygem_whisper_video_task` 做主流程；该接口已返回 410。
- `223.112.222.90:48100` 当前由手动 nohup 方式运行 8100 新代码，不是 supervisor 管理；如果 h20 重启或进程退出，需要按记录重新拉起或后续补 supervisor 配置。

## 验证记录

- 本地验证：
  - `python -m py_compile router/crm_server.py scheduler/collect_scheduler.py pojo/models.py router/service/video_server2/voice_params.py`
  - `python -m unittest test.test_scheduled_video_voice_params test.test_voice_clone_upload`
  - `git diff --cached --check`
  - 合并到 `test` 后再次执行同样的 py_compile、定向 unittest、`git diff --check origin/test..HEAD`，均通过。
- h20 验证：
  - `/data/project/test_ai_botserver` 已部署到 `/data/project/test_ai_botserver.20260529193010`。
  - `ai_botserver` 运行在 8017。
  - `ai_botserver_sch` 运行中，并执行 `generate_video_and_callback`。
  - VoxCPM `127.0.0.1:8110/health` 返回 ok。
  - LatentSync `127.0.0.1:8101/health` 返回 ok。
  - 新 8100 进程工作目录为 `/data/project/test_ai_botserver.20260529193010`。
- 外部入口验证（从跳板机访问公网入口）：
  - `GET http://223.112.222.90:48100/status/check` 返回 HTTP 200，body 为 `{"status":"ok"}`。
  - `POST http://223.112.222.90:48100/crm/submit_heygem_whisper_video_task` 返回 HTTP 410。
  - `POST http://223.112.222.90:48100/crm/generate_video_task` 空参数返回 HTTP 400，提示 `job_id 不能为空`。
  - `POST http://223.112.222.90:48100/crm/voice_clone_audition` 空参数返回 HTTP 400，提示 `voice_file_url 不能为空`。
  - `voice_speed=0.5` 返回 HTTP 400，提示仅允许 `[0.75, 1.0, 1.25, 1.5, 2.0, 3.0]`。

## 相关 Commit

- `99694f14 fix: route video generation through scheduled flow`
- `687405a2 merge h20 scheduled video voice params into test`
