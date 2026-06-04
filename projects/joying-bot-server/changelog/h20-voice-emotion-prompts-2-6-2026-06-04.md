---
date: "2026-06-04"
tags: [changelog, h20, voice-clone, voxcpm, prompt, test]
---

# h20 亲切/热情/激昂/严肃/喜悦提示词上线验证

## 改动类型

- [ ] 新功能
- [ ] Bug 修复
- [ ] 重构
- [x] 配置变更

## 改动内容

本次将 VoxCPM 音色克隆情绪提示词中 `voice_emotion=2-6` 更新为与悲伤/愤怒同一风格的长版提示词：

- `2` / 亲切：声音柔和放松，近距离交谈、语速平缓、尾句轻收、气息稳定。
- `3` / 热情：声音明亮饱满，语速稍快、节奏轻快上扬、气息充沛。
- `4` / 激昂：声音坚定有力，语速逐渐加快、重音有冲击力、短促停顿、音调上扬。
- `5` / 严肃：声音低沉沉稳，正式陈述、语速适中偏慢、咬字清楚、气息压稳。
- `6` / 喜悦：声音轻快明亮，带笑意、语速轻快、尾音上扬、节奏跳跃。

GitLab `test` 已更新到：

```text
7dae3c4f Merge origin/test into lucky-test/voxcpm-default-speed-prompt
```

h20 当前 Jenkins 软链：

```text
/data/project/test_ai_botserver -> /data/project/test_ai_botserver.20260604185023
```

## h20 重启与验证

用户确认后，于 h20 重启 8 个 VoxCPM 容器：

```text
2026-06-04 19:19:50 restart begin
2026-06-04 19:20:10 restart done

8120 voxcpm-api-h20-test
8122 voxcpm-api-h20-test-2
8124 voxcpm-api-h20-test-3
8126 voxcpm-api-h20-test-4
8128 voxcpm-audition-api-h20-test-1
8129 voxcpm-audition-api-h20-test-2
8130 voxcpm-audition-api-h20-test-3
8131 voxcpm-audition-api-h20-test-4
```

live code 检查确认 8 个容器均已加载新版提示词：

```text
new_2=True
new_3=True
new_4=True
new_5=True
new_6=True
sad=True
angry=True
voice_volume_log=True
style_preview=True
```

8 个 VoxCPM 容器 health 全部 OK：

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

## 烟测结果

直接调用 8128 试听池：

```text
POST http://127.0.0.1:8128/v1/clone-voice
voice_emotion=2
voice_speed=1.0
voice_volume=50
HTTP=200
CONTENT_TYPE=audio/wav
BYTES=307244
TIME=1.750s
```

8128 容器日志确认新版亲切提示词进入模型输入：

```text
mode=controllable emotion_id=2 voice_speed=1.0 voice_volume=50
raw_text_len=24 styled_text_len=87 style_prefix_len=63 reference_text_len=0
```

## 影响范围

- 影响 h20 VoxCPM 可控克隆模式中 `voice_emotion=2-6` 的风格控制提示词。
- 悲伤/愤怒继续保持此前已验证的长版提示词。
- 默认高保真路径不扩大改动面。
- 视频池 `8120/8122/8124/8126` 与试听池 `8128-8131` 均已加载新版代码。

## 相关 Commit

- `7dae3c4f Merge origin/test into lucky-test/voxcpm-default-speed-prompt`
- `dcbac65b fix: refine VoxCPM emotion prompts`
