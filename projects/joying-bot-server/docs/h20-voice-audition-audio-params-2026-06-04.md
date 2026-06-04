---
date: "2026-06-04"
tags: [h20, voice-clone, audition, voxcpm, crm, investigation]
---

# h20 最近克隆试听音频与传参对应记录

## 记录背景

2026-06-04 排查 h20 测试服最近通过前端服务生成的 `/crm/voice_clone_audition` 克隆试听音频，目标是把生成音频和实际传参一一对应。

本次查询的主要日志：

- h20 主机：`hgx19`
- Bot 日志：`/data/server_logs/supervisord/ai_botserver.out`
- 8100 手动入口日志：`/tmp/bot_8100_test_ai_botserver.log`
- VoxCPM 试听容器：`voxcpm-audition-api-h20-test-1`
- VoxCPM API：`http://127.0.0.1:8128/v1/clone-voice`

## 本地音频目录

已下载到本地项目目录：

```text
C:\Users\admin\Desktop\joyingbot-new-h20-model-pool-productionize\artifacts\h20_voice_audition_20260604_1604_1606
```

清单文件：

```text
C:\Users\admin\Desktop\joyingbot-new-h20-model-pool-productionize\artifacts\h20_voice_audition_20260604_1604_1606\manifest.json
```

## 最近成功 6 条试听记录

时间为北京时间。6 条均已下载并用 WAV 头校验，采样率均为 `48000 Hz`，声道均为单声道。

| 序号 | 时间 | 本地文件 | CDN URL | config_id | mode | reference_text_len | voice_emotion | voice_speed | voice_volume | 时长 |
|---:|---|---|---|---:|---|---:|---|---:|---:|---:|
| 1 | 2026-06-04 16:04:08 | `01_20260604_160408_emotion2_speed1p0_volume50.wav` | `https://videos-test.joyingai.cn/video/crm/20260604/user4_1780560309790_dcb5137164ece900.wav` | 12 | controllable | 42 | 2（亲切） | 1.0 | 50 | 4.16s |
| 2 | 2026-06-04 16:05:15 | `02_20260604_160515_emotion3_speed1p0_volume50.wav` | `https://videos-test.joyingai.cn/video/crm/20260604/user4_1780560377337_5dbb973e3582a3c5.wav` | 12 | controllable | 42 | 3（热情） | 1.0 | 50 | 3.04s |
| 3 | 2026-06-04 16:05:29 | `03_20260604_160529_emotion4_speed1p0_volume50.wav` | `https://videos-test.joyingai.cn/video/crm/20260604/user4_1780560391394_add68e3846f4c528.wav` | 12 | controllable | 42 | 4（激昂） | 1.0 | 50 | 3.84s |
| 4 | 2026-06-04 16:05:42 | `04_20260604_160542_emotion5_speed1p0_volume50.wav` | `https://videos-test.joyingai.cn/video/crm/20260604/user4_1780560403756_2675c8f75099f59f.wav` | 12 | controllable | 42 | 5（严肃） | 1.0 | 50 | 4.48s |
| 5 | 2026-06-04 16:06:01 | `05_20260604_160601_emotion6_speed1p0_volume50.wav` | `https://videos-test.joyingai.cn/video/crm/20260604/user4_1780560423181_82f7a314dd817c6c.wav` | 12 | controllable | 42 | 6（喜悦） | 1.0 | 50 | 5.44s |
| 6 | 2026-06-04 16:06:21 | `06_20260604_160621_emotion7_speed1p0_volume50.wav` | `https://videos-test.joyingai.cn/video/crm/20260604/user4_1780560443047_a7c198767d3a383f.wav` | 12 | controllable | 42 | 7（悲伤） | 1.0 | 50 | 4.80s |

## 共同传参

6 条共同使用的参考音频：

```text
reference_audio_url = https://files.joyingai.cn/crm/20260603/user4_1780465406179_ff23b59da031198a.mp3
```

共同参数：

```text
voice_speed = 1.0
voice_volume = 50
reference_text_len = 42
mode = controllable
api_url = http://127.0.0.1:8128/v1/clone-voice
config_id = 12
```

## 情绪编号口径

来自 `router/service/video_server/voxcpm_api.py`：

```text
1 = normal / 自然
2 = 亲切
3 = 热情
4 = 激昂
5 = 严肃
6 = 喜悦
7 = 悲伤
8 = 愤怒
```

## 排查结论

- 最新成功的 6 条试听都走 `config_id=12`，实际 VoxCPM 地址是 `8128`。
- 这 6 条是同一参考音频、同一语速、同一音量，只变更 `voice_emotion=2..7`。
- 生成音频的日志时长、下载后 WAV 头校验时长、文件大小均一致。
- Bot 日志没有记录完整 `text` 请求体，只记录了 `reference_text_len`、`voice_emotion`、`voice_speed`、`voice_volume`、`config_id`、VoxCPM 地址和 CSM URL。
- VoxCPM 容器日志有 `text` 前 50 字，但该日志里的中文片段本身不可读，不应当凭乱码还原完整 text。

## 后续建议

- 如果之后需要完整一一对应 `text`、`reference_audio_url`、`reference_text`、`voice_emotion`、`voice_speed`、`voice_volume` 和输出音频，建议在 `/crm/voice_clone_audition` 里新增一条脱敏结构化日志。
- 结构化日志不要打印完整音频内容或敏感配置，只记录请求参数摘要、URL、文本长度、输出 CDN、duration、size、config_id。
- 后续排查时优先筛：`grep -nF "[voiceAudition]" /data/server_logs/supervisord/ai_botserver.out`，避免宽泛 grep 把启动配置行带出来。
