---
date: 2026-07-02
project: joying-bot-server
type: doc
tags: [h20, hyperframes, model-pool, timeout, retry, dingtalk]
aliases: [H20 模型超时隔离与重试行为]
---

# H20 模型超时隔离与重试行为

## 背景

H20 网感视频链路里，同一条 `t_comfyui_config` 配置同时承载：

- `config_value_audio`: VoxCPM 音频模型地址
- `config_value`: HeyGem/唇形模型地址

任务领取配置时会把 `is_active` 从 `1` 改为 `2`。不同阶段超时后的处理不一样，不能统一理解成“都隔离模型池”。

## 当前行为

| 阶段 | 触发条件 | 是否隔离模型池 | 任务状态 | 说明 |
|---|---|---|---|---|
| VoxCPM 音频模型 | VoxCPM busy/503/可识别的音频模型忙 | 是 | 回到 `task_status=0` | 通知“音频模型池卡死保护”，地址使用 `config_value_audio` |
| HeyGem 唇形模型 | busy 或 `VideoGenTimeoutError` | 是 | 回到 `task_status=0` | 通知“唇形模型池卡死保护”，地址使用 `config_value` |
| HyperFrames 等渲染槽 | `HF_RENDER_LOCK_TIMEOUT` | 否 | 回到 `task_status=0` | 前面的音频/唇形模型池会释放回可用 |
| HyperFrames 渲染进程 | CLI/Docker timeout 或非 0 退出 | 否 | 通常失败 | 属于后处理失败，不隔离音频/唇形模型池 |

## 音频和唇形超时

音频或唇形阶段被识别为模型忙/超时后：

1. 当前配置会被隔离：`is_active=0`。
2. 任务不会最终失败，会回到 `task_status=0`。
3. 下一轮调度会重新找 `is_active=1` 的健康模型池配置。
4. 如果还有其他空闲健康模型池，就会重新领取并执行。
5. 如果没有可用模型池，任务继续等下一轮。

收到钉钉通知后，需要人工或脚本重启对应容器，确认恢复后再把模型池配置改回可用。

## HyperFrames 等槽超时

HyperFrames 等渲染槽超时只说明后处理排队太久，不代表音频或唇形模型坏掉。

当前处理：

1. 音频已经生成完成。
2. 唇形已经生成完成。
3. 等 HyperFrames 渲染槽时触发 `HF_RENDER_LOCK_TIMEOUT`。
4. 任务回到 `task_status=0`，等待下轮重试。
5. 当前模型池配置不会隔离。
6. 外层 `finally` 会调用 `_release_comfyui_config`。
7. 如果配置仍是 `is_active=2`，会释放回 `is_active=1`。

所以 HyperFrames 排队不会占着前面的音频/唇形模型池。

## 是否会干扰结果

当前结论：旧容器继续跑一般不会污染新结果。

原因：

- 旧容器不会主动回调后端数据库。
- 调度已经不再等待旧结果，也不会读取旧结果。
- 唇形任务提交 code 带随机后缀，例如 `task_id_lip_xxx`，避免远端任务 ID 冲突。
- 新一轮任务会使用新的音频、唇形任务和输出路径。

主要副作用是：

- 被隔离的旧容器可能继续占 GPU/CPU/显存，需要重启。
- 如果只是 HyperFrames 排队超时，下一轮会重新跑音频和唇形，存在重复成本。

## 当前取舍

当前机制偏稳：

- 对模型忙/超时：隔离坏模型池，任务回队列重试。
- 对 HyperFrames 等槽：不隔离模型池，只回队列等待。
- 对旧容器结果：不信任、不复用，避免串结果。

代价是 HyperFrames 等槽超时后，已完成的音频和唇形会在下一轮重跑。

后续如果要降低重复成本，可以考虑做断点续跑：

- 保存已完成的 `heygem_standardized_video_path/url`。
- HyperFrames 等槽超时时，下轮直接从 HyperFrames 阶段继续。
- 但这会增加状态判断和清理复杂度，当前先不做。

## 相关代码点

- `scheduler/collect_scheduler.py`
  - `_get_available_comfyui_config`
  - `_quarantine_comfyui_config`
  - `_release_comfyui_config`
  - `_prepare_hyperframes_video_task`
  - `_process_single_video_task`
- `router/service/video_server2/video_gen_service.py`
  - `VideoGenTimeoutError`
  - `is_video_model_busy_error`
- `router/service/video_server/voxcpm_api.py`
  - `VOXCPM_QUEUE_TIMEOUT_SECONDS = 300`
- `router/service/video_server2/hyperframes_cli.py`
  - `hf_render_lock_timeout_seconds`
  - `HF_RENDER_LOCK_TIMEOUT`

## 图谱链接

- [[projects/joying-bot-server/00-项目概览|项目概览]]
- [[projects/joying-bot-server/docs/00-docs-index|Docs 索引]]
