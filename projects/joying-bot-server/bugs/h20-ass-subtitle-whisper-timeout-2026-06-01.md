---
date: "2026-06-01"
status: fixed
severity: high
tags: [bug, h20, video-generation, subtitles, whisper]
---

# h20 ASS 字幕 Whisper 超时导致视频任务卡住

## 问题描述

h20 测试服视频生成已经完成 VoxCPM 音色克隆和 LatentSync 唇形同步，但在 ASS 字幕合成阶段卡住。任务 `job_id=946` / `task_id=937` 的 60.733333 秒中间视频，在 `audio_to_subtitle2.py` 的 Whisper Word Timestamps 阶段等待 1800 秒后超时，最终回调 CRM 为“字幕生成阶段失败”。

## 复现步骤

1. CRM 创建视频任务，Bot 通过 `/crm/generate_video_task` 入库并由 `ai_botserver_sch` 调度。
2. h20 先完成 VoxCPM 音频生成、LatentSync 视频合成和 30fps 转换。
3. 进入 `generate_ass_from_video`，调用 `transcribe_async(..., word_timestamps=True, model_name="medium")`。
4. Whisper worker 在 1800 秒内未返回，`res_q.get(timeout=1800)` 超时。

## 期望行为

60 秒左右视频的字幕识别和对齐应在可接受时间内完成，任务继续执行字幕烧录、BGM、封面、上传和 CRM 成功回调；失败时也应释放 `t_comfyui_config` 调度锁。

## 实际行为

- 2026-06-01 09:16:14：任务 937 开始识别音频 `Word Timestamps`。
- 2026-06-01 09:46:14：`Whisper 进程响应超时或发生异常`，刚好 1800 秒。
- h20 GPU0 占用约 30GB 显存，但当时 GPU 利用率为 0%，scheduler/worker CPU 异常偏高，Whisper 子进程出现 defunct。
- DB 当前显示 `task_status=2`、`callback_status=1`、`t_comfyui_config.id=1 is_active=2`，说明失败回调发出后，本地任务状态和调度锁没有正常落库释放。

## 原因

当前初步根因不是 h20 硬件配置不够，而是测试服字幕路径和生产不同：

- h20：`router/service/video_server2/audio_to_subtitle2.py` 直接导入 `whisper_thread_pool.transcribe_async`，在 `ai_botserver_sch` 进程下启动本地 multiprocessing worker。
- 生产：`audio_to_subtitle2.py` 导入 `model_whisper_server.whisper_transcribe_post`，调用本机 `http://127.0.0.1:8188/whisper/transcribe` 独立 Whisper 服务。
- 生产 8188 服务由 `/data/zjh/video_server_model_overseas/whisper_service.py` 提供；现有服务日志样例显示 `word_timestamps=True` 的请求核心耗时约 0.66 秒。该样例不等价于 h20 这条 60 秒视频，但能证明生产走的是独立模型服务路径。
- h20 这次 60.733333 秒中间视频在本地 worker 中 1800 秒未完成，说明不是正常慢，而是本地 Whisper Word Timestamps/进程通信/子进程状态进入异常慢或卡死状态。

## 解决方案

待实施。建议优先级：

1. 先修复失败后的资源释放：字幕失败时必须回滚 session 并释放 `t_comfyui_config.is_active=1`，避免后续任务一直显示“没有可用配置”。
2. 将 h20 字幕识别路径对齐生产：部署或复用独立 Whisper HTTP 服务，再让 h20 的 `audio_to_subtitle2.py` 通过 `model_whisper_server.py` 调用服务，避免在 scheduler 进程内长期跑 Whisper worker。
3. 如果独立服务仍慢，再评估降低字幕模型、取消 `word_timestamps=True` 改近似对齐，或基于已知文案和音频时长生成近似字幕。
4. 后续应给 Whisper 阶段增加更细日志：音频时长、模型加载耗时、ffmpeg 转 WAV 耗时、transcribe 核心耗时、对齐耗时。

## 优化点

- 配置日志当前会打印 token/header，后续应脱敏。
- 字幕失败后 DB 状态不一致，需要单独修复调度事务和锁释放逻辑。
- h20 和生产字幕实现应减少差异，避免测试服验证结果不能代表生产行为。

## 相关文件

- h20 `/data/project/test_ai_botserver/router/service/video_server2/audio_to_subtitle2.py`
- h20 `/data/project/test_ai_botserver/router/service/video_server2/whisper_thread_pool.py`
- 生产 `/data/project/prod_ai_autodone/router/service/video_server2/audio_to_subtitle2.py`
- 生产 `/data/project/prod_ai_autodone/router/service/video_server2/model_whisper_server.py`
- 生产 `/data/zjh/video_server_model_overseas/whisper_service.py`
- h20 日志 `/data/server_logs/supervisord/botserver_sch.out`

## 2026-06-01 进展记录

已在 h20 测试服验证修复：

- Bot 字幕链路已改为调用独立 Whisper 服务 `http://127.0.0.1:8188/whisper/transcribe`。
- 8188 Whisper 服务已从 CPU-only 的 `botserver` 环境切到 GPU 可用的 `joyingbot` 环境。
- 烟测显示 Whisper 日志出现 `绑定设备: cuda:0`，60 秒左右测试视频 `word_timestamps=false` 转写核心耗时约 9.45 秒。
- 任务 `job_id=947/task_id=938` 已完成完整视频生成链路：VoxCPM 声音克隆、LatentSync 唇形同步、字幕、BGM、封面、上传、CRM 完成回调。
- 最终视频地址：`https://videos-test.joyingai.cn/video/crm/20260601/user4_1780285072136_5a3d99f701e49b4d.mp4`
- 本地任务状态：`task_status=3`、`progress=100`、`callback_status=1`。
- 旧卡住任务 `job_id=946/task_id=937` 已标记失败，失败原因为 `subtitle generation failed before 8188 GPU fix`。

遗留问题：

- LatentSync 仍然偏慢。`task_id=938` 从调用 LatentSync 到返回大约 14 分钟；模型进度条本身约 52 秒，慢点主要在每次 `conda run -n latentsync python -m scripts.inference` 子进程启动、模型加载、视频预处理/后处理和输出合成。
- h20 当前 VoxCPM、Whisper、LatentSync 都集中在 GPU0，其他 GPU 基本空闲，后续应做 GPU 分配。
- 测试库有历史待处理任务积压，调度器会先领取旧任务，产品新任务可能排队。
- 发布阶段调用 `127.0.0.1:8015/publish_video_task` 失败，原因是发布服务未启动或该端口不可用；这不影响视频生成完成和 CRM 视频结果回调。
