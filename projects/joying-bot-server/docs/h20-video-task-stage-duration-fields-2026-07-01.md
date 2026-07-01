---
date: 2026-07-01
project: joying-bot-server
type: doc
tags: [doc, h20, database, video-task, hyperframes]
aliases: [H20 video task stage duration fields]
---

# H20 视频任务阶段耗时字段

## 背景

`t_video_generate_task` 需要展示每条视频生成任务在关键阶段的耗时，方便排查任务慢在哪里。

这次新增字段只记录核心阶段耗时，不改任务状态流转、不改 CRM 回调结构。

## 新增字段

| 字段 | 含义 | 写入链路 |
|---|---|---|
| `audio_generate_ms` | 音频阶段耗时，包含参考音频处理、参考音频 Whisper、VoxCPM 克隆音频、音频上传 | 极简路线、网感视频路线 |
| `lip_sync_ms` | 唇形/视频合成阶段耗时，包含素材视频处理、对口型生成、色彩/尺寸标准化 | 极简路线、网感视频路线 |
| `minimal_postprocess_ms` | 极简路线后处理整段耗时，包含字幕、混剪、BGM、封面拼接、最终上传 | 极简路线 |
| `hyperframes_postprocess_ms` | 网感路线后处理整段耗时，从 HeyGem 标准化视频完成后开始，到 HyperFrames 最终视频/封面上传完成结束 | 网感视频路线 |

已有字段仍保留：

| 字段 | 含义 |
|---|---|
| `whisper_timeline_ms` | HyperFrames Whisper 字幕时间轴生成耗时 |
| `analysis_ms` | HyperFrames 结构化分析耗时 |
| `hf_render_ms` | HyperFrames CLI 渲染耗时 |

注意：`whisper_timeline_ms + analysis_ms + hf_render_ms` 不是完整后处理耗时，会漏掉 BGM 下载、混剪素材预处理、最终上传等外围耗时。所以新增 `hyperframes_postprocess_ms` 作为和 `minimal_postprocess_ms` 对齐的整段 wall-clock 后处理耗时。

## SQL

```sql
ALTER TABLE t_video_generate_task
    ADD COLUMN audio_generate_ms INT NULL COMMENT 'Audio generation and voice clone cost in ms',
    ADD COLUMN lip_sync_ms INT NULL COMMENT 'Lip-sync video generation cost in ms',
    ADD COLUMN minimal_postprocess_ms INT NULL COMMENT 'Minimal route postprocess cost in ms',
    ADD COLUMN hyperframes_postprocess_ms INT NULL COMMENT 'HyperFrames postprocess total cost in ms';
```

代码仓库内也新增了迁移文件：

`sql/video_generate_task_stage_durations.sql`

## 测试库执行记录

2026-07-01 已在测试库 `zhugedata_test.t_video_generate_task` 添加字段。

执行时遇到过 `metadata lock`，原因是当时有正在更新 `t_video_generate_task` 的 SQL。处理方式：

1. 先确认没有残留 `ALTER TABLE` 等待会话。
2. 等待正在更新任务状态的 SQL 执行结束。
3. 再执行 `ALTER TABLE`。
4. 通过 `information_schema.COLUMNS` 确认 4 个字段存在。

确认结果：

```text
audio_generate_ms|int|YES|Audio generation and voice clone cost in ms
lip_sync_ms|int|YES|Lip-sync video generation cost in ms
minimal_postprocess_ms|int|YES|Minimal route postprocess cost in ms
hyperframes_postprocess_ms|int|YES|HyperFrames postprocess total cost in ms
```

## 正式库上线顺序

正式库也需要在部署新代码前先加字段。

推荐顺序：

1. 暂停或避开正在大量写 `t_video_generate_task` 的调度任务。
2. 在正式库执行上面的 `ALTER TABLE`。
3. 用 `information_schema.COLUMNS` 确认 4 个字段存在。
4. 再部署新代码并重启 scheduler。

如果先部署代码、后加字段，新代码写入这些字段时可能因为表结构缺字段导致任务失败。

## 相关代码

- `pojo/models.py`
- `router/service/video_server2/video_work.py`
- `scheduler/collect_scheduler.py`
- `test/test_video_task_stage_durations.py`
- `sql/video_generate_task_stage_durations.sql`

## 图谱链接

- [[projects/joying-bot-server/00-项目概览|项目概览]]
- [[projects/joying-bot-server/docs/00-docs-index|Docs 索引]]
