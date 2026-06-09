---
date: "2026-06-09"
tags: [project, changelog, h20-test, voice-clone, migration, ops]
---

# 2026-06-09 H20 voice clone runtime and migration status

## 改动类型
- bug fix
- deployment verification
- ops handoff note

## 当前状态
- 声音克隆业务层 payload 统一修复已提交到 `feature/ai_v6.3.1_video`，并已合并到远端 `test`。
- 当前远端 `origin/test` 与 `origin/feature/ai_v6.3.1_video` 均指向 `ef7fc984`。
- H20 当前 release 为 `/data/project/test_ai_botserver.20260609180518`。
- H20 8100 曾运行在旧 release `/data/project/test_ai_botserver.20260609164113`，已精确重启 8100。
- 重启后 8100、8017、18017 均指向 `/data/project/test_ai_botserver.20260609180518`。
- 健康检查：8100 与 8017 均返回 `{"status":"ok"}`。
- 任务队列：无 `task_status IN (0,1,2)` 活跃任务。
- 模型池：`comfyui_url` 4 个可用，`voice_audition_url` 4 个可用，无 `is_active=2` 锁。

## 声音克隆服务结论
- 红线镜像 `joying/voxcpm-api:h20-test` 是 VoxCPM 声音克隆 / TTS API 服务。
- 视频生成音色克隆与试听音色克隆使用同一个镜像、同一套服务代码、同一套情绪 prompt。
- 二者不是同一个容器实例，而是为了资源隔离分别启动不同容器和端口。

## 当前 VoxCPM 容器池
视频生成音色克隆池：
- `voxcpm-api-h20-test` -> 8120
- `voxcpm-api-h20-test-2` -> 8122
- `voxcpm-api-h20-test-3` -> 8124
- `voxcpm-api-h20-test-4` -> 8126

试听音色克隆池：
- `voxcpm-audition-api-h20-test-1` -> 8128
- `voxcpm-audition-api-h20-test-2` -> 8129
- `voxcpm-audition-api-h20-test-3` -> 8130
- `voxcpm-audition-api-h20-test-4` -> 8131

## VoxCPM 启动关键信息
- image: `joying/voxcpm-api:h20-test`
- network: `host`
- restart: `unless-stopped`
- command: `python /app/voxcpm_api.py --host 0.0.0.0 --port <port>`
- 关键挂载：
  - `/data/model_cache/huggingface:/root/.cache/huggingface`
  - `/data/video_tmp:/data/video_tmp`
  - `/data/project/test_ai_botserver/router/service/video_server/voxcpm_api.py:/app/voxcpm_api.py`
- 需要 NVIDIA Docker / GPU 环境。

## duix.avatar 结论
- `duix.avatar:2.9` 是视频唇形同步服务，不是声音克隆服务。
- 完整镜像名：`registry.hd-04.alayanew.com:8443/alayanew-5580740d-b175-49a9-9409-98b01b89bdc1/guiji2025/duix.avatar:2.9`
- 当前容器：
  - `duix-avatar-h20-test-6004` -> 宿主机 6004 映射容器 8383
  - `duix-avatar-h20-test-6005` -> 宿主机 6005 映射容器 8383
  - `duix-avatar-h20-test-6006` -> 宿主机 6006 映射容器 8383
  - `duix-avatar-h20-test-6007` -> 宿主机 6007 映射容器 8383

## 当前视频生成池配对
- VoxCPM 8120 + duix 6004
- VoxCPM 8122 + duix 6005
- VoxCPM 8124 + duix 6006
- VoxCPM 8126 + duix 6007

## 给运维的简短口径
- 如果只迁移试听 / 音色克隆，迁 `joying/voxcpm-api:h20-test` 即可，同时带上 HuggingFace 缓存、临时目录和挂载的 `voxcpm_api.py`，并准备 GPU/NVIDIA Docker 环境。
- 如果迁完整视频生成，还需要迁 `duix.avatar:2.9`，因为它负责唇形同步。
- `latentsync-api` 当前测试服主链路没有使用，可先不迁，除非后续要切回 LatentSync。
- 当前未执行任何迁移动作，只确认了 H20 现状、服务用途、容器池与迁移口径。

## 相关文件
- `router/service/video_server2/voxcpm_tts.py`
- `router/crm_server.py`
- `router/service/video_server/voxcpm_api.py`
- `scheduler/collect_scheduler.py`
