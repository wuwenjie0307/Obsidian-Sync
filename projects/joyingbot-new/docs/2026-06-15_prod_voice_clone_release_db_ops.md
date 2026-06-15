---
date: "2026-06-15"
project: joyingbot-new
type: doc
tags: [doc, production, release, voice-clone, database, apidoc, voxcpm]
aliases: ["正式服音色克隆上线数据库操作说明"]
---

# 正式服音色克隆上线数据库操作说明

## 图谱链接

- 项目: [[projects/joyingbot-new/00-项目概览|joyingbot-new]]
- 索引: [[projects/joyingbot-new/docs/00-docs-index|参考文档索引]]
- 相关 Bug: [[projects/joyingbot-new/bugs/2026-06-15_voice_audition_route_and_pool_7001|测试服试听接口 404 与 VoxCPM 7001 端口失效]]
- 相关 Changelog: [[projects/joyingbot-new/changelog/2026-06-15_voice_clone_tts_area_unit_normalization|声音克隆 TTS 面积单位 m² 规范化]]

## 上线范围

- 上线项目: `crm.ai.joyingbot`
- 不要求单独上线: `crm.ai.admin`
- 代码基线: GitLab `origin/test`，核对提交 `2da06f38`
- 目标库: `zhugedata`
- 本次 DB 操作:
  - CRM 侧: 新增音色字段。
  - AI/bot 侧: 核验/补齐模型池配置，不新增字段。

## CRM 侧 DDL

执行前先确认字段是否已存在；如果线上已有 `voice_emotion / voice_speed / voice_volume`，不要重复执行。

```sql
ALTER TABLE `crm_agent_video_userprofile_source`
    ADD COLUMN `voice_emotion` tinyint(4) NOT NULL DEFAULT '1' COMMENT '语音情绪:1正常2亲切3热情4激昂5严肃6喜悦7悲伤8愤怒' AFTER `voice_file_url`,
    ADD COLUMN `voice_speed` decimal(4,2) NOT NULL DEFAULT '1.00' COMMENT '语速倍率' AFTER `voice_emotion`,
    ADD COLUMN `voice_volume` int NOT NULL DEFAULT '50' COMMENT '音量(0-100)' AFTER `voice_speed`;

ALTER TABLE `crm_agent_video_generate_task`
    ADD COLUMN `voice_emotion` tinyint(4) NOT NULL DEFAULT '1' COMMENT '语音情绪:1正常2亲切3热情4激昂5严肃6喜悦7悲伤8愤怒' AFTER `voice_file_url`,
    ADD COLUMN `voice_speed` decimal(4,2) NOT NULL DEFAULT '1.00' COMMENT '语速倍率' AFTER `voice_emotion`,
    ADD COLUMN `voice_volume` int NOT NULL DEFAULT '50' COMMENT '音量(0-100)' AFTER `voice_speed`;
```

## AI/bot 侧配置核验

`t_comfyui_config` 本次不改表结构，只核验/补齐配置。

查询视频生成模型池:

```sql
SELECT id, config_key, config_value_audio, config_value, is_active, type, description, updated_time
FROM zhugedata.t_comfyui_config
WHERE config_key = 'comfyui_url'
ORDER BY id;
```

查询声音试听模型池:

```sql
SELECT id, config_key, config_value_audio, config_value, is_active, type, description, updated_time
FROM zhugedata.t_comfyui_config
WHERE config_key = 'voice_audition_url'
ORDER BY id;
```

如果生产库没有 `voice_audition_url`，按生产实际 VoxCPM 试听端口插入:

```sql
INSERT INTO zhugedata.t_comfyui_config
  (config_key, config_value_audio, config_value, is_active, description, type, created_time, updated_time)
VALUES
  ('voice_audition_url',
   'http://127.0.0.1:<生产试听VoxCPM端口>',
   'http://127.0.0.1:<生产试听VoxCPM端口>',
   1,
   'prod voice audition voxcpm 1',
   2,
   NOW(),
   NOW());
```

如有不可用试听端口，先禁用旧端口，再启用健康端口:

```sql
UPDATE zhugedata.t_comfyui_config
SET is_active = 0, updated_time = NOW()
WHERE config_key = 'voice_audition_url'
  AND config_value_audio = 'http://127.0.0.1:<不可用端口>';

UPDATE zhugedata.t_comfyui_config
SET is_active = 1, updated_time = NOW()
WHERE config_key = 'voice_audition_url'
  AND config_value_audio IN (
    'http://127.0.0.1:<健康试听端口1>',
    'http://127.0.0.1:<健康试听端口2>'
  );
```

## 上线前后核验

上线前确认没有长期模型池锁:

```sql
SELECT id, config_key, config_value_audio, config_value, is_active, description, updated_time
FROM zhugedata.t_comfyui_config
WHERE is_active = 2
  AND config_key IN ('comfyui_url', 'voice_audition_url')
ORDER BY id;
```

上线前确认没有正在跑的视频任务:

```sql
SELECT id, job_id, task_id, task_status, progress, callback_status,
       publish_call_status, created_time, updated_time,
       LEFT(fail_reason, 300) AS fail_reason
FROM zhugedata.t_video_generate_task
WHERE task_status IN (0, 1, 2)
ORDER BY id DESC
LIMIT 20;
```

上线后确认模型池释放正常:

```sql
SELECT config_key, is_active, COUNT(*) AS count
FROM zhugedata.t_comfyui_config
WHERE config_key IN ('comfyui_url', 'voice_audition_url')
GROUP BY config_key, is_active
ORDER BY config_key, is_active;
```

## 注意事项

- `<生产试听VoxCPM端口>` 由运维按正式服实际健康端口替换，不要照抄测试服端口或测试库 id。
- `comfyui_url` 是正式视频生成池；`voice_audition_url` 是声音试听池。
- `is_active=1` 表示可用，`is_active=2` 表示运行中，`is_active=0` 表示禁用。
- 旧配置不要删除，停用改 `is_active=0`。
- VoxCPM 模型服务需要加载最新 `voxcpm_api.py`，否则音频峰值保护、长文本分段、面积单位规范化不会生效。
