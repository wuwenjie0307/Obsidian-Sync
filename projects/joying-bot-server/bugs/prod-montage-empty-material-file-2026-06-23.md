---
date: "2026-06-23"
project: "joying-bot-server"
type: bug
status: investigation
severity: high
tags: [bug, production, video-generation, montage, material, ffmpeg, crm]
aliases: ["prod-montage-empty-material-file-2026-06-23", "正式服混剪素材空文件导致失败"]
---

# 正式服混剪素材空文件导致失败

## 图谱链接

- 项目: [[projects/joying-bot-server/00-项目概览|joying-bot-server]]
- 索引: [[projects/joying-bot-server/bugs/00-bugs-index|Bug 记录索引]]

## 问题描述

2026-06-23 排查正式服用户 `real_name = 100` 多条视频生成失败。CRM/前端看到的失败原因是“混剪处理阶段失败”。

最终定位到：混剪素材库里有一条视频素材 URL 能访问，但文件本身是空文件或未上传完整。任务合成过程中一旦选中这条素材，系统下载后无法读取视频内容，于是整条任务失败。

问题素材：

```text
https://files.joyingai.cn/crm/20260618/user106_1781750280613_1bd0f848d6b89e74.mov
```

面向客户的解释口径：

```text
这次是混剪素材里有一条视频文件异常，系统读取不到完整内容，所以合成中断了。不是账号或操作问题，处理掉这条异常素材后重新生成即可。
```

## 影响任务

正式库 `t_video_generate_task` 中 `real_name = '100'` 最近任务里，以下任务失败原因为 `混剪处理阶段失败`，都命中同一个异常素材：

| task_id | job_id | 混剪素材数 | 失败位置 | 日志时间 |
|---:|---:|---:|---:|---|
| 15182 | 16975 | 42 | 9/42 | 2026-06-22 14:05:17 |
| 15253 | 17059 | 36 | 4/36 | 2026-06-22 15:23:43 |
| 15302 | 17109 | 28 | 9/28 | 2026-06-22 16:58:46 |
| 15311 | 17120 | 23 | 13/23 | 2026-06-22 17:34:16 |
| 15314 | 17125 | 29 | 2/29 | 2026-06-22 17:37:54 |

另外，2026-06-23 当天新任务 `task_id=15542 / job_id=17434` 的 `Montage_dict` 也包含同一个异常素材，需要关注是否后续同样失败。

## 复现步骤

1. 查询正式库：

```sql
SELECT *
FROM t_video_generate_task
WHERE real_name = '100'
ORDER BY updated_time DESC
LIMIT 100;
```

2. 找到失败任务的 `task_id/job_id`，到正式服 scheduler stdout 日志中按 task_id 搜索。
3. 在日志里可以看到：素材 URL 下载完成后，进入混剪视频静音处理，然后 ffmpeg 读取失败。
4. 直接探测问题素材 URL，可稳定复现不可读。

## 期望行为

异常素材不应导致用户无法理解的“混剪处理阶段失败”。理想行为至少满足其中之一：

1. 素材上传/入库前校验文件不是空文件，且能被视频工具正常读取。
2. 后端合成时遇到单条异常混剪素材，可记录并跳过，继续处理其它素材。
3. 如果跳过素材，日志或回调里能标明被跳过的 `material_id/source_url/原因`，方便客服和前端排查。

## 实际行为

当前正式服合成逻辑在处理混剪素材时逐条下载并处理：

1. 从 CRM 素材接口同步 `material_source_url` 到本地 `t_video_material_template`。
2. 生成任务时把这些素材组装成 `Montage_dict`。
3. 合成过程中下载素材 URL 到 `/tmp/*.mov`。
4. 调用 ffmpeg 做静音处理。
5. 如果素材是空文件或不可读，ffmpeg 报错，整条任务失败。

典型日志：

```text
检测到 URL，正在下载: https://files.joyingai.cn/crm/20260618/user106_1781750280613_1bd0f848d6b89e74.mov
下载完成: /tmp/xxx.mov
混剪视频 N/M 下载完成，开始进行视频静音处理
[视频生成][混剪处理] 失败，具体错误信息: ffmpeg failed when removing audio
moov atom not found
/tmp/xxx.mov: Invalid data found when processing input
```

## 原因

根因是素材 URL 对应的源文件异常：HTTP 返回成功，但文件大小为 0。

正式服探测结果：

```text
HTTP/1.1 200 OK
Content-Type: video/quicktime
Content-Length: 0
ETag: "d41d8cd98f00b204e9800998ecf8427e"
```

`d41d8cd98f00b204e9800998ecf8427e` 是空内容的常见 MD5。`ffprobe` 对该 URL 也直接报：

```text
moov atom not found
Invalid data found when processing input
```

所以本次不是账号问题，也不是“素材太多”本身导致。素材多只是更容易选到这条坏素材；直接原因是混剪素材不可读。

## 数据库证据

`real_name='100'` 的失败任务里，每条失败任务都在 `t_video_material_template` 命中这一个 URL，且每个任务只命中一次：

| task_id | job_id | total | bad_url_count |
|---:|---:|---:|---:|
| 15182 | 16975 | 42 | 1 |
| 15253 | 17059 | 36 | 1 |
| 15302 | 17109 | 28 | 1 |
| 15311 | 17120 | 23 | 1 |
| 15314 | 17125 | 29 | 1 |

对应素材记录：

| material_id | task_id | job_id | subtitle 摘要 |
|---:|---:|---:|---|
| 13870 | 15182 | 16975 | 所以我对南部新城产品困局的判断是... |
| 13997 | 15253 | 17059 | 能不能加梯，要看楼栋条件... |
| 14100 | 15302 | 17109 | 买房不是给板块投票... |
| 14172 | 15311 | 17120 | 还是现在的老房子住得太憋屈... |
| 14212 | 15314 | 17125 | 前两年交付的三代宅产品... |

## 日志证据

正式服当前运行目录：

```text
/data/project/prod_ai_botserver -> /data/project/prod_ai_botserver.20260616092618
```

本次主要日志不是旧文档里的 `/data/project/prod_ai_autodone/logs/run.log`，而是：

```text
/data/server_logs/supervisord/botserver_sch.out.*
```

关键窗口：

```text
/data/server_logs/supervisord/botserver_sch.out.10:429208-429228  task_id=15182
/data/server_logs/supervisord/botserver_sch.out.9:706715-706732   task_id=15253
/data/server_logs/supervisord/botserver_sch.out.7:162100-162119  task_id=15302
/data/server_logs/supervisord/botserver_sch.out.7:181064-181083  task_id=15311
/data/server_logs/supervisord/botserver_sch.out.7:182592-182609  task_id=15314
/data/server_logs/supervisord/botserver_sch.out:89085-89086     task_id=15542 Montage_dict 含同一素材
```

## 素材来源接口线索

本地表 `t_video_material_template.material_source_url` 不是合成过程生成的，而是从 CRM 素材接口同步进来的。

代码线索：

- `scheduler/collect_scheduler.py` 的 `sync_crm_video_generate_tasks()` 会调用 `get_crm_video_material_templates_list()`。
- `router/crm_server.py` 的 `/generate_video_task` 单 job 同步逻辑会调用 `get_crm_video_material_usertask_list()`。
- 两处都会把接口返回的 `material_source_url/material_subtitle/is_mix_material` 写入 `t_video_material_template`。

接口线索：

```text
/crm/agent/pc/video/materialTemplatesList
/crm/agent/pc/video/materialUsertaskList
```

给前端/素材同事的对接口径：

```text
请检查素材上传或素材库接口返回的这条素材：
https://files.joyingai.cn/crm/20260618/user106_1781750280613_1bd0f848d6b89e74.mov

现在这个 URL 返回 200，但 Content-Length 是 0，文件本身为空/不完整。后端合成时会从素材接口同步 material_source_url，混剪时再下载这个 URL，所以需要在素材上传/入库或素材接口返回前拦住这类空文件。
```

## 解决方案

当前已确认根因，尚未改代码。

短期处理：

1. 从素材库移除或替换这条异常素材。
2. 对失败任务重新生成。
3. 如果 `15542/17434` 还在处理或后续失败，优先检查是否同样命中该素材。

后端兼容方案：

1. 简单版：合成过程中单条混剪素材不可读时跳过，继续处理后续素材。
2. 稳妥版：跳过时记录 `task_id/job_id/material_id/source_url/subtitle/原因`。
3. 完整版：增加阈值和回调，例如跳过素材数量、是否允许全部素材异常时继续生成、是否回传给前端展示。

时间评估：

```text
基础跳过异常素材：约半天到 1 天
带清晰日志和跳过明细：约 1 天
前端展示/回调跳过详情：约 1-2 天，需产品和前端配合
```

## 优化点

1. 上传侧校验：不允许 0 字节文件入库。
2. 素材接口校验：`materialTemplatesList/materialUsertaskList` 返回前过滤或标记不可用素材。
3. 后端生成侧兜底：下载完成后检查文件大小，必要时用 `ffprobe` 检查可读性。
4. 错误信息增强：不要只写“混剪处理阶段失败”，至少内部日志要带具体 URL 和素材 ID。
5. 任务状态口径：如果跳过素材仍生成成功，需要明确是否通知前端“跳过了几条素材”。

## 验证结果

已完成只读验证：

1. 正式库查询确认 5 条失败任务均为 `混剪处理阶段失败`。
2. 素材表确认 5 条失败任务都包含同一个异常 URL。
3. 正式服日志确认失败点均为该 URL 下载后，ffmpeg 静音处理时报不可读。
4. 直接 `curl -I` 确认该 URL `Content-Length: 0`。
5. 直接 `ffprobe` 确认该 URL 报 `moov atom not found`。

未做操作：

1. 未修改正式库。
2. 未删除素材。
3. 未重启服务。
4. 未改代码。

## 本次排查步骤

1. 从 Obsidian 查正式服连接方式、生产环境架构、正式服视频合成失败排查文档。
2. 用正式库查询用户 `real_name='100'` 的最近 100 条视频任务。
3. 找到失败任务 `task_id/job_id` 和失败原因。
4. 查 `t_video_material_template`，统计每个失败任务的素材数量和异常 URL 命中情况。
5. 登录正式服，只读确认生产目录和日志位置。
6. 按 task_id 在 scheduler stdout 滚动日志中定位失败窗口。
7. 直接对异常 URL 做 HTTP 头和 `ffprobe` 探测。
8. 追代码确认素材来源接口：`materialTemplatesList/materialUsertaskList` 同步到 `t_video_material_template`。

## 本次踩坑记录

1. 不要只看旧正式服链路 `/data/project/prod_ai_autodone/logs/run.log`。本次任务实际在 `prod_ai_botserver` scheduler 链路，关键日志在 `/data/server_logs/supervisord/botserver_sch.out.*`。
2. DB 时间和日志时间相差 8 小时：DB 中 `updated_time=2026-06-22 06:05:17` 对应日志里约 `2026-06-22 14:05:17`。查日志时要换算北京时间。
3. CodeGraph 在当前 worktree 未初始化，不能依赖 `codegraph_context`，只能退回 `rg` 查代码。后续如要频繁做结构排查，可在项目里初始化 CodeGraph。
4. PowerShell 管道里把中文路径传给 Python 曾经乱码，读 Obsidian 中文文件名时优先用 PowerShell `Get-Content -LiteralPath ... -Encoding UTF8`。
5. 本地沙箱会拦截 SSH 网络连接，需要按权限流程放行；不要重复跑无权限 SSH。
6. SSH key 未通，使用临时环境变量中的密码走 Paramiko；不要把密码写进命令行、文件、Obsidian 或最终回复。
7. 正式服 Python 没有 `pymysql`，本地 Node 也没有 `mysql2`，最后用正式服 `mysql` CLI 并通过 stdin 输入密码查询。不要把数据库密码放在命令参数里。
8. `curl` 返回 200 不代表素材正常。本次关键点是 200 但 `Content-Length: 0`，必须同时看文件大小或用 `ffprobe` 验证。
9. “素材太多”不是直接根因。素材多只是更容易命中异常素材；根因是素材文件为空/不可读。
10. 当前后端错误对前端不友好，只显示“混剪处理阶段失败”，没有直接告诉是哪条素材坏了。

## 相关文件

- `scheduler/collect_scheduler.py`
- `router/crm_server.py`
- `crm/crm_request_util.py`
- `router/service/video_server2/video_work.py`
- `router/service/video_server2/video_tool.py`
- `pojo/models.py`

## 相关记录

- [[projects/joying-bot-server/docs/正式服视频合成失败日志排查|正式服视频合成失败日志排查]]
- [[projects/joying-bot-server/docs/生产环境架构|生产环境架构]]
- [[projects/joying-bot-server/bugs/prod-scheduler-montage-material-sync-2026-06-08|prod-scheduler-montage-material-sync-2026-06-08]]
- [[projects/joying-bot-server/bugs/h20-montage-material-filter-is-mix-flag-2026-06-12|h20-montage-material-filter-is-mix-flag-2026-06-12]]
