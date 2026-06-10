---
date: "2026-06-10"
tags: [changelog, h20, hyperframes, rollout]
---

# HyperFrames 测试环境合并保护与路由开关

## 改动类型

- [ ] 新功能
- [x] Bug 修复
- [ ] 重构
- [x] 配置变更

## 改动内容

- 决策：当前 HyperFrames 后处理分支暂不合并到共享 `test`，因为测试库还没有添加本分支新增的 `t_video_generate_task` 字段。
- 风险：即使运行时开关默认关闭，ORM 模型已经映射了 `templates_style_id`、Whisper、analysis、HyperFrames artifact/url 等新字段；如果代码先于数据库迁移部署，普通任务查询或写入也可能触发 unknown column，并影响原有 minimal 旧链路。
- 新增控制：提交 `1c67cd5b fix: guard hyperframes route behind switch` 增加 `H20_HYPERFRAMES_ROUTE_ENABLED`。默认关闭；数据库已迁移但运行链路未验收时，`science_guide` / `video_diary` 会显式失败为 `HYPERFRAMES_ROUTE_DISABLED`，不会进入不确定的 HyperFrames 渲染链路。
- 文档：`docs/h20_hyperframes_phase08_acceptance.md` 增加合并和测试环境保护门槛，明确先迁库、再部署、先验 minimal、最后开 HyperFrames 开关。

## 影响范围

- 个人分支：`feature/hyperframes-postprocess-dev` 已推送到 GitLab。
- 共享 `test`：未合并、未推送、未重启测试服务。
- 合并前置条件：测试库必须先执行所有 SQL 迁移，至少到 `sql/h20_hyperframes_upload_callback.sql`；之后部署时先保持 `H20_HYPERFRAMES_ROUTE_ENABLED` 关闭，验证旧链路，再开关控制验收 HyperFrames。

## 相关 Commit

- `1c67cd5b fix: guard hyperframes route behind switch`

## 相关文件

- `router/service/video_server2/template_route.py`
- `scheduler/collect_scheduler.py`
- `test/test_template_route.py`
- `docs/h20_hyperframes_phase08_acceptance.md`

## YApi / 接口文档检查

- 项目：`crm`。
- 已有分类：`视频生成 | 网感模板`，包含 `templatesStyleList` PC/H5 两个接口，用于返回风格列表，例如 `id`、`style_name`、`cover_url`、`sort`、`status`。
- 创建接口：`/crm/agent/pc/video/generateJobBatchCreate` 和 `/crm/agent/pc/video/generateJobUserCreate` 的请求示例已经包含 `templates_style_id`。
- 任务列表接口：`/crm/agent/pc/video/generateTaskList` 当前响应示例未展示 `templates_style_id`，后续联调如果前端/CSM 需要回显风格，需要补接口文档和接口响应确认。
- 注意：YApi 详情里存在示例 Authorization，不要复制进代码、文档或提交记录。
