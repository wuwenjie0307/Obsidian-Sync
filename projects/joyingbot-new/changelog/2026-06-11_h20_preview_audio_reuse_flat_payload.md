---
date: 2026-06-11
project: joyingbot-new
type: changelog
tags: [changelog, h20, voice-clone, preview-audio, video-generation]
aliases: [H20 试听音频复用 flat payload]
---

# H20 试听音频复用 flat payload

## 改动类型

- 后端兼容性优化
- H20 测试环境部署与重启记录
- API 文档同步

## 改动内容

- 解决试听克隆接口生成的音频与最终视频中音频不一致的问题：最终视频创建链路现在可以直接接受前端已有的试听音频字段，不强制要求前端额外包一层 `reference_sample`。
- 在 `botserver/admin_server.py` 中新增 `_normalize_reference_sample_payload(reference_sample)`，统一规范化试听音频复用 payload。
- `create_digital_human_video` 在没有 `reference_sample` 时，会从请求体顶层字段中提取试听音频信息并转换为内部参考样本结构。
- 兼容字段包括 `audio_url`、`local_audio_url`、`preview_audio_url`、`ref_audio_url`、`reference_audio_url`、`audio_path`、`local_path`、`relative_path`、`path`、`emotion`、`emotion_label`、`source`、`sample_id`、`text`、`speech_text`、`preview_text`、`audition_text`、`voice_id`、`person_id`、`voice_name`、`metadata`、`ref_text`、`speaker_wav_text`、`speaker_text`。
- 保留已存在的 `reference_sample` 包装格式，避免影响旧调用方。
- 通过 apidoc/YApi 同步了 `POST /admin/app/preview_tts_clone` 的请求示例，将参考音频示例更新为本地上传路径风格。

## 影响范围

- `POST /admin/app/preview_tts_clone` 的试听音频结果可继续按前端现有字段传递。
- `POST /admin/app/create_digital_human_video` 可在不新增前端字段的情况下复用试听音频。
- 目标链路是“选择情绪生成试听音频 -> 保存该试听音频作为克隆音频 -> 最终视频复用同一音频”。
- 前端无需新增 `reference_sample` 包装字段，减少前后端再次对齐成本。

## 验证结果

- 本地回归：`python -m pytest tests/test_reference_sample_payload.py -q`，结果 `5 passed`。
- 本地组合回归：`python -m pytest tests/test_reference_sample_payload.py tests/test_audio_clone_helpers.py -q`，结果 `15 passed`。
- Git 分支：`feature/ai_v6.3.1_video`。
- 功能提交：`4423651 fix: reuse preview audio clone payload`。
- 已合并到 `test`，merge commit 为 `bb7f083`，并推送到 GitLab。
- H20 测试服务器 `/www/wwwroot/joyingbot` 已拉取最新 `test`。
- 已执行 `supervisorctl restart h20-botserver:h20-botserver_00` 重启服务。
- 重启后确认 8100 端口服务存活，`POST http://127.0.0.1:8100/admin/create_digital_human_video` 返回 `请先登录`，说明路由和进程已加载。
- 完整登录态端到端视频生成当时仍受已有任务锁影响：任务 `3810` 处于 `processing`，返回“任务正在执行中”，因此最终视频产出未在该轮完全跑完。

## 相关文件

- `botserver/admin_server.py`
- `tests/test_reference_sample_payload.py`
- `tests/test_audio_clone_helpers.py`

## 相关记录

- [[projects/joyingbot-new/changelog/2026-06-10_voice_audition_reference_sample|试听音频参考样本]]
- [[projects/joyingbot-new/changelog/2026-06-09_voice_clone_payload_consistency|语音克隆 payload 一致性]]
- [[projects/joyingbot-new/changelog/2026-06-09_h20_voice_clone_runtime_and_migration_status|H20 语音克隆运行与迁移状态]]

## 图谱链接

- [[projects/joyingbot-new/00-项目概览|项目概览]]
- [[projects/joyingbot-new/changelog/00-changelog-index|更新日志索引]]
## 2026-06-11 H20 端到端验证与测试服清理

### 端到端结论

- 14:14 左右完成的视频任务确认跑通了“试听音频保存为原音色 -> 作为克隆参考音频 -> 生成最终视频”的链路。
- 对应任务：`job_id=1195`，`task_id=1172`，本地任务表 `id=1389`。
- 任务状态：`task_status=3`，`progress=100`。
- 最终视频：`https://videos-test.joyingai.cn/video/crm/20260611/user4_1781158525852_f5788df17446dbff.mp4`。
- 用作音色克隆原音频的试听音频：`https://videos-test.joyingai.cn/video/crm/20260611/user4_1781158358486_75a63cadfb5f578a.wav`。
- 任务入库音色参数为默认值：`voice_emotion=1`，`voice_speed=1.0`，`voice_volume=50`。
- 运行日志中 `collect_scheduler.py` 的最终生成传参显示：`Original_audio_url=https://videos-test.joyingai.cn/video/crm/20260611/user4_1781158358486_75a63cadfb5f578a.wav`，说明最终视频确实使用该试听音频作为克隆参考音频。

### 链路语义确认

- 前端在试听阶段选择情绪、语速、音量等参数生成试听音频。
- 用户选择“使用本次试听作为音色样本”后，保存形象时应保存试听接口返回的音频 URL 作为 `voice_file_url`。
- 进入视频生成任务时，后端使用该 `voice_file_url` 作为原音色参考音频。
- 因为情绪、语速、音量效果已经体现在试听生成的音频里，正式视频生成时音色克隆参数使用默认值，避免对同一效果二次叠加处理。

### 测试服清理

- 原卡住任务：`id=1384`，`job_id=1191`，`task_id=1168`。
- 清理前状态：`task_status=2`，占用 `t_comfyui_config.id=17`，`is_active=2`。
- 已将该任务标为失败：`task_status=4`，并释放模型池 `config_id=17` 为 `is_active=1`。
- 中断期间遗留的新测试任务 `id=1390`，`job_id=1196`，`task_id=1173` 在清理前已自行生成成功，未强制改失败；对应 `config_id=16` 已自动释放。
- 最终复查：`task_status IN (0,1,2)` 无记录，`t_comfyui_config.is_active=2` 无记录。
- H20 服务状态：8100 与 8017 health 为 ok，18017 调度进程已重启成功并运行在 `/data/project/test_ai_botserver.20260611115843`。
