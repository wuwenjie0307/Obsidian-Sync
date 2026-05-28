---
date: 2026-05-28
tags: [changelog]
---

# 生产环境审查 + h20 并发保护

## 改动类型

- [x] 新功能
- [ ] Bug 修复
- [ ] 重构
- [x] 配置变更

## 改动内容

### 生产环境审查

确认生产服务器 (222.71.55.27) 代码基线：
- 生产目录：`/data/project/prod_ai_autodone/`
- 测试目录：`/data/project/test_ai_autodone/`
- 入口：`app_autodone_cn.py --env cn_prod/cn_test`（supervisor 管理，用户 joying）
- `video_work_Heygem_Whisper` 函数签名**无** voice_emotion/speed/volume 参数
- 生产无 `voxcpm_tts.py`、`latentsync_service.py` 文件
- 生产 TTS：qwen3 (DashScope) → qwen (cosyvoice-v3.5-plus) 回退
- 生产视频：VideoGenService → duix.avatar Docker
- 生产 Whisper：HTTP 服务调用 (`model_whisper_server.py`)
- `/data/projects/joying-bot-server/` 是独立的 chatbot 服务，与视频生成无关

### h20 API 并发保护

- VoxCPM API (8100)：`threading.BoundedSemaphore(2)`，最多 2 并发，超时 300s
- LatentSync API (8101)：`threading.BoundedSemaphore(1)`，串行执行，超时 600s
- 修改文件：`voxcpm_api.py`、`latentsync_api.py`
- 已上传到 h20，待重启服务

### 生产网络

- 222.71.55.27 无法直连 h20 的 8100/8101 端口（预期内，最终方案是本地部署）

## 影响范围

- `router/service/video_server/voxcpm_api.py`
- `router/service/video_server/latentsync_api.py`
- Obsidian：`docs/生产环境架构.md`（新增/更新）
