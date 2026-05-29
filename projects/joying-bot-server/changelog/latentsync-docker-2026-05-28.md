---
date: 2026-05-28
tags: [changelog]
---

# LatentSync Docker 化 + video_work 正式切换

## 改动类型

- [x] 新功能
- [ ] Bug 修复
- [ ] 重构
- [x] 配置变更

## 改动内容

1. **latentsync_api.py** — 支持 Docker/裸机双模式
   - 自动检测 conda，无 conda 时用 `sys.executable` 直接调 inference
   - 环境变量 `LATENTSYNC_DIR`、`LATENTSYNC_USE_CONDA`、`LATENTSYNC_CONDA_ENV` 可覆盖

2. **video_work.py (video_server2)** — 正式切换到新模型
   - TTS：VoxCPM 替代 DashScope qwen3-tts
   - 唇形同步：LatentSync 替代 duix.avatar Docker
   - voice_emotion/speed/volume 参数已透传
   - 旧方案代码注释保留（可回退）

3. **docker/latentsync/** — 新增 4 个文件
   - `Dockerfile`：CUDA 12.1 + PyTorch 2.5.1 + LatentSync 1.6
   - `docker-compose.yml`：单实例参考配置
   - `deploy.sh`：8 实例批量部署脚本（端口 6101-6108）
   - `README.md`：运维部署文档（构建、部署、验证、监控、回滚）

## 影响范围

- `router/service/video_server/latentsync_api.py`
- `router/service/video_server2/video_work.py`
- `docker/latentsync/*`（新增）

## 相关 Commit

- `de5a775a` feat: LatentSync Docker 化 + video_work 切换到新模型（joyingbot-new, feature/ai_v1_api_merge）
