---
date: "2026-05-29"
status: fixed
severity: high
tags: [bug, h20, botserver, crm, voice-clone]
---

# /crm/voice_clone_audition botserver 500

## 问题描述

`/crm/voice_clone_audition` 在 botserver 上报 HTTP 500。

## 日志位置

h20 机器上查看：

```text
/data/server_logs/supervisord/ai_botserver.out
```

## 原因

待查。需要登录 h20 后从上述日志中定位最新 traceback。

## 解决方案

待查。

## 优化点

- 查询日志时不要复制完整配置内容，避免泄漏 password/token/key。
- 优先筛选 endpoint、Traceback、Exception、ERROR 关键字。

## 建议排查命令

```bash
grep -nE "voice_clone_audition|Traceback|Exception|ERROR|Error" /data/server_logs/supervisord/ai_botserver.out | tail -120
```

```bash
tail -200 /data/server_logs/supervisord/ai_botserver.out
```

## 2026-05-29 17:05 日志定位

已查看 h20：

```text
/data/server_logs/supervisord/ai_botserver.out
```

最新 500 根因：CRM 请求传入了不支持的 `voice_speed`。

日志关键信息：

```text
[voiceAudition] 调用 h20 API: url=http://127.0.0.1:8110/v1/clone-voice emotion=1 speed=0.5 volume=50
RuntimeError: h20 API 返回 400: voice_speed 仅允许 [0.75, 1.0, 1.25, 1.5, 2.0, 3.0]
POST /crm/voice_clone_audition HTTP/1.1 500
```

判断：

- VoxCPM API 正常返回了参数校验错误 `400`。
- botserver 当前把 h20 API 的 `400` 包成异常，最终对 CRM 返回 `500`。
- 直接绕过问题的方式是 CRM 不要传 `voice_speed=0.5`，改传允许值。

允许值：

```text
0.75, 1.0, 1.25, 1.5, 2.0, 3.0
```

后续优化：

- botserver 应在调用 h20 API 前先校验 `voice_speed`，非法参数直接返回 HTTP 400。
- 或者至少把 h20 API 的 4xx 错误透传为 400，不应包装成 500。

## 2026-05-29 字段范围确认

最终确认：`voice_speed=0.5` 不属于允许值。

允许范围：

```text
voice_emotion: 1-8，默认 1
voice_speed: 0.75 / 1.0 / 1.25 / 1.5 / 2.0 / 3.0，默认 1.0
voice_volume: 0-100，默认 50
```

语速不是只能加速：`0.75` 是减速档，`1.0` 是原速，大于 `1.0` 是加速。

代码层面需要确保非法参数返回 HTTP 400，不要包装成 500。

## 2026-05-29 代码修复

已提交并推送到 `origin/test`：

```text
3a00f6c6 fix: validate voice clone audition params
```

修复内容：

- `voice_emotion` 默认 `1`，只允许 `1-8`。
- `voice_speed` 默认 `1.0`，只允许 `0.75 / 1.0 / 1.25 / 1.5 / 2.0 / 3.0`。
- `voice_volume` 默认 `50`，只允许 `0-100`。
- botserver 在调用 h20 API 前先做参数校验。
- h20 API 返回 4xx 时，botserver 透传为 400，不再包装成 500。

说明：`voice_speed=0.5` 仍然不支持；`0.75` 是慢速档。
