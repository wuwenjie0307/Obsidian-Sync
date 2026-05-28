---
date: 2026-05-28
tags: [changelog]
---

# 新模型代码适配 + h20 服务启动

## 改动类型

- [x] 新功能
- [ ] Bug 修复
- [ ] 重构
- [x] 配置变更

## 改动内容

1. **新增 VoxCPM TTS 客户端** — `router/service/video_server/voxcpm_tts.py`（v1/v2 各一份）
   - HTTP 调用 h20 VoxCPM API 做音色克隆
   - 内置 fallback：`voxcpm_api_base` 配置为空 → 自动走旧 DashScope

2. **新增 LatentSync 唇形同步客户端** — `router/service/video_server/latentsync_service.py`（v1/v2 各一份）
   - HTTP 调用 h20 LatentSync API 做唇形同步
   - 内置 fallback：`latentsync_api_base` 配置为空 → 自动走旧 VideoGenService

3. **API 服务迁移到 router/** — `voxcpm_api.py` + `latentsync_api.py` 从 `api_server/` 移入 `router/service/video_server/`，遵循项目目录惯例

4. **video_work.py v1/v2 添加注释切换** — import 区用注释标记新旧方案，一键注释/取消注释即可切换

5. **config.py 新增配置项** — `voxcpm_api_base` 和 `latentsync_api_base`（默认空 = 走旧方案）

6. **h20 服务启动** — VoxCPM API (8100) 和 LatentSync API (8101) 已手动启动并验证通过
   - 启动方式：nohup 后台运行（supervisor 待晋良配置）

## 影响范围

- `router/service/video_server/video_work.py` — v1 视频生成流程（注释级改动）
- `router/service/video_server2/video_work.py` — v2 视频生成流程（注释级改动）
- `app_config/config.py` — 新增两个配置项
- h20 服务器 — 两个 API 服务运行中（8100/8101）

## 相关 Commit

- 未推送（本地改动，通过 SCP 同步到 h20）
