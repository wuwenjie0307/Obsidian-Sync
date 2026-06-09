---
date: "2026-06-09"
status: open
severity: high
tags: [bug, h20-test, voice-clone, todo]
---

# 试听与视频生成声音克隆行为不一致

## 问题描述
用户反馈同一套素材、同一情绪和默认语速下，声音克隆试听与正式视频生成听感不一致。当前确认视频生成与试听均传入 `emotion=7`、`speed=1.0`、`volume=50`，但视频生成使用 `comfyui_url` 资源池中的 VoxCPM，例如 `8120`；试听使用 `voice_audition_url` 资源池中的 VoxCPM，例如 `8128`。

## 复现步骤
1. 使用同一音色克隆素材生成试听音频，情绪选择悲伤，语速使用默认值。
2. 使用同一音色克隆素材生成视频，情绪选择悲伤，语速使用默认值。
3. 对比试听音频与视频成片中的克隆声音音色、语气、节奏一致性。

## 期望行为
试听与正式视频生成在同一音色、同一情绪、同一语速、同一音量参数下，应保持基本一致的克隆音色和情绪表现。试听池可以独立于视频模型池，但声音克隆行为应一致。

## 实际行为
两条链路走不同资源池和不同入口。若两个 VoxCPM 服务的模型版本、情绪 prompt 映射、参数解释、reference_text 处理或文本清洗逻辑存在漂移，同参数也可能得到不同听感。

## 环境信息
- 项目: `joyingbot-new`
- 日期: `2026-06-09`
- 测试服视频样例: `https://videos-test.joyingai.cn/video/crm/20260609/user4_1780996084916_8a4c1ff1f7692e38.mp4`
- 试听样例: `https://videos-test.joyingai.cn/video/crm/20260609/user4_1780996585867_eb70d68421ff5b9d.wav`
- 视频任务证据: `emotion=7 speed=1.0 volume=50 api_base=http://127.0.0.1:8120 text_len=313`
- 试听任务证据: `emotion=7 speed=1.0 volume=50 api_base=http://127.0.0.1:8128`

## 原因
根因方向不是语速参数被改动，而是试听链路和视频生成链路的声音克隆行为缺少一致性约束。两套资源池可以独立，但应共享同一套情绪配置、参数规范、reference_text 处理和日志观测字段。

## 解决方案
- 保留试听池与视频池资源隔离，避免试听占用视频模型组。
- 抽取共享的声音克隆请求封装，让试听和视频生成只在 pool selector 上不同。
- 补充日志字段，至少记录 `api_base`、`text_len`、`reference_text_len`、`voice_emotion`、`voice_speed`、`voice_volume`，并预留情绪 prompt 版本或 hash。
- 增加回归测试，验证试听与视频生成构造出的 clone-voice 请求核心参数一致。

## 优化点
- 后续可给 VoxCPM 服务增加 `/version` 或 `/health` 元信息，返回 code/model/emotion_prompt/text_cleaner 版本 hash。
- 调度侧可对试听池和视频池的 clone 服务版本 hash 做启动期或运行期告警。

## 相关文件
- `scheduler/collect_scheduler.py`
- `router/crm_server.py`
- `router/service/video_server2/video_work.py`
- `router/service/video_server2/voxcpm_tts.py`
- `router/service/voice_audition_pool_service.py`
