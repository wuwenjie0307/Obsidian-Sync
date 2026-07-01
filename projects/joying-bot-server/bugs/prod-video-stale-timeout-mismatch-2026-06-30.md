---
date: "2026-06-30"
project: "joying-bot-server"
type: bug
status: fixed-in-code
severity: high
tags: [bug, prod, video, scheduler, timeout, model-pool]
---

# 正式服唇形模型池 stale 保护仍为 2100 秒

## 问题描述

正式服告警显示：

`VIDEO_PROCESSING_STALE_TIMEOUT: task stuck in processing for more than 2100s`

对应 `config_id=29`，唇形地址为 `http://192.192.168.139:6013`。该模型池配置被自动标记为不可用。

## 原因

此前只把两个视频模型调用入口的 `DEFAULT_HEYGEM_TIMEOUT_SECONDS` 改为 `7200` 秒，但 scheduler 外层卡死保护仍保留：

`STALE_VIDEO_PROCESSING_SECONDS = 35 * 60`

因此当模型池 `t_comfyui_config.is_active=2` 超过 2100 秒未释放时，scheduler 会先触发外层 stale 保护并隔离模型池，即使模型内部调用还允许继续等待到 7200 秒。

## 解决方案

代码已补充本地 hotfix 提交：

`e27c6aa8 fix: align scheduler stale timeout with video model timeout`

改动：

- `scheduler/collect_scheduler.py`
  - `STALE_VIDEO_PROCESSING_SECONDS = 2 * 60 * 60`
- `test/test_video_model_busy_retry.py`
  - 新增回归测试，确保 scheduler stale timeout 与模型调用 timeout 同为 7200 秒。

## 验证

已执行：

`python -m unittest test.test_video_time_align_orientation test.test_video_model_busy_retry`

结果：

`Ran 18 tests in 2.198s`

`OK`

## 线上处理

`config_id=29` 对应服务健康检查通过：

- VoxCPM `http://192.192.168.47:8117/health` 返回 `{"status":"ok"}`
- 唇形 `http://192.192.168.139:6013/easy/query` 返回正常接口响应
- `task_id=17932` 已成功生成视频

已将正式库 `t_comfyui_config.id=29` 从 `is_active=0` 恢复为 `is_active=1`。

## 后续

需要在能访问内网 GitLab 时推送本地 hotfix 分支，并合入 `master` 后再部署 LLM76 scheduler。
