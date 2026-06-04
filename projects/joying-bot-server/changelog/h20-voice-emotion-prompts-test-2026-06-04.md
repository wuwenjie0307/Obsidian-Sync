---
date: "2026-06-04"
tags: [changelog, h20, voice-clone, voxcpm, prompt, test]
---

# h20 音色克隆悲伤/愤怒提示词更新与试听验证

## 改动类型

- [ ] 新功能
- [ ] Bug 修复
- [ ] 重构
- [x] 配置变更

## 改动内容

本次按产品给定文案，更新 h20 测试服 VoxCPM 音色克隆情绪提示词中的两项：

- `voice_emotion=7` / 悲伤：`嗓音沙哑疲惫，像是哭过后强撑着开口，语速极慢，每句话之间有沉重的停顿，音调持续下沉，气息不稳，带着压抑已久的悲痛`
- `voice_emotion=8` / 愤怒：`压抑克制的愤怒，语速不快但咬字极重，每个字都像是从牙缝里挤出来，声音低沉绷紧，语调几乎不起伏，越平静越危险，像暴风雨前的压迫感`

同时将 `STYLE_PROMPT_MAX_CHARS` 从 `80` 调整到 `180`，避免新版长提示词在去重已有括号 style prompt 时被长度限制拦住。

### h20 现场处理

当前测试服 live 目录：

```text
/data/project/test_ai_botserver.20260604150743
```

已更新：

```text
/data/project/test_ai_botserver/router/service/video_server/voxcpm_api.py
```

现场备份：

```text
/data/project/test_ai_botserver/router/service/video_server/voxcpm_api.py.bak.20260604174452
```

重启并验证的 VoxCPM Docker 实例：

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

补充同步遗留裸机 `8110` VoxCPM。该进程 cwd 为：

```text
/data/project/test_ai_botserver.20260603195816
```

遗留目录备份：

```text
/data/project/test_ai_botserver.20260603195816/router/service/video_server/voxcpm_api.py.bak.20260604175553
```

`8110` 已重启，健康检查返回 ok。

### 本地代码同步

本地同步修改：

- `router/service/video_server/voxcpm_api.py`
- `test/test_voxcpm_voice_style_prompt.py`

本地验证：

```text
python -m unittest test.test_voxcpm_voice_style_prompt test.test_voice_clone_upload test.test_scheduled_video_voice_params
Ran 39 tests OK

python -m py_compile router/service/video_server/voxcpm_api.py
OK

git diff --check -- router/service/video_server/voxcpm_api.py test/test_voxcpm_voice_style_prompt.py
OK
```

备注：本地测试过程中仍有既有 `DeprecationWarning: invalid escape sequence '\s'`，本次未处理该无关 warning。

## 试听验证

测试入口：h20 本机 `http://127.0.0.1:8100/crm/voice_clone_audition`

测试正文：

```text
我真的没有想到，事情会变成这样。你先别说话，让我把这件事讲完。我们必须认真面对这个结果。
```

参考音频：

```text
https://files.joyingai.cn/crm/20260114/user4_1768388268372_3900b285138e29f3.m4a
```

固定参数：

```text
voice_speed=1.0
voice_volume=50
```

### 悲伤样本

参数：`voice_emotion=7`

结果：

```text
HTTP 200 / code=200
耗时: 4.758s
音频时长: 10.080s
文件大小: 967724 bytes
试听资源: config_id=12 / http://127.0.0.1:8128
CDN: https://videos-test.joyingai.cn/video/crm/20260604/user4_1780567692804_5e725e5accf6baae.wav
```

### 愤怒样本

参数：`voice_emotion=8`

结果：

```text
HTTP 200 / code=200
耗时: 4.380s
音频时长: 8.480s
文件大小: 814124 bytes
试听资源: config_id=12 / http://127.0.0.1:8128
CDN: https://videos-test.joyingai.cn/video/crm/20260604/user4_1780567697386_b4a37fcefa4f55fc.wav
```

### 日志确认

Bot 日志确认两次请求均走试听池 `config_id=12`：

```text
emotion=7 speed=1.0 volume=50 -> http://127.0.0.1:8128/v1/clone-voice
emotion=8 speed=1.0 volume=50 -> http://127.0.0.1:8128/v1/clone-voice
```

VoxCPM 容器日志确认新版 style prompt 进入模型输入：

```text
emotion_id=7 -> (嗓音沙哑疲惫，像是哭过后强撑着开口，语速极慢，每句话之间有沉重的停顿...)
emotion_id=8 -> (压抑克制的愤怒，语速不快但咬字极重，每个字都像是从牙缝里挤出来...)
```

最终健康检查：

```text
8100 {"status":"ok"}
8128 {"status":"ok"}
8129 {"status":"ok"}
8130 {"status":"ok"}
8131 {"status":"ok"}
```

## 影响范围

- 仅影响 h20 测试服 VoxCPM 音色克隆情绪提示词。
- 覆盖试听池和视频生成 VoxCPM 池：`8120/8122/8124/8126/8128/8129/8130/8131`。
- 同步补齐遗留裸机 `8110`，避免 fallback 或手动测试命中旧提示词。
- 不涉及生产环境。
- 不涉及数据库变更。
- 不记录任何 h20 登录密码或 sudo 密码。

## 相关 Commit

- 暂无。本地相关文件处于 staged 修改，尚未提交或推送。
