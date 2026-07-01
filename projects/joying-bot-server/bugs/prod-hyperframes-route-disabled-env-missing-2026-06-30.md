---
date: "2026-06-30"
project: "joying-bot-server"
type: bug
status: fixed
severity: high
tags: [bug, prod, hyperframes, scheduler, env]
aliases: ["正式服 HYPERFRAMES_ROUTE_DISABLED"]
---

# 正式服 HYPERFRAMES_ROUTE_DISABLED

## 问题描述

正式库视频任务失败，前端显示：

`HYPERFRAMES_ROUTE_DISABLED: templates_style_id=2 template_id=video_diary; set H20_HYPERFRAMES_ROUTE_ENABLED=1 after DB migrations and runtime readiness`

## 复现步骤

1. 正式库创建 `templates_style_id=2` 的网感视频任务。
2. LLM-76 的 `ai_botserver_sch` 领取任务。
3. scheduler 解析到 `template_id=video_diary`，路由为 `hyperframes`。
4. 进程环境缺少 `H20_HYPERFRAMES_ROUTE_ENABLED=1`，任务被主动标记失败并回调 CRM。

## 期望行为

正式环境 DB migration、Docker runner、模型池等准备完成后，HyperFrames 路由任务应进入 Docker runner 渲染流程。

## 实际行为

LLM-76 scheduler 在进入生成前拦截任务，并将任务失败原因写为 `HYPERFRAMES_ROUTE_DISABLED`。

## 原因

代码中 `templates_style_id=1` 和 `templates_style_id=2` 会进入 HyperFrames 路由；该路由受环境变量 `H20_HYPERFRAMES_ROUTE_ENABLED` 控制。

2026-06-30 00:00 CST 检查 LLM-76 `ai_botserver_sch` 进程环境，只看到：

- `HF_RENDER_BACKEND=docker`
- `HF_MAX_CONCURRENCY=7`
- `HF_DOCKER_BINARY=/data/script/hf-docker`
- `HF_DOCKER_IMAGE=h20-hyperframes-renderer:0.6.42-node22.22.2`
- `HF_DOCKER_MOUNTS=/data:/data,/tmp:/tmp`
- `HF_DOCKER_SHM_SIZE=2g`
- `HF_RENDER_LOCK_TIMEOUT_SECONDS=60`

未看到 `H20_HYPERFRAMES_ROUTE_ENABLED=1`。

## 影响任务

正式库 `zhugedata.t_video_generate_task` 最终匹配 5 条，均发生在修复前：

| local id | task_id | job_id | company_id | user_id | templates_style_id | 标题 | 失败时间 |
|---|---:|---:|---:|---:|---:|---|---|
| 17614 | 17620 | 20044 | 69 | 85 | 2 | 21个城市房价止跌上涨！刚需现在该抄底吗 | 2026-06-29 23:54:22 CST |
| 17615 | 17621 | 20045 | 65 | 1374 | 2 | 新增5个区收二手房做保障房！刚需改善都能沾光？ | 2026-06-29 23:56:43 CST |
| 17616 | 17622 | 20047 | 65 | 1374 | 1 | 新增5个区收二手房做保障房！直接影响全国房价走向 | 2026-06-29 23:57:06 CST |
| 17617 | 17623 | 20048 | 82 | 379 | 2 | C82T10016U379T20260630000238 | 2026-06-30 00:02:38 CST |
| 17618 | 17624 | 20049 | 82 | 379 | 1 | C82T10016U379T20260630000307 | 2026-06-30 00:03:07 CST |

截图中的 `templates_style_id=2 template_id=video_diary` 对应前两条之一；截图未包含 job_id/title，不能仅凭截图唯一确定是哪一条。

## 解决方案

已执行修复。

2026-06-30 00:07 CST 在 LLM-76 修复 `ai_botserver_sch` supervisor 环境：

1. 备份 `/etc/supervisord.d/ai_botserver_sch.conf` 到 `/etc/supervisord.d/ai_botserver_sch.conf.bak.20260630000700`。
2. 在 `environment=` 中追加 `H20_HYPERFRAMES_ROUTE_ENABLED="1"`，保留原有 HyperFrames Docker 参数。
3. 执行 `supervisorctl reread && supervisorctl update ai_botserver_sch && supervisorctl restart ai_botserver_sch`。
4. 新进程 PID 为 `563552`，状态 `RUNNING`。

历史失败任务未自动重置或重跑，因为这些任务已回调 CRM 且出现 `积分解冻成功`，直接改库重跑可能造成重复回调或结算状态二次影响。

## 优化点

- 正式发布 checklist 里应明确 `H20_HYPERFRAMES_ROUTE_ENABLED=1` 属于 scheduler 必需 env，不只是 H20 测试服配置。
- 发布后应跑一个 `templates_style_id=1/2` 的正式 smoke task，确认不会在路由开关处被拦截。

## 验证结果

2026-06-30 00:00 CST 只读验证：

- LLM-76 scheduler 日志出现 `[template-route-resolved]` 后紧接 `[hyperframes-route-disabled]`。
- LLM-76 scheduler 进程环境缺少 `H20_HYPERFRAMES_ROUTE_ENABLED=1`。
- 正式库任务失败原因与前端截图一致。

2026-06-30 00:12 CST 修复后验证：

- `supervisorctl status ai_botserver_sch` 显示 `RUNNING`。
- 进程环境包含 `H20_HYPERFRAMES_ROUTE_ENABLED=1`，并保留 `HF_RENDER_BACKEND=docker`、`HF_DOCKER_IMAGE=h20-hyperframes-renderer:0.6.42-node22.22.2`、`HF_MAX_CONCURRENCY=7`、`HF_DOCKER_BINARY=/data/script/hf-docker`、`HF_DOCKER_MOUNTS=/data:/data,/tmp:/tmp`、`HF_DOCKER_SHM_SIZE=2g`、`HF_RENDER_LOCK_TIMEOUT_SECONDS=60`。
- 直接加载 `template_route.py` 验证：`templates_style_id=2` 解析为 `hyperframes/video_diary`，`skip_old_pipeline=True`，当前不会触发 `HYPERFRAMES_ROUTE_DISABLED`。
- 正式库 `zhugedata.t_video_generate_task` 中同类失败总数为 5；`2026-06-30 00:07:00 CST` 之后新增同类失败数为 0。
- 调度日志中 `2026-06-30 00:07:00 CST` 之后 `[hyperframes-route-disabled]` 新增数为 0；最后两条真实拦截日志仍是修复前的 `job_id=20048/task_id=17623` 和 `job_id=20049/task_id=17624`。

## 相关文件

- `scheduler/collect_scheduler.py`
- `router/service/video_server2/template_route.py`

## 相关记录

- [[projects/joying-bot-server/docs/prod-test-hyperframes-runtime-config-check-2026-06-29|正式服 / 测试服 HyperFrames 配置对比]]
