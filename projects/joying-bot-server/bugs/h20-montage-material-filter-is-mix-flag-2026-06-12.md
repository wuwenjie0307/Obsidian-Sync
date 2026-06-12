---
date: "2026-06-12"
project: "joying-bot-server"
type: bug
status: fixed-on-test
severity: high
tags: [bug, h20, video-generation, montage, crm-sync, scheduler, material-filter, apidoc]
aliases: ["H20 混剪素材已落库但被 is_mix_material 过滤"]
---

# H20 混剪素材已落库但被 is_mix_material 过滤

## 图谱链接

- 项目: [[projects/joying-bot-server/00-项目概览|joying-bot-server]]
- 索引: [[projects/joying-bot-server/bugs/00-bugs-index|Bug 记录索引]]

## 问题描述

2026-06-12 排查 H20 测试环境一条视频任务：用户反馈已经设置混剪镜头，但实际生成结果没有使用混剪素材，最终表现为纯口播。

目标视频：

```text
https://videos-test.joyingai.cn/video/crm/20260611/user4_1781164414649_34a68f6c8b829905.mp4
```

定位到任务：

| 字段 | 值 |
|---|---:|
| `company_id` | `1` |
| `job_id` | `1198` |
| `task_id` | `1175` |
| `task_status` | `3` |
| `progress` | `100` |

## 复现步骤

1. 用户在 CRM/CSM 任务中配置混剪/分镜素材。
2. H20 生成视频任务 `job_id=1198, task_id=1175`。
3. 生成完成后查看视频，结果未出现混剪画面。
4. 查 H20 本地素材表和生成日志。

## 期望行为

只要当前任务下存在有效的用户任务素材，生成阶段应将视频素材组装进 `Montage_dict`，将图片素材组装进 `Photo_dict`，在对应口播文案处使用混剪/分镜素材覆盖原口播画面。

## 实际行为

H20 本地表 `t_video_material_template` 里已有 2 条素材：

- 1 条视频素材，`material_type=1`
- 1 条图片素材，`material_type=2`
- 两条都有 `material_source_url`
- 两条都有 `material_subtitle`
- 但两条 `is_mix_material=0`

运行日志显示生成阶段读到了素材，但全部被过滤：

```text
[process-video-task-material-filter] job_id=1198 task_id=1175 material_count=2 selected_mix_material_count=0 skipped_non_mix_material_count=2 montage_count=0 photo_count=0
```

后续生成参数等价于：

```text
Montage_dict=None
Photo_dict=None
```

因此生成结果成了纯口播。

## 原因

本次直接原因不是素材没有同步，而是生成阶段过度依赖 `is_mix_material=1` 作为唯一开关。

旧逻辑在 `scheduler/collect_scheduler.py` 的生成前素材组装阶段会：

1. 按 `job_id + task_id` 查 H20 本地 `t_video_material_template`。
2. 跳过缺少 `material_source_url` 或 `material_subtitle` 的素材。
3. 对 `is_mix_material != 1` 的素材直接 `continue`。
4. 只有 `is_mix_material=1` 的素材才进入 `Montage_dict` / `Photo_dict`。

这条任务的 2 条有效素材都为 `is_mix_material=0`，所以被全部跳过。

Apidoc 中 `/crm/agent/pc/video/materialUsertaskList` 的返回示例把 `is_mix_material` 标注为“是否设置分镜”，但历史记录和本次数据都说明该字段不能作为唯一硬判断。更稳妥的判断应优先看当前任务维度素材是否有效：`task_id`、`material_source_url`、`material_subtitle`、`material_type`。

## 和上次混剪失效的对比

相关历史记录：[[projects/joying-bot-server/bugs/prod-scheduler-montage-material-sync-2026-06-08|生产 scheduler 未同步用户混剪素材导致纯口播]]

| 对比项 | 上次混剪失效 | 本次混剪失效 |
|---|---|---|
| 表象 | 用户选了混剪，生成纯口播 | 用户选了混剪，生成纯口播 |
| CRM/CSM 是否能查到素材 | 能 | 能 |
| H20/AI 本地 `t_video_material_template` 是否有素材 | 没有 | 有，2 条 |
| 断点 | 同步阶段 | 生成过滤阶段 |
| 直接原因 | scheduler 依赖 `video_category=2`，未同步 `materialUsertaskList` | 生成阶段硬要求 `is_mix_material=1`，有效素材被跳过 |
| 关键错误依赖字段 | `video_category` | `is_mix_material` |
| 生成前素材数 | `material_count=0` | `material_count=2`，但 `selected_mix_material_count=0` |
| 最终传参 | `Montage_dict=None` / `Photo_dict=None` | `Montage_dict=None` / `Photo_dict=None` |
| 修复方向 | scheduler 改为按 `company_id + job_id + task_id` 同步用户任务素材 | 生成阶段不再单靠 `is_mix_material=1`，无显式选中时 fallback 使用有效任务素材 |

共同点：两次本质都是后端过度相信 CRM 侧不稳定标记字段，导致用户任务维度的有效混剪素材没有进入生成链路。

## 解决方案

已在 `test` 分支合入后端兼容修：

- 个人分支：`codex-montage-material-fallback`
- 修复提交：`5e4b9b90 fix: fallback to valid montage task materials`
- 合入 `test` 后的远端提交：`5b20bd21`

修复规则：

1. 生成阶段仍按 `job_id + task_id` 查询本地 `t_video_material_template`，没有取消查表。
2. 先筛有效素材：必须有 `material_source_url`、`material_subtitle`，且 `material_type` 为 `1` 或 `2`。
3. 如果存在 `is_mix_material=1` 的有效素材，仍然只使用这些明确选中的素材。
4. 如果没有任何 `is_mix_material=1`，但当前任务下有有效素材，则 fallback 使用这些有效素材。
5. fallback 时记录 warning 日志：

```text
[process-video-task-material-filter-fallback] reason=no_selected_mix_material_but_valid_task_materials
```

该修复只解决“素材已落库但被 `is_mix_material` 过滤”的场景。如果本地 `t_video_material_template` 没有素材，仍然属于上次那类同步阶段问题，需要继续修同步链路。

## 优化点

- CRM/CSM 侧需要确认：用户设置混剪后，`materialUsertaskList` 为什么仍返回 `is_mix_material=0`。
- Apidoc 需要明确 `is_mix_material` 是否是强业务开关，还是仅展示/记录字段。
- H20 生成日志应持续保留：`material_count`、`selected_mix_material_count`、`skipped_non_mix_material_count`、`fallback_material_count`、`montage_count`、`photo_count`。
- 如果未来 CRM 明确保证 `is_mix_material` 可靠，可以再收窄 fallback 策略。

## 验证结果

在隔离 worktree 中完成 TDD 验证：

1. 先新增失败测试，确认旧代码缺少 fallback helper，会红灯。
2. 实现 `_build_video_task_material_dicts` 后测试转绿。
3. 合入最新 `origin/test` 无冲突。
4. 推送共享 `test` 前再次验证通过。

验证命令：

```powershell
python -m unittest test.test_video_material_montage_sync
```

结果：

```text
Ran 4 tests in 0.215s
OK
```

语法检查：

```powershell
python -m py_compile scheduler\collect_scheduler.py test\test_video_material_montage_sync.py
```

结果：退出码 `0`。

## 相关文件

- `C:\Users\admin\Desktop\joyingbot-new\scheduler\collect_scheduler.py`
- `C:\Users\admin\Desktop\joyingbot-new\test\test_video_material_montage_sync.py`

## 相关记录

- [[projects/joying-bot-server/bugs/prod-scheduler-montage-material-sync-2026-06-08|生产 scheduler 未同步用户混剪素材导致纯口播]]
- [[projects/joying-bot-server/docs/prod-montage-material-sync-deferred-todo-2026-06-09|生产混剪素材同步大改延后待办]]
