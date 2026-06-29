---
date: "2026-06-29"
project: "joying-bot-server"
type: bug
status: investigation
severity: high
tags: [bug, h20, duix, heygem, model-pool, vibevideo]
aliases: ["H20 DuiX 6005 task 1638 av_transfer 卡死"]
---

# H20 DuiX 6005 task 1638 av_transfer 卡死

## 图谱链接

- 项目: [[projects/joying-bot-server/00-项目概览|joying-bot-server]]
- 索引: [[projects/joying-bot-server/bugs/00-bugs-index|Bug 记录索引]]
- 相关容量记录: [[projects/joying-bot-server/docs/h20-hyperframes-concurrency-capacity-summary-2026-06-29|H20 HyperFrames 并发容量记录]]

## 问题描述

测试库 `task_id=1638` 失败，失败原因：

```text
VIDEO_PROCESSING_STALE_TIMEOUT: task stuck in processing for more than 2100s
```

该任务没有进入 HyperFrames 渲染阶段，而是卡在前置 DuiX/HeyGem 对口型容器 `duix-avatar-h20-test-6005`。

## 实际行为

- H20 后端已完成 VoxCPM 声音克隆、源视频下载、音视频对齐和上传。
- 09:59:59 提交到 `http://127.0.0.1:6005/easy/submit`。
- 容器 `6005` 接口保持可用，`/easy/query?code=1638` 持续返回 `status=1`、`progress=20`、`msg=视频特征提取完成`、`result=""`。
- 容器内部没有生成 `/code/data/temp/1638-r.mp4`。
- 后端 watchdog 在 2100 秒后把任务置失败，并把 `config_id=17` 隔离为不可用。

## 关键证据

1638 的输入不是长视频：

- 原始人像视频：`46.228s`
- 克隆音频：`23.360s`
- 提交给 DuiX 的对齐后视频：`23.358s`
- DuiX 读到的视频信息：`120fps / 1080x1920 / 23.358s`

容器内部文件：

```text
/code/data/temp/1638.wav              2.2M
/code/data/temp/1638.mp4              24M
/code/data/temp/1638/temp.wav         731K
/code/data/temp/1638/audio_data.npy   55M
```

说明音频下载、视频下载、音频转 16k、音频特征提取已经完成。

内部日志卡点：

```text
10:00:04 1638 -> get_aud_feat1 success, npy:/code/data/temp/1638/audio_data.npy
10:00:05 [1638]init_wh result :[0.9144]
10:00:05 1638 -> init_wh_process end
10:00:10 1638 ->av_transfer maybe blocked, restart...
10:00:10 1638 ->kill all process
10:00:11 1638 ->all process killed and restart
10:00:21 1638 ->result info [] ,continue ...
```

之后一直重复：

```text
1638 ->result info [] ,continue ...
```

## 原因判断

根因边界已确认：

- 不是 HyperFrames Docker runner。
- 不是 VoxCPM 声音克隆。
- 不是视频过长导致正常慢处理。
- 是 DuiX/HeyGem 容器内部 `av_transfer` 阶段被自身 watchdog 判定卡住。

更精确地说，DuiX 在完成音频特征和初始化后，`av_transfer` 没有正常开始持续产出帧处理日志，约 5 秒后触发 `av_transfer maybe blocked, restart...`。它随后杀掉内部 worker 并重启底层进程，但没有把当前任务标记为失败，也没有写入 `result_info`，导致外层 `/easy/query` 永远停在 `progress=20`。

对比任务 `1637`：

- `1637.mp4` 和 `1638.mp4` 的 md5 相同，视频输入一致。
- `1637` 同样是 `120fps / 23.358s / 2803 frames`，但正常生成 `1637-r.mp4`。
- 说明 120fps 可能会放大压力，但不是单独必现原因；更像 DuiX 内部 worker/队列偶发卡死或 watchdog 误杀后没有失败回传。

## 影响范围

- 只影响使用该 DuiX/HeyGem 容器实例的前置对口型阶段。
- 任务会占用模型池实例直到 H20 后端 stale watchdog 触发。
- 当前保护能隔离坏实例，但任务本身会失败，不能自动在其它模型实例重试。

## 解法建议

短期止血：

1. 保留现有 stale watchdog 隔离逻辑。
2. 对 `6005/easy/query` 增加“进度长时间不动”的识别：例如 `status=1` 且 `progress=20` 超过阈值，提前视为 DuiX 卡死。
3. 卡死时释放/隔离当前模型实例，让任务失败得更早，避免等满 2100 秒。
4. 对已经出现 `av_transfer maybe blocked` 的容器实例，建议运维侧重启对应 DuiX 容器后再恢复 `is_active=1`。

中期优化：

1. 如果业务允许，提交给 DuiX 前统一转成稳定的 30fps，降低 DuiX 对 120fps 素材的处理压力。
2. 让 DuiX 容器在自身 watchdog 重启 worker 时，同时把当前任务写入失败状态，而不是空轮询。
3. 后端可按错误类型区分：DuiX 卡死适合换实例重试；输入素材格式错误才直接失败。

难度判断：

- 后端止血难度：低到中，主要是加 no-progress timeout 和更明确的错误分类。
- DuiX 容器内部彻底修复难度：中到高，因为核心逻辑在编译后的 `.so` 模块里，无法直接像普通 Python 一样改源码。
- 30fps 标准化难度：中，需要确认不会影响口型质量和已成功的任务链路。

## 验证结果

已查：

- `duix-avatar-h20-test-6005` 仍在运行，接口可响应。
- 容器 CPU 约 `0.1%`，不是正在高负载处理。
- 任务 `1638` 仍在容器内部空轮询 `result_info []`。
- 今日只有 `1638` 出现 `av_transfer maybe blocked`。

## 相关文件

- H20 live runtime: `/data/project/test_ai_botserver.20260628231007`
- DuiX container: `duix-avatar-h20-test-6005`
- DuiX image: `guiji2025/duix.avatar:2.9`
- Backend caller: `router/service/video_server2/video_gen_service.py`
- HyperFrames 前置调用: `router/service/video_server2/video_work.py`
- Scheduler stale recovery: `scheduler/collect_scheduler.py`

## 相关记录

- [[projects/joying-bot-server/bugs/h20-hyperframes-duix-6005-busy-isolation-2026-06-22|h20-hyperframes-duix-6005-busy-isolation-2026-06-22]]
- [[projects/joying-bot-server/docs/h20-hyperframes-concurrency-capacity-summary-2026-06-29|h20-hyperframes-concurrency-capacity-summary-2026-06-29]]
