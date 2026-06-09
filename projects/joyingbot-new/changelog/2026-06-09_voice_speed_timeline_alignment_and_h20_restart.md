---
tags: [project, changelog]
---

# 2026-06-09 voice speed timeline alignment and H20 restart

## 改动类型
- bug fix
- deployment verification

## 改动内容
- 将音色倍速上限收紧到 1.5 倍，移除 3.0 倍速路径。
- 在混剪链路中按克隆音频时长对齐模板视频时长，避免倍速后字幕和口播时长不同步。
- 混剪素材继续保持静音，不引入素材原声混入。
- 已将 test 分支最新提交 `a93615a1 fix: align voice speed video timeline` 合并并推送到 `origin/test`。

## 影响范围
- `router/service/video_server2/voice_params.py`
- `router/service/video_server2/video_work.py`
- `router/service/video_server2/video_time_align.py`
- `scheduler/collect_scheduler.py`
- 回归测试：`test/test_montage_material_audio_policy.py`、`test/test_scheduled_video_voice_params.py`、`test/test_voice_speed_timeline_alignment.py`

## 验证结果
- H20 当前 release: `/data/project/test_ai_botserver.20260609120308`
- `8100`、`8017`、`18017` 的进程 cwd 都指向当前 release
- `8100` 和 `8017` 健康检查返回 `{"status":"ok"}`
- 数据库任务表没有 `0/1/2` 待处理任务
- `t_comfyui_config` 没有 `is_active=2` 的模型池锁
- 最近 300 行日志未见 `ERROR` / `Exception` / `Traceback`

## 相关提交
- `a93615a1`
