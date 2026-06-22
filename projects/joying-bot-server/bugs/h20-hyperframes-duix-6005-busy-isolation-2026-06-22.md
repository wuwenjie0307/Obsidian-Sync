---
date: "2026-06-22"
project: "joying-bot-server"
type: bug
status: investigation
severity: high
tags: [bug, h20, hyperframes, video-generation, duix, heygem, model-pool, scheduler]
aliases: ["H20 HyperFrames 6005 busy 被误判失败"]
---

# H20 HyperFrames 6005 busy 被误判失败

## 图谱链接

- 项目: [[projects/joying-bot-server/00-项目概览|joying-bot-server]]
- 索引: [[projects/joying-bot-server/bugs/00-bugs-index|Bug 记录索引]]
- 相关历史: [[projects/joying-bot-server/bugs/prod-6014-busy-task-8405-2026-06-04|prod-6014-busy-task-8405-2026-06-04]]
- 相关历史: [[projects/joyingbot-new/bugs/2026-06-11_h20_duix_6004_task_1174_stuck|H20 1174 卡在 duix 6004 20%]]

## 问题描述

2026-06-22 测试服网感视频链路出现多条任务失败。用户最初提到 `task_id=1316`、`task_id=1317`，只读查询后判断这两条不是本次失败样本；实际失败集中在后续任务，例如 `task_id=1324`、`1325`、`1326`。

失败记录表现为：

```text
fail_reason=HEYGEM_STANDARDIZE_FAILED: 视频合成阶段失败
whisper_timeline_path 为空
analysis_path 为空
hf_manifest_path 为空
hf_final_video_url 为空
```

这些字段说明失败发生在 HyperFrames 后处理之前，也就是 HeyGem / DuiX 标准化口播视频阶段。

## 现场证据

只读排查得到的关键现象：

- 失败任务路由到了 `config_id=17`。
- `config_id=17` 对应视频实例端口为 `6005`。
- `6005` 的 `/easy/submit` 返回过 `code=10001`、`msg=忙碌中`。
- H20 侧 `t_comfyui_config.is_active` 只是调度锁：`1=可分配`、`2=使用中`、`0=下线/不可用`。
- 现有释放逻辑在任务成功或失败后都会把使用中的配置从 `is_active=2` 放回 `1`，但这不代表 DuiX 容器内部任务状态已清理。
- 新任务在 6005 容器恢复后可以成功，说明 science_guide / video_diary / HyperFrames 链路本身不是整体不可用。

## 根因判断

这是两层问题叠加：

1. 底层触发原因：DuiX / HeyGem 容器内部状态卡住或仍处于 busy，导致后续 `/easy/submit` 返回 `code=10001 忙碌中`。
2. 上层处理缺陷：H20 HyperFrames 前置阶段没有把 busy 识别为模型实例状态问题，而是经 `StagePublicError` 包装成 `视频合成阶段失败`，再被调度层记录为 `HEYGEM_STANDARDIZE_FAILED`，最终把业务任务置为终态失败并回调 CRM。

因此，不能只把任务静默改回待生成。否则前端从“失败”变成“一直生成中”，反而削弱排查信号。正确做法应该同时保护任务和隔离疑似异常实例。

## 解决方案

本地功能分支计划采用最小复用方案：

1. 复用现有 `t_comfyui_config.is_active=0` 作为实例隔离状态，不新增数据库字段。
2. `/easy/submit` 返回 `code=10001`、`忙碌`、`busy` 时，抛出可识别的 `VideoGenBusyError`。
3. `StagePublicError` 保留 `original_error` 和异常链，避免 busy / timeout 被阶段公开错误吞掉。
4. HyperFrames HeyGem 标准化阶段识别 busy 后，不把任务置为终态失败。
5. 对应 `config_id` 标记为 `is_active=0`，避免下轮继续分配疑似卡住实例。
6. 当前任务置回待生成或等待重试，并写入明确 `fail_reason`，例如：`MODEL_INSTANCE_BUSY: config_id=17 返回忙碌，已隔离实例，任务等待其他实例重试`。
7. 不进行失败完成回调，避免 CRM 收到非业务失败。
8. 日志必须显式记录 `job_id`、`task_id`、`config_id`、实例 URL、busy 响应，方便继续追查容器根因。

## 后续排查计划

代码修复不等于解释容器为什么卡。后续仍需只读追查：

1. 找到首次让 `6005` 进入 busy / 卡住状态的任务，而不只看后续失败任务。
2. 对齐 `t_video_generate_task.updated_time`、H20 scheduler 日志、`duix-avatar-h20-test-6005` 容器日志。
3. 判断容器是真在运行旧任务，还是内部状态假 busy。
4. 检查是否存在进程残留、GPU 显存占用、`/easy/query` 进度长期不变、结果文件为空等信号。
5. 若确认实例异常，需要运维确认后再重启容器或清理内部任务状态；不要在排查阶段直接改测试服。

## 相关文件

- `router/service/video_server/video_gen_service.py`
- `router/service/video_server2/video_gen_service.py`
- `router/service/video_server2/video_work.py`
- `scheduler/collect_scheduler.py`
- `pojo/models.py`
- `test/test_video_model_busy_retry.py`

## 当前状态

- 已完成只读现场判断。
- 已确认不直接在测试服改代码、写库、部署或重启。
- 本地功能分支已有初版 busy retry 补丁，但需要调整为“busy 不终态失败 + 隔离疑似卡住实例 + 显式留证”，避免静默无限重试。
