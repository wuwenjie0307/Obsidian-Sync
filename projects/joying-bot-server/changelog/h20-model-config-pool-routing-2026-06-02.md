---
date: "2026-06-02"
tags: [changelog, h20, docker, scheduler, voxcpm, latentsync]
---

# h20 模型调用逻辑接入 t_comfyui_config 2026-06-02

## 背景

h20 测试服已经把 CRM 视频生成主流程改回生产式调度链路：

```text
/crm/generate_video_task -> 本地任务入库 -> scheduler 领取任务 -> t_comfyui_config 锁 -> 模型处理 -> CRM 回调
```

但此前 `t_comfyui_config` 主要只作为资源锁使用，实际 VoxCPM / LatentSync 调用地址仍主要来自全局配置：

```text
voxcpm_api_base
latentsync_api_base
```

这和生产服“领取到哪条可用模型服务配置，就调用哪条服务地址”的模型池逻辑还没有完全对齐。

## 本次改动

- `scheduler/collect_scheduler.py`
  - scheduler 领取到 `config_model` 后读取模型地址：
    - `config_value_audio` -> VoxCPM API base
    - `config_value` -> LatentSync API base
  - 调用 `video_work_Heygem_Whisper(...)` 时透传：
    - `voxcpm_api_base`
    - `latentsync_api_base`
  - `config_value` 为空时仍回退全局 `latentsync_api_base`，避免旧配置缺失时直接失败。

- `router/service/video_server2/video_work.py`
  - `video_work_Heygem_Whisper(...)` 新增可选参数：
    - `voxcpm_api_base`
    - `latentsync_api_base`
  - LatentSync 客户端优先使用传入的 `latentsync_api_base`。
  - VoxCPM 调用继续传递 `voice_emotion` / `voice_speed` / `voice_volume`，并额外传入 `voxcpm_api_base`。

- `router/service/video_server2/voxcpm_tts.py`
  - `clone_voice_and_synthesize(...)` 支持 `api_base` 覆盖。
  - 优先用调度传入地址；未传时继续回退全局 `voxcpm_api_base`。

- `test/test_scheduled_video_voice_params.py`
  - 新增 AST 级回归测试，确认：
    - scheduler 将模型地址传给 `video_work_Heygem_Whisper`
    - `video_work_Heygem_Whisper` 将地址传给 VoxCPM / LatentSync 客户端
    - VoxCPM 客户端支持 `api_base` 参数

## 验证结果

已在本地执行：

```text
python -m py_compile scheduler/collect_scheduler.py router/service/video_server2/video_work.py router/service/video_server2/voxcpm_tts.py router/service/video_server2/latentsync_service.py
python -m unittest test.test_scheduled_video_voice_params test.test_voice_clone_upload test.test_latentsync_timeout test.test_video_quality_pipeline
git diff --check
```

结果：

```text
py_compile: 通过
unit tests: Ran 26 tests, OK
git diff --check: 通过，仅 CRLF warning
```

## h20 后续配置

代码部署到 h20 后，测试库 `zhugedata_test.t_comfyui_config.id=1` 应配置为：

```sql
UPDATE zhugedata_test.t_comfyui_config
SET config_value_audio = 'http://127.0.0.1:8120',
    config_value = 'http://127.0.0.1:8121',
    is_active = 1
WHERE id = 1;
```

含义：

```text
config_value_audio -> VoxCPM Docker
config_value -> LatentSync Docker
```

## 当前对齐度

完成该改动后，h20 与生产服模型调用逻辑的对齐度预计从约 55%-60% 提升到约 80%-85%。

剩余差距主要在：

- 多条 Docker 服务池化还没扩起来。
- Docker 性能仍需继续和裸机对齐。
- 模型服务常驻预热、监控、失败重试等生产级运维细节还需要后续补齐。

## 2026-06-02 15:20 h20 验证补充

- 当前部署目录：`/data/project/test_ai_botserver.20260602145953`
- `ai_botserver`、`ai_botserver_sch` 均为 supervisor 运行状态。
- h20 本机健康检查通过：
  - Bot 8100：`/status/check -> {"status":"ok"}`
  - Bot 8017：`/status/check -> {"status":"ok"}`
  - VoxCPM Docker 8120：`/health -> {"status":"ok"}`
  - LatentSync Docker 8121：`/health -> {"status":"ok"}`
- 测试库 `t_comfyui_config.id=1` 当前配置：
  - `config_value_audio = http://127.0.0.1:8120`
  - `config_value = http://127.0.0.1:8121`
  - `is_active = 1`
- 最新验证任务：
  - `t_video_generate_task.id=1243`
  - `job_id=1040`
  - `task_id=1031`
  - `task_status=3`
  - `progress=100`
  - `callback_status=1`
  - 生成地址：`https://videos-test.joyingai.cn/video/crm/20260602/user4_1780384644704_f0178eaa0ba4c2fb.mp4`
- 日志证据：
  - `voxcpm_tts.py` 调用 `http://127.0.0.1:8120/v1/clone-voice`
  - `latentsync_service.py` 调用 `http://127.0.0.1:8121/v1/lip-sync`
  - `collect_scheduler.py` 在任务完成后释放 `config_id=1`，`is_active: 2 -> 1`

结论：h20 当前已经完成“调度领取 `t_comfyui_config` 空闲记录 -> 按记录里的 VoxCPM / LatentSync 地址调用 Docker 模型 -> 任务完成后释放锁”的闭环验证。和生产模型池调用逻辑的对齐度可按 80%-85% 估算。
