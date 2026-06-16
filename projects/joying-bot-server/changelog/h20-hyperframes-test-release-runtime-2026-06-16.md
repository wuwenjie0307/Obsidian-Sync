---
date: 2026-06-16
project: joying-bot-server
type: changelog
tags: [h20, hyperframes, test-release, gitlab, runtime, database]
aliases: [H20 HyperFrames test release runtime 2026-06-16, 网感视频 test 发布与运行时验证]
---

# H20 HyperFrames test 发布与运行时验证（2026-06-16）

## 改动类型

测试环境发布 / 数据库 schema 补齐 / H20 服务运行时验证。

## 改动内容

- 功能分支：`feature/ai_v6.3.3_vibevideo`
- 目标分支：`test`
- 临时目标侧集成分支：`merge-check/ai_v6.3.3_vibevideo-to-test`
- 远端 `test` 已更新到：`1fb5e38935e7da6b5358dd6bbe5baac29825cd2e`
- 测试库 `zhugedata_test.t_video_generate_task` 已补齐 HyperFrames 所需字段：
  - `whisper_timeline_path TEXT`
  - `analysis_path TEXT`
  - `analysis_ms INT`
  - `hf_manifest_path TEXT`
  - `hf_result_path TEXT`
  - `hf_final_video_path TEXT`
  - `hf_cover_path TEXT`
  - `hf_subtitle_timeline_path TEXT`
  - `hf_render_ms INT`
  - `hf_final_video_url TEXT`
  - `hf_cover_url TEXT`
- 保留已存在字段和索引：
  - `templates_style_id INT NOT NULL DEFAULT 3`
  - `whisper_timeline_ms INT`
  - `idx_video_generate_task_templates_style_id(templates_style_id, task_status)`

## 影响范围

- H20 测试环境已加载新代码 release：`/data/project/test_ai_botserver.20260616162226`
- `/data/project/test_ai_botserver` 已指向该 release。
- 代码标记已确认存在：
  - `hyperframes-postprocess/index.js`
  - `router/service/video_server2/hyperframes_cli.py`
  - `router/service/video_server2/hyperframes_analysis.py`
  - `router/service/video_server2/template_route.py`
  - `sql/h20_hyperframes_upload_callback.sql`
- grep 标记已确认存在：`hf_final_video_url`、`HYPERFRAMES_UPLOAD_FAILED`、`H20_HYPERFRAMES_ROUTE_ENABLED`。

## 验证结果

发布前验证：

```text
python -m py_compile ... 通过
node --check hyperframes-postprocess\index.js 通过
git diff --check origin/test...HEAD 通过
python -m unittest test.test_template_route test.test_hyperframes_postprocess test.test_hyperframes_cli test.test_hyperframes_analysis test.test_whisper_timeline test.test_hyperframes_upload_callback -v
```

结果：65 个网感相关测试通过。

H20 运行时验证：

- 自动部署后 `8017` / `18017` 已运行在新 release。
- `8100` 原本仍在旧 release `/data/project/test_ai_botserver.20260616093915`，已按 exact PID 重启。
- 重启后进程：
  - `8100 PID=458228`，cwd 为 `/data/project/test_ai_botserver.20260616162226`
  - `8017 PID=454974`，cwd 为 `/data/project/test_ai_botserver.20260616162226`
  - `18017 PID=454975`，cwd 为 `/data/project/test_ai_botserver.20260616162226`
- 健康检查：
  - `8100 /status/check -> {"status":"ok"}`
  - `8017 /status/check -> {"status":"ok"}`
- 队列和模型池：
  - 当前无 `task_status IN (0,1,2)` active 视频任务。
  - `t_comfyui_config` 无 `is_active=2` 模型池锁。

## 相关文件

- `pojo/models.py`
- `scheduler/collect_scheduler.py`
- `router/crm_server.py`
- `router/service/video_server2/template_route.py`
- `router/service/video_server2/whisper_timeline.py`
- `router/service/video_server2/hyperframes_analysis.py`
- `router/service/video_server2/hyperframes_cli.py`
- `hyperframes-postprocess/index.js`
- `sql/h20_hyperframes_template_routing.sql`
- `sql/h20_hyperframes_whisper_timeline.sql`
- `sql/h20_hyperframes_analysis.sql`
- `sql/h20_hyperframes_cli.sql`
- `sql/h20_hyperframes_upload_callback.sql`

## 相关记录

- [[projects/joying-bot-server/docs/h20-hyperframes-db-field-change-rules-2026-06-16|H20 HyperFrames 数据库字段变更规则]]
- [[projects/joying-bot-server/docs/h20-hyperframes-prd-uncertainty-decisions-2026-06-08|H20 HyperFrames PRD 不确定项与决策记录]]
- [[projects/joying-bot-server/changelog/h20-hyperframes-phase08-acceptance-probe-2026-06-10|H20 HyperFrames Phase 08 acceptance probe]]

## 遗留问题

- 真实 E2E 尚未完成，需要继续跑：`science_guide`、`video_diary`、`minimal` 各一条。
- 仍需检查最终视频、封面、回调、`ffprobe`、人工抽帧视觉效果。
- `H20_HYPERFRAMES_ROUTE_ENABLED` 是运行时门禁；如果未显式开启，`science_guide` / `video_diary` 会明确失败为 disabled，不会误入新链路。
- 测试服发现 bug 必须先修回 `feature/ai_v6.3.3_vibevideo`，再重新集成到 `test`，不能只修 `test`。

## 图谱链接

- [[projects/joying-bot-server/00-项目概览|项目概览]]
- [[projects/joying-bot-server/changelog/00-changelog-index|更新日志索引]]
- [[projects/joying-bot-server/docs/00-docs-index|参考文档索引]]