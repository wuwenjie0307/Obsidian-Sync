---
date: "2026-06-01"
tags: [changelog, h20, crm, voice-clone, audition, asr]
---

# 试听接口增加参考音频 ASR

## 改动类型

- [ ] new feature
- [x] bug fix
- [ ] refactor
- [ ] config change

## 改动内容

- `/crm/voice_clone_audition` 入参不变，前端仍只需要传 `voice_file_url`、可选 `text`、`voice_emotion`、`voice_speed`、`voice_volume`。
- 后端内部收到 `voice_file_url` 后，会调用独立 Whisper 服务识别参考音频原文。
- ASR 成功时，把识别结果作为 `reference_text` 传给 h20 VoxCPM `/v1/clone-voice`，用于提升音色克隆稳定性。
- ASR 失败或返回空文本时，不阻断试听接口，降级为空 `reference_text` 继续生成。
- 这与完整视频生成链路已有的“参考音频 -> ASR -> reference_text -> VoxCPM”逻辑对齐。

## 影响范围

- 仅影响音色试听接口。
- 不改变前端传参。
- 不改变完整视频生成调度入口。
- 可能使试听接口多一次 Whisper 调用，耗时会比之前略增加；失败时会降级，不应直接导致试听失败。

## 验证

本地验证通过：

```powershell
python -m py_compile router\crm_server.py router\service\video_server2\audio_duration.py router\service\video_server2\model_whisper_server.py
python -m unittest test.test_scheduled_video_voice_params test.test_voice_clone_upload
git diff --check
```

GitLab `test` 已同步：

```text
295085a4 fix: add reference asr for voice audition
```

## 备注

- 本次没有暴露 `reference_text` 给前端或接口文档。
- 接口文档仍只需要说明 `text` 是非必填的目标合成文案。
- 后续如果要实现 VoxCPM 截图里的 Hi-Fi / 极致克隆模式，还需要单独确认 h20 当前 VoxCPM `generate()` 是否支持 `reference_wav_path`、`cfg_value`、`inference_timesteps` 等参数。

## 2026-06-01 h20 本机验证

- 发现当前 h20 `8017` / Jenkins 最新部署目录已有试听 ASR 修复。
- 当前外部 `48100 -> 8100` 进程仍跑旧目录 `/data/project/test_ai_botserver.20260529211325`，尚未吃到这次 ASR 修复；不要误以为外部入口已生效。
- 用 h20 本机 `8017` 验证参考音频：`https://files.joyingai.cn/crm/20260114/user4_1768388268372_3900b285138e29f3.m4a`，时长 `9.856s`。
- Whisper ASR 识别结果：`咨询的角色信息量更加可以被搜索的这种角色所以我觉得咨询师可能会更好一点`。
- 目标文案较短时，第一次生成 `0.96s` 被短音频保护拦截。
- 使用更长目标文案后生成成功：`https://videos-test.joyingai.cn/video/crm/20260601/user4_1780300703094_7e84c36906ec20d9.wav`，时长 `2.240s`。
- ASR 初始返回繁体，已追加修复：试听接口会把参考音频 ASR 文本通过 `zhconv.convert(..., "zh-cn")` 转为简体后再传给 VoxCPM。
- GitLab `test` 最新提交：`821a71eb fix: normalize audition reference text`。

## 2026-06-01 最终确认：Bot 音色克隆 ASR 使用范围

### 结论

Bot 服务内目前两条音色克隆链路都使用参考音频 ASR：

1. 完整视频生成链路：
   - 入口：`/crm/generate_video_task`
   - 流程：CRM 传 `job_id` -> Bot 拉 `generateTaskList` -> 调度任务 -> `video_work_Heygem_Whisper`
   - 声音克隆前会对 `voice_file_url` 参考音频做 Whisper ASR。
   - ASR 文本会作为 `reference_text` 传给 VoxCPM。

2. 音色试听链路：
   - 入口：`/crm/voice_clone_audition`
   - 本次新增：收到 `voice_file_url` 后，后端内部调用 Whisper ASR。
   - ASR 成功后，文本转简体，再作为 `reference_text` 传给 VoxCPM。
   - ASR 失败或返回空文本时降级为空 `reference_text`，不阻断接口。

### CRM / 前端传参是否改变

不改变。

试听接口仍然只需要原有字段：

```json
{
  "voice_file_url": "参考音频URL，必填",
  "text": "要合成的试听文案，非必填",
  "voice_emotion": 1,
  "voice_speed": 1.0,
  "voice_volume": 50
}
```

前端/CRM 不需要传 `reference_text`。

`reference_text` 是 Bot 后端内部根据 `voice_file_url` 自动 ASR 得到的字段，不对前端暴露，也不需要写入接口入参。

完整视频生成链路也不需要 CRM 额外传 `reference_text`，仍按原流程只通过 `/crm/generate_video_task` 传 `job_id`，Bot 再从 CRM 拉任务详情。

### h20 当前部署状态

- `8017`：supervisor / Jenkins 最新部署代码，已包含试听接口 ASR 修复。
- `8100`：外部 `223.112.222.90:48100` 对应的 Bot，目前仍跑旧目录 `/data/project/test_ai_botserver.20260529211325`，尚未吃到这次试听 ASR 修复。

因此：

- h20 本机 `8017` 已验证新逻辑正常。
- CRM 外部走 `48100` 要生效，需要把 `8100` 重启到当前最新 `/data/project/test_ai_botserver` 部署目录。
- 这一步会影响外部联调入口，不应默认自动做；需要用户确认后再操作。

### UTF-8 测试注意事项

远程 h20 shell 里直接写中文 curl body 时，可能因为 shell/编码问题把 `text` 变成 `????????`，导致 VoxCPM 实际收到乱码文案，最终生成内容不对。

正确测试方式：

- 使用前端/API 工具正常发送 `application/json; charset=utf-8`。
- 或在 h20 上先写 UTF-8 JSON 文件，再用 `curl --data-binary @payload.json` 发送。
- 不要把“远程 shell 中文被转问号”的异常测试结果误判为模型必然不按 `text` 生成。

### 已验证样例

参考音频：

```text
https://files.joyingai.cn/crm/20260114/user4_1768388268372_3900b285138e29f3.m4a
```

参考音频时长：`9.856s`

参考音频 ASR 简体文本：

```text
咨询的角色信息量更加可以被搜索的这种角色所以我觉得咨询师可能会更好一点
```

正确 UTF-8 请求生成结果：

```text
https://videos-test.joyingai.cn/video/crm/20260601/user4_1780301700077_02182c20e917a12c.wav
```

生成音频时长：`12.640s`

生成音频 ASR：

```text
您好,这是本次声音克隆视听效果,我们正在测试参考音频识别文字后传给模型,看看音色语速和情绪是否更稳定自然。
```

结论：正确 UTF-8 JSON 请求下，VoxCPM 最终生成内容基本按 `text` 输出。

## 2026-06-01 16:32 h20 48100/8100 状态复核

- h20 本机 `127.0.0.1:8100/status/check` 返回 `{"status":"ok"}`。
- 但 `8100` 进程仍是旧进程：PID `2766060`，启动时间 `Fri May 29 21:13:48 2026`，工作目录 `/data/project/test_ai_botserver.20260529211325`。
- 当前 Jenkins 最新软链为 `/data/project/test_ai_botserver -> /data/project/test_ai_botserver.20260601160216`，`8017` supervisor 服务已跑在最新部署目录。
- 最新目录的 `router/crm_server.py` 已包含试听 ASR 修复标记：`_transcribe_voice_audition_reference_text`、`zhconv.convert(reference_text, "zh-cn")`、`reference_text_len`、传给 VoxCPM 的 `reference_text`。
- 结论：外部 `48100 -> h20:8100` 对应的 Bot 当前还不是最新代码，尚未吃到试听 ASR 修复。要让 CRM 外部试听接口生效，需要把 `8100` 停掉并从当前 `/data/project/test_ai_botserver` 最新软链目录重启。
