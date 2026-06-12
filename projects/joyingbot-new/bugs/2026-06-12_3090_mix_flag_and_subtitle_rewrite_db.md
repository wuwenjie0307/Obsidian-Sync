---
date: "2026-06-12"
project: joyingbot-new
type: bug
status: investigation
severity: medium
tags: [bug, 3090-test-server, montage, subtitle-rewrite, mysql, crm]
aliases: ["3090 混剪标记与字幕二创失败排查"]
---

# 3090 混剪标记与字幕二创失败排查

## 图谱链接

- 项目: [[projects/joyingbot-new/00-项目概览|joyingbot-new]]
- 索引: [[projects/joyingbot-new/bugs/00-bugs-index|Bug 记录索引]]
- 运维入口: [[projects/joyingbot-new/docs/2026-06-12_3090_test_server_runbook|3090 测试服运行手册]]

## 问题描述

2026-06-12 在 3090 新测试服上从前端提交任务后，用户反馈第一个视频处理成功，并且前端使用了混剪；需要确认混剪标记是否传到后端。同时日志中出现一次“视频字幕二创失败”，需要判断失败属于哪个任务。

现场任务:

```text
job_id=1217
task_id=1191
time=2026-06-12 11:31:46~11:31:48
generate_source=2
```

## 现场证据

CRM 素材库新接口返回的素材字段:

```text
id=659
job_id=1217
task_id=1191
material_type=2
material_subtitle=还能领100块立减券，
is_mix_material=0
is_lip_sync=0
```

后端同步代码会直接把 CRM 返回的字段落库:

```text
m_record.is_mix_material = m.get("is_mix_material")
m_record.is_lip_sync = m.get("is_lip_sync")
```

因此本次后端确实收到了混剪相关字段，但该素材的 `is_mix_material` 是 `0`，不是 `1`。

任务接口侧同步成功:

```text
11:31:47 [generate_video_task][同步数据] job_id=1217 数据同步完成并提交数据库, tasks=1
11:31:47 POST /crm/generate_video_task 200
11:31:48 [generate_video_task-async][start] job_id=1217 task_id=1191
11:31:48 materialSubtitleCallback resp_code=200
11:31:48 [字幕改写-skip(个人无需改写)] job_id=1217 task_id=1191 generate_source=2
11:31:48 [generate_video_task-async][end] job_id=1217 task_id=1191 cost_ms=432
```

这说明 `1217/1191` 生成任务内部没有字幕二创失败；它按个人任务逻辑跳过了字幕改写。

后续的字幕二创失败来自独立接口:

```text
11:36:08 POST /crm/rewrite_video_subtitle HTTP/1.1 500
```

错误链路:

```text
agent_config_service.py:41
Error querying database for model=COMMON, type=VIDEO_SCRIPT_ONE_NEW:
MySQL Connection not available.

crm_server.py:2041
_prompt_template: None

crm_server.py:2116
视频字幕二创失败（发生异常）
ValueError: Invalid template: None
```

## 当前判断

1. 混剪标记问题:
   - 后端已接收并记录 CRM 返回的 `is_mix_material` 字段。
   - 本次 CRM 返回 `is_mix_material=0`，所以后端不会把该素材当作显式混剪素材。
   - 如果前端确实勾选混剪，需要继续查前端到 CRM 素材库接口之间，为什么最终返回给 Bot 的 `is_mix_material` 仍是 `0`。

2. 字幕二创失败:
   - 不是 `job_id=1217 / task_id=1191` 生成任务内部失败。
   - 是一次独立 `/crm/rewrite_video_subtitle` 请求失败。
   - 直接原因是查询 prompt 配置 `COMMON / VIDEO_SCRIPT_ONE_NEW` 时 MySQL 连接不可用，导致 `_prompt_template=None`。
   - 代码随后把 `None` 传给 `SystemMessagePromptTemplate.from_template()`，触发 `ValueError: Invalid template: None`。

## 排查命令

按任务查混剪字段和调度侧混剪统计:

```bash
grep -RniC 80 -E "job_id=1217|task_id=1191|1191|1217|selected_mix_material_count|is_mix_material|混剪" \
  /data/project/crm.ai.joyingbot/logs /data/server_logs/supervisord 2>/dev/null | tail -n 500
```

查字幕二创失败上下文:

```bash
grep -RniC 120 -E "2026-06-12 11:36|文案二创传参|rewrite_video_subtitle|VIDEO_SCRIPT_ONE_NEW|MySQL Connection not available|Invalid template" \
  /data/server_logs/supervisord /data/project/crm.ai.joyingbot/logs 2>/dev/null
```

临时恢复字幕二创接口可先重启 Bot 接口服务，重建 DB 连接池:

```bash
sudo supervisorctl restart ai_botserver
sudo supervisorctl status
```

重启后重新触发 `/crm/rewrite_video_subtitle`，确认是否能取到 prompt 并返回 200。

## 后续建议

- 前端/CRM 联调确认混剪勾选后，素材库接口返回给 Bot 的 `is_mix_material` 是否应为 `1`。
- Bot 后端可考虑在 `/crm/rewrite_video_subtitle` 中对 `_prompt_template` 为空做显式错误处理，避免底层 `Invalid template: None`。
- 对 `agent_config_service.get_prompt()` 的 DB 连接不可用问题做连接池恢复或重试，避免单次 MySQL 连接失效导致前端一直显示生成中。

## 相关文件

- `router/crm_server.py`
- `router/crm_request_util.py`
- `common/agent_config_service.py`
- `pojo/models.py`
- `scheduler/collect_scheduler.py`
