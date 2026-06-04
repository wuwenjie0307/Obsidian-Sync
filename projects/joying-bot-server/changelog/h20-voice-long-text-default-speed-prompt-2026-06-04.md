---
date: "2026-06-04"
tags: [changelog, h20, voice-clone, voxcpm, prompt, test]
---

# h20 长文案音色情绪默认语速提示修复

## 改动类型

- [ ] 新功能
- [x] Bug 修复
- [ ] 重构
- [ ] 配置变更

## 改动内容

本次处理“长文案下音色情绪变淡”的 P0 快速修复：非默认情绪下，如果用户没有主动调整语速，也就是 `voice_speed=1.0`，VoxCPM 可控克隆前缀不再额外追加 `自然语速`。

规则调整：

```text
emotion_id != 1 且 voice_speed == 1.0
=> (情绪提示词)正文

emotion_id != 1 且 voice_speed 为 0.75 / 1.25 / 1.5 / 2.0 / 3.0
=> (情绪提示词，语速提示词)正文

emotion_id == 1
=> 保持原默认行为
```

同时增加最小诊断日志字段，方便确认长文案是否仍需要 P1 分段生成：

```text
mode / emotion_id / voice_speed / raw_text_len / styled_text_len / style_prefix_len / reference_text_len
```

## Git 状态

- 本地相关提交：`4826469e fix: omit default VoxCPM speed prompt`。
- 已推送干净个人分支：`origin/lucky-test/voxcpm-default-speed-prompt-clean`，只包含：
  - `router/service/video_server/voxcpm_api.py`
  - `test/test_voxcpm_voice_style_prompt.py`
- 当前 `origin/test` 已包含旧分支合入后的提交链：
  - `9761c9ea fix: refine VoxCPM emotion prompts`
  - `f8591d0b fix: preserve Heygem video quality`
  - `1f030117 fix: omit default VoxCPM speed prompt`
- 因 `origin/test` 已经前进到 `1f030117`，本次没有再把 clean 分支合回 test，避免重复提交。

## 本地验证

```text
python -m unittest test.test_voxcpm_voice_style_prompt
Ran 15 tests OK
```

覆盖点：

- 非默认情绪 + `voice_speed=1.0` 不再拼 `自然语速`。
- 非默认情绪 + `voice_speed=1.25` 仍拼显式语速提示。
- 默认情绪 + 默认语速保持原行为。
- 已有括号提示词仍能被剥离，避免被当正文读出。
- `clone_voice` 日志包含最小诊断字段。

## h20 部署与重启

h20 当前 Jenkins 软链：

```text
/data/project/test_ai_botserver -> /data/project/test_ai_botserver.20260604181103
```

重启的 VoxCPM 容器：

```text
8120 voxcpm-api-h20-test
8122 voxcpm-api-h20-test-2
8124 voxcpm-api-h20-test-3
8126 voxcpm-api-h20-test-4
8128 voxcpm-audition-api-h20-test-1
8129 voxcpm-audition-api-h20-test-2
8130 voxcpm-audition-api-h20-test-3
8131 voxcpm-audition-api-h20-test-4
```

健康检查结果：第 7 轮全部 OK。

```text
8120 {"status":"ok"}
8122 {"status":"ok"}
8124 {"status":"ok"}
8126 {"status":"ok"}
8128 {"status":"ok"}
8129 {"status":"ok"}
8130 {"status":"ok"}
8131 {"status":"ok"}
```

live code 检查确认 8 个容器均已加载新逻辑：

```text
_should_append_speed_prompt
_get_style_prefix_len
style_prefix_len
mode=controllable emotion_id=...
```

注意：遗留裸机 `8110` 仍在旧目录 `/data/project/test_ai_botserver.20260603195816`，本轮没有重启它；本次验证目标是 8120/8122/8124/8126 视频池和 8128-8131 试听池。

## h20 烟测结果

### 直接 VoxCPM 试听池烟测

入口：`http://127.0.0.1:8128/v1/clone-voice`

共同参数：

```text
voice_emotion=3
voice_speed=1.0
voice_volume=50
reference_audio_url=https://files.joyingai.cn/crm/20260603/user4_1780465406179_ff23b59da031198a.mp3
```

结果：

| case | HTTP | text_len | 耗时 | WAV 大小 | 时长 |
|---|---:|---:|---:|---:|---:|
| short | 200 | 38 | 2.604s | 599084 bytes | 6.240s |
| long | 200 | 312 | 12.103s | 4638764 bytes | 48.320s |

日志关键证据：

```text
emotion_id=3 voice_speed=1.0 raw_text_len=38  styled_text_len=63  style_prefix_len=25
emotion_id=3 voice_speed=1.0 raw_text_len=312 styled_text_len=337 style_prefix_len=25
```

`styled_text_len = raw_text_len + style_prefix_len`，说明默认语速下没有再追加额外的 `自然语速`。

### Bot 试听接口烟测

入口：`http://127.0.0.1:8100/crm/voice_clone_audition`

结果：

| case | HTTP / code | text_len | 耗时 | CDN |
|---|---|---:|---:|---|
| short | 200 / 200 | 38 | 4.105s | https://videos-test.joyingai.cn/video/crm/20260604/user4_1780569361365_b3a67d6c4e5b2b1b.wav |
| long | 200 / 200 | 312 | 21.672s | https://videos-test.joyingai.cn/video/crm/20260604/user4_1780569382402_0fe0b26c82753869.wav |

Bot 日志确认两次都走试听池 `config_id=12 -> http://127.0.0.1:8128/v1/clone-voice`，参数为：

```text
emotion=3 speed=1.0 volume=50 reference_text_len=42
```

VoxCPM 容器日志确认两次 Bot 烟测也命中新逻辑：

```text
raw_text_len=38  styled_text_len=63  style_prefix_len=25 reference_text_len=42
raw_text_len=312 styled_text_len=337 style_prefix_len=25 reference_text_len=42
```

## 影响范围

- 影响 h20 VoxCPM 可控克隆模式的文本前缀拼接。
- 默认高保真路径不扩大改动面。
- 完整视频链路使用的 VoxCPM 视频池容器已重启并加载新逻辑。
- 试听链路使用的 8128-8131 专用 VoxCPM 容器已重启并通过 smoke test。
- 本轮没有实现长文案分段生成；如果产品仍反馈 300-500 字长文案情绪不明显，P1 再做 80-120 字分段生成与音频拼接方案。

## 后续待办

- [ ] 产品试听本次 short / long 两条 CDN，主观确认“热情”是否比修复前更明显。
- [ ] 如果长文案仍平淡，进入 P1：按 80-120 字切段，多次 generate 后拼接音频。
- [ ] 单独确认完整视频任务入库时能否写入非默认 `voice_emotion`；近期任务仍多为 `voice_emotion=1`，未覆盖非默认情绪的完整视频样本。
- [ ] 如需要让外部 48100 严格使用最新 Jenkins Bot 代码，另行重启 `8100` 到 `/data/project/test_ai_botserver.20260604181103`；本轮未重启 `8100`，但 Bot 试听接口烟测已返回成功。
