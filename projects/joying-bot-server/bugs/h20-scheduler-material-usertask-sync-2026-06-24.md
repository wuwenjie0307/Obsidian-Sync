---
date: "2026-06-24"
project: "joying-bot-server"
type: bug
status: fixed-in-feature
severity: high
tags: [bug, h20, video-generation, montage, material, scheduler, crm, hyperframes]
aliases: ["H20 scheduler 用户任务混剪素材同步", "materialUsertaskList 与 materialTemplatesList 混剪素材同步差异"]
---

# H20 scheduler 用户任务混剪素材同步

## 图谱链接

- 项目: [[projects/joying-bot-server/00-项目概览|joying-bot-server]]
- 索引: [[projects/joying-bot-server/bugs/00-bugs-index|Bug 记录索引]]
- 相关字段文档: [[projects/joyingbot-new/docs/2026-06-23_crm_material_usertask_list_response_fields|CRM 用户任务素材列表返回体字段说明]]

## 问题描述

2026-06-24 测试环境排查网感视频混剪问题。产品反馈选择了混剪，但生成视频里多个混剪素材没有全部生效。实测视频：

```text
https://videos-test.joyingai.cn/video/crm/20260624/user4_1782276740148_51ec1196e5462e74.mp4
```

用户感知是“混剪没生效”或“只生效了一个素材”。排查后确认：渲染链路支持多个混剪素材，问题出在本地素材表没有同步完整用户任务素材。

## 测试库证据

对应任务：

```text
本地 t_video_generate_task.id = 1619
job_id = 1461
task_id = 1403
templates_style_id = 2  # 视频日记
generate_source = 2
generate_type = NULL
task_status = 3
progress = 100
callback_status = 1
created_time = 2026-06-24 04:42:42 UTC
updated_time = 2026-06-24 04:52:36 UTC
```

本地 `t_video_material_template` 中只有一条素材完整，另一条为空壳：

| local id | material_id | material_type | is_mix_material | sort_order | source_url 状态 |
|---:|---:|---:|---:|---:|---|
| 796 | 727 | 1 | 1 | 2 | 有 mp4 URL |
| 797 | 726 | NULL | NULL | NULL | NULL，空壳 |

直接查 CRM 的 `materialUsertaskList`，同一个 `job_id=1461/task_id=1403` 实际有两条完整用户任务素材：

| material_id | material_type | is_mix_material | sort_order | source_url |
|---:|---:|---:|---:|---|
| 727 | 1 | 1 | 2 | mp4 |
| 726 | 2 | 1 | 1 | jpg |

结论：不是 HyperFrames/render 丢了第二条素材，而是生成前本地表只拿到一条完整素材；第二条图片素材同步成空壳，生成时被当作无效素材跳过。

## 两个素材接口的区别

`materialTemplatesList`：

```text
/crm/agent/pc/video/materialTemplatesList
```

老的素材库/模板素材接口。历史上用于同步素材库，但不一定代表“当前用户本次任务实际选择的混剪素材”。这次任务里继续依赖它，会导致用户选中的部分素材同步不完整。

`materialUsertaskList`：

```text
/csm/agent/pc/video/materialUsertaskList
```

用户任务素材接口。它返回某个 job/task 下用户实际选择的素材，包含 `job_id/task_id/material_source_url/material_type/is_mix_material/sort_order` 等生成需要的字段。对混剪生成来说，这个接口才是本次任务素材的真相来源。

## 与同事聊天记录的对应关系

同事排查记录中的关键判断：

```text
失败的几条任务在 materialUsertaskList 里能查到用户选的混剪素材，job_id、task_id 也能对应上；
应该问题是我们生产本地的 t_video_material_template 没同步到这些素材，
所以后面 scheduler 生成时就当成没有混剪素材，最后生成成纯口播了。

更像是后端 scheduler 这条老链路没同步 materialUsertaskList 的素材，
最近生成流程走 scheduler 后才暴露。
```

本次测试任务现象与这段判断吻合：CRM 用户任务素材接口有完整素材，本地素材表缺失/空壳，scheduler 后续只按本地表生成。

早期怀疑的 `video_category=2` 条件不是这次最终根因。当前代码已经没有用 `video_category=2` 作为同步混剪素材开关；真正差异是 scheduler 同步链路使用了旧素材接口，而创建任务接口已经使用用户任务素材接口。

## 代码链路

生成阶段读取本地表：

- `scheduler/collect_scheduler.py::_process_single_video_task`
- `scheduler/collect_scheduler.py::_prepare_hyperframes_video_task`
- 两条链路都会查询 `VideoMaterialTemplate`，然后通过 `_build_video_task_material_dicts()` 组装 `Montage_dict/Photo_dict`。

创建任务接口已经使用新接口：

- `router/crm_server.py::generate_video_task`
- 调用 `get_crm_video_material_usertask_list()`。
- 解析素材行自己的 `task_id/video_task_id/taskId` 后写入 `t_video_material_template`。

问题点：

- `scheduler/collect_scheduler.py::sync_crm_video_generate_tasks()` 的老同步链路仍使用 `get_crm_video_material_templates_list()`。
- 对当前用户任务混剪素材，旧接口不能稳定返回完整用户选中素材。

## 修复方案

feature 分支已收窄为保守修复：

1. `sync_crm_video_generate_tasks()` 保留原有 `materialTemplatesList` 同步路径。
2. 仅当 `templates_style_id in (1, 2)`（科普指南/视频日记）时，额外调用 `materialUsertaskList` 做补齐。
3. 补齐只处理本地缺失或空壳素材；如果本地素材已有 `material_source_url/material_type/is_mix_material`，不覆盖。
4. 入库时用素材行返回的真实 `task_id/video_task_id/taskId`。
5. 如果素材行缺少 task_id，跳过并记录日志，避免写入空壳或错误 task 维度。
6. 渲染/后处理层不改，因为只要本地表有多条完整素材，旧极简和 H20 HyperFrames 都能消费多条素材。

## 验证结果

已在本地 feature 分支跑过：

```text
python -m unittest test.test_video_material_montage_sync
python -m unittest test.test_hyperframes_cli
```

结果均通过。`test_video_material_montage_sync` 增加了回归断言：scheduler 同步必须使用 `materialUsertaskList`，并按素材真实 task_id 入库。

## 线上 master 待确认点

用户要求后续只读查看 GitLab `master` 分支，因为 master 是线上正在使用的代码且线上当前没有问题。检查目标：

1. `crm/crm_request_util.py` 中两个接口路径是否与当前 feature 一致。
2. `router/crm_server.py::generate_video_task` 是否使用 `materialUsertaskList`。
3. `scheduler/collect_scheduler.py::sync_crm_video_generate_tasks` 在线上 master 是否仍使用 `materialTemplatesList`，或者是否有其它线上保护逻辑。
4. 只允许 `git fetch` / `git show origin/master:...` / `git grep origin/master` 等只读方式，不切分支、不 checkout、不 merge，避免污染当前功能分支和 test。

## 相关文件

- `crm/crm_request_util.py`
- `router/crm_server.py`
- `scheduler/collect_scheduler.py`
- `pojo/models.py`
- `test/test_video_material_montage_sync.py`

## 相关记录

- [[projects/joying-bot-server/bugs/prod-scheduler-montage-material-sync-2026-06-08|prod-scheduler-montage-material-sync-2026-06-08]]
- [[projects/joying-bot-server/bugs/h20-montage-material-filter-is-mix-flag-2026-06-12|h20-montage-material-filter-is-mix-flag-2026-06-12]]
- [[projects/joying-bot-server/bugs/prod-montage-empty-material-file-2026-06-23|正式服混剪素材空文件导致失败]]
- [[projects/joyingbot-new/docs/2026-06-23_crm_material_usertask_list_response_fields|CRM 用户任务素材列表返回体字段说明]]

## 线上 master 只读对比结果

2026-06-24 已只读 fetch GitLab `origin/master`，未切分支、未 checkout、未 merge。当前查看的 master commit：

```text
3d20eb7e3db6706d2f46ef5fa4e6b136def371ac
```

只读命令原则：

```text
git fetch origin master:refs/remotes/origin/master
git grep ... origin/master -- <files>
git show origin/master:<file>
```

确认结果：

1. `origin/master:crm/crm_request_util.py` 同时定义了两个接口：
   - `get_crm_video_material_templates_list()` -> `/crm/agent/pc/video/materialTemplatesList`
   - `get_crm_video_material_usertask_list()` -> `/csm/agent/pc/video/materialUsertaskList`
2. `origin/master:router/crm_server.py::generate_video_task()` 已经使用 `materialUsertaskList`，并且按素材行返回的真实 `task_id/video_task_id/taskId` 入库。
3. `origin/master:scheduler/collect_scheduler.py::sync_crm_video_generate_tasks()` 仍是老逻辑：
   - import `get_crm_video_material_templates_list`
   - 注释写着 `video_category=2 时，同步素材库 materialTemplatesList 到本地表`
   - 代码判断 `if int(task_video_category) == 2:`
   - 内部调用 `get_crm_video_material_templates_list(...)`
   - upsert 使用外层 `task_id`，不是素材行自身的 `task_id`

对当前问题的解释：

- master 线上“没问题”不代表 scheduler 老链路是新任务素材的正确来源。
- 更可能是线上当前正常任务主要走 `/generate_video_task` 接口链路，接口链路已经用 `materialUsertaskList`，所以用户实际选择的混剪素材能同步完整。
- 一旦任务进入或依赖 scheduler 的老同步链路，就仍可能触发同类问题：`video_category=0` 不同步，或用 `materialTemplatesList` 同步不到完整用户任务素材。
- 这与同事聊天记录“最近生成流程走 scheduler 后才暴露”一致。

本次 feature 修复与 master 的差异：

- 去掉 scheduler 对 `video_category=2` 的素材同步开关。
- scheduler 改用 `materialUsertaskList`。
- scheduler 入库时按素材行真实 `task_id/video_task_id/taskId` 写入。

注意：这次只读检查没有修改任何 Git 分支。工作区已有脏文件保持原样。


