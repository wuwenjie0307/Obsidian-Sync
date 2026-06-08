---
date: "2026-06-08"
status: open
severity: high
tags: [bug, production, lucky-prod, video-generation, montage, crm-sync, scheduler, apidoc]
---

# 生产 scheduler 未同步用户混剪素材导致纯口播

## 问题描述

2026-06-08 客户反馈连续 3 次提交视频任务，每次都选择了 1 个混剪/分镜素材，但生成结果都是纯口播，没有混剪画面覆盖。

业务预期是：用户选中某一段文案后，视频播放到这句口播文案时，使用用户选择的分镜视频/素材覆盖原口播画面。

本次排查确认：不是 ffmpeg 覆盖阶段失败，也不是文案太短导致无法匹配；问题发生在更早的素材同步阶段。

## 生产证据

失败任务来自生产库 `zhugedata.t_video_generate_task`：

| local id | job_id | task_id | company_id | video_category | generate_source | 结果 |
|---:|---:|---:|---:|---:|---:|---|
| `9694` | `10433` | `9687` | `193` | `0` | `2` | 生成成功但纯口播 |
| `9696` | `10435` | `9689` | `193` | `0` | `2` | 生成成功但纯口播 |
| `9697` | `10436` | `9690` | `193` | `0` | `2` | 生成成功但纯口播 |

生产本地表 `t_video_material_template` 对这 3 个任务没有素材记录，`material_count=0`。这说明后续视频生成链路根本没有拿到混剪素材。

同时，CRM 实时接口 `/csm/agent/pc/video/materialUsertaskList` 能查到用户选中的素材：

- `company_id=193, job_id=10436, task_id=9690` 返回 `total=1`，有素材 URL，`material_type=1`，`is_mix_material=1`。
- `company_id=193, job_id=10433, task_id=9687` 也能返回 1 条用户任务素材。

结论：用户在 CRM 侧确实选了混剪素材，但生产后端本地没有同步下来。

## apidoc 对照

apidoc 里相关接口含义如下：

| 接口 | apidoc 标题 | 作用 |
|---|---|---|
| `/crm/agent/pc/video/materialTemplatesList` | 短视频 / 模板 / 模板素材列表 | 模板素材库，不是用户本次任务实际选择的素材 |
| `/crm/agent/pc/video/materialUsertaskList` | 短视频 / 模板 / 用户任务素材列表 | 查询用户任务维度素材 |
| `/csm/agent/pc/video/materialUsertaskList` | 短视频 / 视频分镜素材列表 | 查询用户任务/分镜维度素材 |

`materialUsertaskList` 的入参示例包含：

```json
{
  "filter": {
    "company_id": 1,
    "job_id": 118,
    "task_id": 143
  },
  "from": 1,
  "size": 10
}
```

返回素材字段包括：

- `job_id`
- `task_id`
- `material_type`
- `material_subtitle`
- `material_source_url`
- `is_mix_material`
- `sort_order`

这说明判断用户有没有选混剪素材，应该看 `materialUsertaskList`，不能只看 `video_category`，也不能从 `materialTemplatesList` 判断。

注意：`csm` 项目里的 `/csm/agent/pc/video/materialUsertaskList` apidoc 返回示例疑似复制了 job 列表字段，里面出现了 `video_category` 等字段，容易误导；`crm` 项目里的同类接口示例更接近真实素材结构。

## 原因

直接原因：生产 scheduler 链路同步素材时使用了旧逻辑。

生产分支 `origin/dev-lucky-yk-prod` 中，`scheduler/collect_scheduler.py` 仍然是：

- 先判断 `video_category == 2`
- 满足后才同步素材
- 同步时调用的是 `materialTemplatesList`

但这次失败任务的真实混剪素材在 `materialUsertaskList` 中，且任务 `video_category=0`。因此 scheduler 没有把用户任务素材同步到本地 `t_video_material_template`，后续生成时只能按“没有混剪素材”的纯口播任务处理。

更准确地说，这不是前端没选上，而是后端 scheduler 没有从正确接口同步用户任务素材。

## 为什么之前没明显出现

这个更像是遗留链路问题，不是 2026-06-08 当天新写坏的逻辑。

旧 scheduler 逻辑早就存在，但之前能混剪的任务可能更多走 `/generate_video_task` 这条 router 链路。生产分支 router 里已经有“按 job 调用 `materialUsertaskList` 同步素材”的逻辑，所以那条链路能把素材写入本地表。

近期生成流程更多走 scheduler 后，scheduler 没同步 `materialUsertaskList` 的旧问题才暴露出来。

补充证据：5 月 21 日曾经成功混剪的任务里，`video_category` 也不一定是 `2`，`is_mix_material` 也不一定是 `1`；真正区别是当时本地 `t_video_material_template` 里有素材记录。

## 复现步骤

1. 在 CRM/前端创建视频生成任务。
2. 给某段文案选择 1 个混剪/分镜素材。
3. 让任务走生产 scheduler 生成链路。
4. 生成完成后查看视频，结果是纯口播。
5. 查生产本地 `t_video_material_template`，对应 `job_id/task_id` 没有素材记录。
6. 同时查 CRM `/csm/agent/pc/video/materialUsertaskList`，对应 `company_id/job_id/task_id` 能查到用户选的素材。

## 期望行为

scheduler 同步任务时，应根据 `company_id + job_id + task_id` 或至少 `company_id + job_id` 调用 `materialUsertaskList`，把用户实际选择的任务素材同步到本地 `t_video_material_template`。

生成阶段应能读取本地素材表，并在对应口播文案处覆盖混剪/分镜素材。

## 实际行为

scheduler 仍按旧逻辑依赖 `video_category == 2`，并调用 `materialTemplatesList`。对于 `video_category=0` 但实际有用户混剪素材的任务，素材没有入库，最终生成成纯口播。

## 解决方案

建议修复 scheduler 素材同步逻辑：

1. scheduler 不再用 `video_category == 2` 作为是否同步混剪素材的开关。
2. scheduler 改为调用 `get_crm_video_material_usertask_list` / `/materialUsertaskList`。
3. 按 `company_id + job_id + task_id` 同步用户任务素材；如果接口按 job 返回多任务素材，则入库时使用返回行里的真实 `task_id` 做隔离。
4. 不要硬性只保留 `is_mix_material=1`。历史成功任务里存在 `is_mix_material=0` 但仍有素材的情况，生成侧应优先看 `task_id`、`material_source_url`、`material_subtitle`、`material_type` 等有效素材字段。
5. 增加回归测试，覆盖 `video_category=0` 但 `materialUsertaskList` 有素材的任务。

## 当前沟通口径

对前端/CRM 同事可以这样说明：

> 我查了下 apidoc 和生产数据，用户选的混剪素材应该在 `materialUsertaskList` 里，不是靠 `video_category` 或 `materialTemplatesList` 判断。这次 CRM 里能查到素材，但我们后端 scheduler 没同步到本地表，所以生成成纯口播。你们那边帮忙确认 `materialUsertaskList` 里的 `job_id`、`task_id`、素材地址这些字段正常写入就行。

更简短版本：

> 前端应该是选上了，问题在后端 scheduler 没把 `materialUsertaskList` 里的素材同步下来，所以生成时当成没混剪。

## 环境信息

- 项目：`joying-bot-server` / `joyingbot-new`
- 生产分支参考：`origin/dev-lucky-yk-prod`
- 本地工作分支：`test` / `feature/ai_v6.3.1_video` 曾做过修复验证
- 生产 DB：`zhugedata`
- 相关表：`t_video_generate_task`、`t_video_material_template`
- 相关接口：`/csm/agent/pc/video/materialUsertaskList`、`/crm/agent/pc/video/materialUsertaskList`、`/crm/agent/pc/video/materialTemplatesList`
- 本次生产排查为只读查询：没有修改生产代码、生产 DB，也没有重启生产服务。

## 优化点

- scheduler 素材同步日志里明确打印：调用的素材接口、`company_id/job_id/task_id`、返回 `total`、实际入库条数。
- 素材同步失败或返回 0 条时，如果 CRM 任务疑似有混剪配置，应记录 warning，避免最后只看到纯口播结果。
- 不要把 `video_category` 当作“是否存在用户混剪素材”的唯一依据；它更像视频大类字段，历史数据中不稳定。
- apidoc 中 `/csm/agent/pc/video/materialUsertaskList` 的返回示例建议请接口维护方修正，避免继续误导成 job 列表或 `video_category` 判断。
- 生成侧对空素材表增加可观测日志：明确输出“当前 task 本地素材数为 0，按纯口播生成”。

## 相关文件

- `C:\Users\admin\Desktop\joyingbot-new\scheduler\collect_scheduler.py`
- `C:\Users\admin\Desktop\joyingbot-new\router\crm_server.py`
- `C:\Users\admin\Desktop\joyingbot-new\router\service\video_server2\video_work.py`
- `C:\Users\admin\Desktop\joyingbot-new\router\service\video_server2\video_select_overlay.py`
- apidoc：`/csm/agent/pc/video/materialUsertaskList`
- apidoc：`/crm/agent/pc/video/materialUsertaskList`
- apidoc：`/crm/agent/pc/video/materialTemplatesList`
