---
date: "2026-06-03"
status: open
tags: [h20, voice-clone, voxcpm, prompt, todo, crm]
---

# h20 音色克隆参数与提示词优化 2026-06-03

## 今日任务

今天需要把 h20 测试服的音色克隆参数链路和提示词控制逻辑优化好，重点是：

- 确认前端/CRM 传入的音色参数是否已经能到 Bot、scheduler 和 VoxCPM。
- 确认 `voice_emotion`、`voice_speed`、`voice_volume` 当前是否真正影响模型。
- 设计“情绪 + 语速”组合提示词，让不同选择组合生成不同模型输入文本。
- 保持音量作为确定性的音频后处理参数，不优先放进提示词。

## 当前已确认的信息

### 1. 参数链路已经接通

试听接口 `/crm/voice_clone_audition` 已支持以下字段：

```text
voice_emotion / voiceEmotion
voice_speed   / voiceSpeed
voice_volume  / voiceVolume
voice_file_url / voiceFileUrl
text
```

它会校验参数，然后把 `text`、`reference_audio_url`、`reference_text`、`voice_emotion`、`voice_speed`、`voice_volume` POST 到 h20 VoxCPM 的 `/v1/clone-voice`。

视频生成任务主链路也已经接通：

```text
CRM task 返回体
-> /crm/generate_video_task 同步任务
-> parse_voice_clone_params(task)
-> t_video_generate_task.voice_emotion / voice_speed / voice_volume
-> scheduler.collect_scheduler._process_single_video_task
-> video_work_Heygem_Whisper
-> video_server2.voxcpm_tts.clone_voice_and_synthesize
-> POST {voxcpm_api_base}/v1/clone-voice
```

当前允许值：

```text
voice_emotion: 1-8
1 正常
2 亲切
3 热情
4 激昂
5 严肃
6 喜悦
7 悲伤
8 愤怒

voice_speed: 0.75, 1.0, 1.25, 1.5, 2.0, 3.0
voice_volume: 0-100
```

### 2. 当前没有组合提示词逻辑

VoxCPM API 端当前确实有 `VOICE_EMOTION_MAP`，也会把 `voice_emotion` 映射成 `emotion_id`，但这个 `emotion_id` 当前只用于校验和日志，没有传给模型，也没有拼到 `text`。

当前模型调用形态是：

```python
audio = voxcpm_model.generate(
    text=req.text,
    prompt_wav_path=ref_path,
    prompt_text=req.reference_text or "",
)
```

因此，当前：

- `voice_emotion`：只校验/日志，不实际影响模型输入。
- `voice_speed`：生成后通过 `librosa.effects.time_stretch(...)` 调整音频速度，不是提示词控制。
- `voice_volume`：生成后按 `volume / 50.0` 调整音频振幅，不是提示词控制。
- `prompt_text`：是参考音频的 ASR 文本，不是情绪/语速提示词。

例如：

```text
亲切 + 语速较快
亲切 + 语速较慢
```

当前传给模型的 `text` 是一样的，只是生成后的音频被加速或放慢。`亲切` 本身并没有真正参与模型输入。

### 3. h20 部署相关

h20 Docker VoxCPM 服务按 compose 记录挂载：

```text
/data/project/test_ai_botserver/router/service/video_server/voxcpm_api.py -> /app/voxcpm_api.py
```

因此，当前 h20 VoxCPM Docker 模型服务应受 `router/service/video_server/voxcpm_api.py` 这份逻辑控制。

注意：试听接口 `/crm/voice_clone_audition` 不走 `t_comfyui_config` 模型池，而是走全局 `h20_api_base`。视频生成主链路走 `t_comfyui_config.config_value_audio` 资源池地址。

## 推荐优化方案

### 1. 新增组合提示词构造函数

建议在 `router/service/video_server/voxcpm_api.py` 增加纯函数，例如：

```python
def build_voice_style_prompt(text: str, voice_emotion, voice_speed: float) -> str:
    ...
```

在调用 `voxcpm_model.generate(...)` 前生成 `styled_text`：

```python
styled_text = build_voice_style_prompt(
    text=req.text,
    voice_emotion=req.voice_emotion,
    voice_speed=req.voice_speed,
)

audio = voxcpm_model.generate(
    text=styled_text,
    prompt_wav_path=ref_path,
    prompt_text=req.reference_text or "",
)
```

### 2. 情绪提示词建议

```text
1 正常: 自然、清晰
2 亲切: 温柔甜美，亲切自然
3 热情: 热情、积极、有感染力
4 激昂: 激动、有力量、富有激情
5 严肃: 严肃、沉稳
6 喜悦: 愉快、充满活力
7 悲伤: 低沉，略带哀伤
8 愤怒: 愤怒、强烈、有压迫感
```

### 3. 语速提示词建议

```text
0.75: 语速缓慢，字字清晰
1.0 : 自然语速
1.25: 语速稍快
1.5 : 语速较快，表达流畅
2.0 : 语速很快，但吐字清晰
3.0 : speaking very fast，尽量保持清晰
```

后续可根据产品验收结果微调文案。`3.0` 当前容易导致短音频或 badcase，建议重点验收。

### 4. 组合示例

```text
voice_emotion=2, voice_speed=1.25
=> (温柔甜美，亲切自然，语速稍快)欢迎来到我们的节目！

voice_emotion=2, voice_speed=0.75
=> (温柔甜美，亲切自然，语速缓慢，字字清晰)欢迎来到我们的节目！

voice_emotion=5, voice_speed=1.0
=> (严肃、沉稳，自然语速)以下是本次事故的调查结论...
```

### 5. 音量处理建议

`voice_volume` 建议继续作为音频后处理参数，不放进提示词。

原因：音量是确定性工程参数，通过振幅调整比提示词控制更稳定。提示词适合控制情绪、语气、语速风格，不适合作为音量主控。

## 待办清单

- [x] 在 `router/service/video_server/voxcpm_api.py` 增加 `build_voice_style_prompt(...)`。
- [x] 在 `/v1/clone-voice` 调用 `voxcpm_model.generate(...)` 前使用 `styled_text`。
- [x] 处理空文本、无效 emotion、默认 speed、文本已带括号提示词等边界。
- [x] 增加测试：`亲切 + 快` 与 `亲切 + 慢` 应生成不同提示词。
- [x] 增加测试：`voice_emotion=1`、`voice_speed=1.0` 的默认行为可控。
- [x] 跑现有参数链路测试，避免破坏透传。
- [x] 明确试听接口资源治理方案：不直接占用 `VoxCPM + LatentSync` 成对视频模型池，优先走独立 VoxCPM / 试听专用小池。
- [x] 部署 h20 后用试听接口对比至少 3 组样例。
- [x] 修复 `prompt_wav_path + prompt_text` 高保真模式会把 style prompt 当正文朗读的问题，改用 `reference_wav_path` 可控克隆模式。
- [x] 修复后重新部署 h20 `8110` 并用 Whisper ASR 验证括号控制词没有进入最终朗读。
- [x] 线上如试听量上来，增加试听专用 VoxCPM 小池或异步试听任务，避免长请求和视频生成资源互抢。


## 本次本地处理记录

- 已在本地实现 `build_voice_style_prompt(...)`，将 `voice_emotion + voice_speed` 组合成模型输入文本前缀。
- `/v1/clone-voice` 调用 `voxcpm_model.generate(...)` 时已改为传入 `styled_text`，`voice_volume` 仍保持音频后处理。
- 新增 `test/test_voxcpm_voice_style_prompt.py` 覆盖亲切快/慢、默认值、空文本、无效 emotion、已有括号提示词替换、模型调用点。
- 本地验证通过：`python -m unittest test.test_scheduled_video_voice_params test.test_voice_clone_upload test.test_voxcpm_voice_style_prompt`，`python -m py_compile router/service/video_server/voxcpm_api.py`，`git diff --check -- router/service/video_server/voxcpm_api.py test/test_voxcpm_voice_style_prompt.py`。
- h20 已通过公网 Bot 试听入口完成 7 组样本对比，见下方“h20 试听样本对比结果”。

## h20 试听样本对比结果（首次结果，已作废）

> 2026-06-03 复核发现：首次结果使用的是 `prompt_wav_path + prompt_text` 高保真模式。VoxCPM 会把括号内的 style prompt 当作正文朗读，导致 `(温柔甜美，亲切自然，语速稍快)` 等控制词进入最终音频。因此本节只保留排查记录，不再作为验收结果；有效结果见下一节“reference_wav_path 修复后”。

2026-06-03 测试链路：

```text
223.112.222.90:48100
-> 8100 Bot /crm/voice_clone_audition
-> h20_api_base http://127.0.0.1:8110
-> VoxCPM /v1/clone-voice
```

测试前已将 `8110` VoxCPM 从最新 test 部署目录启动：

```text
/data/project/test_ai_botserver.20260603182741
```

并确认 `8110` 进程加载的 `voxcpm_api.py` 包含：

- `build_voice_style_prompt(...)`
- `styled_text`

VoxCPM 日志确认模型输入已经带上情绪/语速提示词，例如：

```text
(自然、清晰，自然语速)...
(温柔甜美，亲切自然，语速缓慢，字字清晰)...
(温柔甜美，亲切自然，语速稍快)...
(严肃、沉稳，自然语速)...
(激动、有力量、富有激情，语速较快，表达流畅)...
(自然、清晰，speaking very fast，尽量保持清晰)...
```

样本文案：

```text
您好，这是本次声音克隆试听效果测试，我们正在对比不同情绪和语速参数对音色、语气、清晰度和自然度的影响。
```

参考音频：

```text
https://files.joyingai.cn/crm/20260114/user4_1768388268372_3900b285138e29f3.m4a
```

### 返回结果与客观指标

| 样本 | 参数 | HTTP / 耗时 | 生成时长 | 响度 | CDN |
|---|---|---:|---:|---:|---|
| baseline | emotion=1, speed=1.0, volume=50 | 200 / 6.4s | 14.400s | -16.78 dBFS | https://videos-test.joyingai.cn/video/crm/20260603/user4_1780484891521_39287c17b82a3487.wav |
| friendly_slow | emotion=2, speed=0.75, volume=50 | 200 / 7.0s | 24.107s | -19.23 dBFS | https://videos-test.joyingai.cn/video/crm/20260603/user4_1780484898473_c8c2e179a2db77b6.wav |
| friendly_fast | emotion=2, speed=1.25, volume=50 | 200 / 5.2s | 11.392s | -20.06 dBFS | https://videos-test.joyingai.cn/video/crm/20260603/user4_1780484903814_db9ff389e12f1c4a.wav |
| serious_normal | emotion=5, speed=1.0, volume=50 | 200 / 5.3s | 15.040s | -15.91 dBFS | https://videos-test.joyingai.cn/video/crm/20260603/user4_1780484909243_3bb5a33ee5a79ecc.wav |
| volume_loud | emotion=1, speed=1.0, volume=80 | 200 / 4.8s | 13.120s | -12.78 dBFS | https://videos-test.joyingai.cn/video/crm/20260603/user4_1780484913981_caf312f0944b3e9c.wav |
| passionate_fast | emotion=4, speed=1.5, volume=50 | 200 / 5.9s | 11.947s | -20.36 dBFS | https://videos-test.joyingai.cn/video/crm/20260603/user4_1780485005077_da6d972f824ea10c.wav |
| extreme_fast | emotion=1, speed=3.0, volume=50 | 200 / 4.8s | 5.067s | -20.53 dBFS | https://videos-test.joyingai.cn/video/crm/20260603/user4_1780485009987_641a2882c574d2ef.wav |

### 初步结论

- `voice_emotion + voice_speed` 已确认进入 VoxCPM 文本输入，不再只是日志参数。
- `voice_speed` 对最终音频时长影响明显：
  - `0.75x` 从 baseline 的 `14.400s` 拉长到 `24.107s`。
  - `1.25x / 1.5x` 缩短到约 `11-12s`。
  - `3.0x` 缩短到 `5.067s`，本次未触发“音频过短”拦截，但仍属于高风险选项，建议产品验收重点听感。
- `voice_volume=80` 的响度从 baseline `-16.78 dBFS` 提升到 `-12.78 dBFS`，说明音量后处理生效。
- 情绪类参数已体现在 prompt 前缀里；主观音色/语气差异需要产品或测试同学逐条听音频确认。

## h20 试听样本对比结果（reference_wav_path 修复后）

2026-06-03 修复根因：

- 当前代码原先用 `prompt_wav_path + prompt_text` 调 VoxCPM，这是 Hi-Fi / 高保真延续模式，不适合作为不可朗读的 style control 通道。
- 根据 VoxCPM2 用法，style tag 应配合 `reference_wav_path` 的 controllable clone 模式使用。
- 修复后 `voxcpm_model.generate(...)` 调用改为：

```python
audio = voxcpm_model.generate(
    text=styled_text,
    reference_wav_path=ref_path,
)
```

部署记录：

```text
test -> origin/test: 3900dfc0
h20 deploy dir: /data/project/test_ai_botserver.20260603192551
8110 cwd: /data/project/test_ai_botserver.20260603192551
```

复测链路仍为：

```text
223.112.222.90:48100
-> 8100 Bot /crm/voice_clone_audition
-> h20_api_base http://127.0.0.1:8110
-> VoxCPM /v1/clone-voice
```

### 修复后返回结果、客观指标与 ASR 检查

所有样本 `style_terms_found=[]`，表示 Whisper 转写中没有出现 `温柔甜美 / 亲切自然 / 语速稍快 / 自然语速 / 严肃 / 激动` 等括号控制词。

| 样本 | 参数 | HTTP / 耗时 | 生成时长 | 响度 | style_terms_found | CDN |
|---|---|---:|---:|---:|---|---|
| baseline | emotion=1, speed=1.0, volume=50 | 200 / 4.4s | 9.920s | -17.39 dBFS | `[]` | https://videos-test.joyingai.cn/video/crm/20260603/user4_1780486519820_68daaf722a52ee44.wav |
| friendly_slow | emotion=2, speed=0.75, volume=50 | 200 / 7.9s | 15.573s | -19.94 dBFS | `[]` | https://videos-test.joyingai.cn/video/crm/20260603/user4_1780486529856_6498a8f1adba9e41.wav |
| friendly_fast | emotion=2, speed=1.25, volume=50 | 200 / 4.4s | 8.960s | -21.65 dBFS | `[]` | https://videos-test.joyingai.cn/video/crm/20260603/user4_1780486538064_478957bab9b4d3f1.wav |
| serious_normal | emotion=5, speed=1.0, volume=50 | 200 / 4.0s | 9.760s | -16.97 dBFS | `[]` | https://videos-test.joyingai.cn/video/crm/20260603/user4_1780486543999_0ecd5b138acb8759.wav |
| volume_loud | emotion=1, speed=1.0, volume=80 | 200 / 4.0s | 9.760s | -13.19 dBFS | `[]` | https://videos-test.joyingai.cn/video/crm/20260603/user4_1780486549792_5363b7650a21d9ea.wav |
| passionate_fast | emotion=4, speed=1.5, volume=50 | 200 / 3.8s | 6.187s | -18.95 dBFS | `[]` | https://videos-test.joyingai.cn/video/crm/20260603/user4_1780486555436_0e58b45a38bdc30f.wav |
| extreme_fast | emotion=1, speed=3.0, volume=50 | 200 / 3.7s | 3.360s | -20.98 dBFS | `[]` | https://videos-test.joyingai.cn/video/crm/20260603/user4_1780486560871_24f1c46b504554fd.wav |

### 修复后初步结论

- 括号控制词朗读问题已修复：7 组 ASR 均未发现 style 控制词。
- `voice_speed` 仍然对最终时长有明显影响：
  - `0.75x`：baseline `9.920s` -> `15.573s`。
  - `1.25x`：`8.960s`。
  - `1.5x`：`6.187s`。
  - `3.0x`：`3.360s`，ASR 已明显变差，建议前端/产品谨慎开放或至少重点验收。
- `voice_volume=80` 相比 baseline 响度从 `-17.39 dBFS` 提升到 `-13.19 dBFS`，音量后处理仍生效。
- 情绪 prompt 不再被朗读，但不同 emotion 的主观语气差异仍需要人工听感验收。

## 试听并发与资源池方案

2026-06-03 追加判断：

当前视频生成模型池的 `t_comfyui_config` 是 `VoxCPM + LatentSync` 成对配置。试听接口只需要 VoxCPM，如果直接领取现有成对模型池，会把 LatentSync 也一起占住，造成资源浪费，并且会让试听和正式视频生成互相抢资源。

结论：试听接口不建议直接复用现有成对视频模型池。

建议方案：

1. 短期继续让 `/crm/voice_clone_audition` 走专用 `h20_api_base` VoxCPM 服务，例如独立 `8110`，不进入 `t_comfyui_config` 视频模型池。
2. 保留 VoxCPM API 内部 `BoundedSemaphore(2)`，前端限制同一用户同一时间只发起一个试听，后端对繁忙场景返回明确提示。
3. 如果线上试听量上来，新增只包含 VoxCPM 的试听专用小池，例如 `voice_audition_api_bases` 或独立 `t_voice_audition_model_config`，不要绑定 LatentSync。
4. 试听专用小池可用 Redis slot / 分布式锁控制每个 VoxCPM 实例并发，抢不到空位时快速返回繁忙或转异步任务，不建议让用户请求长时间排队。
5. 长期如果产品要求高并发试听，改为异步试听任务：提交返回 `audition_task_id`，前端轮询生成结果。

当前测试策略：本次 h20 参数样本对比仍走公网 Bot 试听入口 `223.112.222.90:48100 -> 8100 Bot -> h20_api_base -> VoxCPM`，但需要确保 `h20_api_base` 指向的 VoxCPM 服务已经加载本次 `build_voice_style_prompt(...)` 逻辑。

## 相关文件

- `router/crm_server.py`
  - `/crm/voice_clone_audition`
  - `/crm/generate_video_task`
- `router/service/video_server2/voice_params.py`
  - 参数解析与允许值
- `pojo/models.py`
  - `VideoGenerateTask.voice_emotion / voice_speed / voice_volume`
- `scheduler/collect_scheduler.py`
  - scheduler 透传参数给 `video_work_Heygem_Whisper`
- `router/service/video_server2/video_work.py`
  - 传参数给 VoxCPM client
- `router/service/video_server2/voxcpm_tts.py`
  - POST `{voxcpm_api_base}/v1/clone-voice`
- `router/service/video_server/voxcpm_api.py`
  - VoxCPM API 实际模型调用与后处理
- `deploy/docker/docker-compose.h20.yml`
  - h20 Docker 模型服务挂载
- `deploy/docker/docker-compose.h20.pool.yml`
  - h20 多实例模型服务挂载

## 已验证

本地参数链路与 VoxCPM style prompt 回归测试已通过：

```text
python -m unittest test.test_scheduled_video_voice_params test.test_voice_clone_upload test.test_voxcpm_voice_style_prompt
Ran 26 tests in 0.341s
OK
```

补充验证：

- `python -m py_compile router/service/video_server/voxcpm_api.py` 通过。
- `git diff --check -- router/service/video_server/voxcpm_api.py test/test_voxcpm_voice_style_prompt.py` 通过，仅有 LF/CRLF 提示。
- h20 修复后 7 组公网试听均返回 200，Whisper ASR 检查 `style_terms_found=[]`。

## 安全备注

本记录不保存 h20 密码、跳板机密码、sudo 密码或任何 token。后续如果需要登录 h20 实机核对，只在当前会话临时使用密码，不写入 Obsidian、Git、代码文件或日志。



## 2026-06-03 混合 Hi-Fi / 可控克隆策略落地

本轮新增产品策略：默认参数优先走 VoxCPM2 Hi-Fi 高保真克隆；只要用户调整情绪或语速，就切到 `reference_wav_path` 可控克隆模式，避免 style prompt 在 Hi-Fi 模式下被当成正文朗读。

### 落地规则

| 条件 | 模式 | 说明 |
|---|---|---|
| `voice_emotion=1/normal`、`voice_speed=1.0`、`reference_text` 非空 | `prompt_wav_path + prompt_text` | 默认追求音色相似度和高保真 |
| 情绪非默认 | `reference_wav_path` | 需要模型级 style control |
| 语速非默认 | `reference_wav_path` | 语速属于风格控制，Hi-Fi 容易忽略 |
| 只有音量非默认 | 仍走 Hi-Fi | 音量是生成后的确定性后处理 |
| `reference_text` 为空 / ASR 失败 | `reference_wav_path` | Hi-Fi 缺少必要参考文本 |

### 代码与提交

- feature commit: `837bf3ce fix: use hifi clone for default voice style`
- test merge commit: `4c68d298 Merge branch 'h20-model-pool-productionize' into test`
- 已推送远端 `origin/test`: `3900dfc0..4c68d298`
- 相关文件：
  - `router/service/video_server/voxcpm_api.py`
  - `test/test_voxcpm_voice_style_prompt.py`

### 本地验证

- `python -m unittest test.test_voxcpm_voice_style_prompt`：11 tests OK
- `python -m unittest test.test_scheduled_video_voice_params test.test_voice_clone_upload test.test_voxcpm_voice_style_prompt`：feature 工作树 29 tests OK；test 工作树合并后 28 tests OK
- `python -m py_compile router/service/video_server/voxcpm_api.py`：feature 工作树 OK；test 工作树提升权限后 OK
- `git diff --check -- router/service/video_server/voxcpm_api.py test/test_voxcpm_voice_style_prompt.py`：OK，仅 Windows CRLF warning

### h20 部署与重启

Jenkins/test 软链已更新到：

```text
/data/project/test_ai_botserver -> /data/project/test_ai_botserver.20260603195816
```

复查发现旧进程仍在旧目录：

- `8110` 原 cwd：`/data/project/test_ai_botserver.20260603192551`
- `8100` 原 cwd：`/data/project/test_ai_botserver.20260603134321`

已将 `8100` 和 `8110` 从最新软链目录重启：

```text
8100 pid=722219 cwd=/data/project/test_ai_botserver.20260603195816
8110 pid=722220 cwd=/data/project/test_ai_botserver.20260603195816
```

最终 health：

```text
8110 /health -> {"status":"ok"}
8100 /status/check -> {"status":"ok"}
```

本地到公网 `223.112.222.90:48100` TCP 连接超时，因此本次复测通过跳板机进入 h20 后，在 h20 内部请求：

```text
127.0.0.1:8100/crm/voice_clone_audition -> 127.0.0.1:8110/v1/clone-voice
```

### h20 三组试听复测结果

样本文案：

```text
您好，这是本次声音克隆试听效果测试，我们正在对比不同情绪和语速参数对音色、语气、清晰度和自然度的影响。
```

参考音频：

```text
https://files.joyingai.cn/crm/20260114/user4_1768388268372_3900b285138e29f3.m4a
```

| 样本 | 参数 | 期望模式 | 8110 日志模式 | HTTP / 耗时 | 生成时长 | 响度 | CDN |
|---|---|---|---|---:|---:|---:|---|
| default_hifi_expected | emotion=1, speed=1.0, volume=50 | Hi-Fi | `mode=hifi` | 200 / 5.61s | 10.720s | -16.08 dBFS | https://videos-test.joyingai.cn/video/crm/20260603/user4_1780488958765_20bcc428e0733811.wav |
| friendly_fast_controllable_expected | emotion=2, speed=1.25, volume=50 | controllable | `mode=controllable` | 200 / 4.30s | 7.552s | -21.18 dBFS | https://videos-test.joyingai.cn/video/crm/20260603/user4_1780488963470_dcbcf4a15911d46f.wav |
| volume_loud_hifi_expected | emotion=1, speed=1.0, volume=80 | Hi-Fi | `mode=hifi` | 200 / 4.58s | 10.880s | -13.42 dBFS | https://videos-test.joyingai.cn/video/crm/20260603/user4_1780488968522_b7f417a625078082.wav |

### 本轮结论

- 试听接口当前可正常使用：三组样本均返回 HTTP 200，CDN 音频可下载并解析为 WAV。
- 混合策略生效：默认参数和只改音量均走 `mode=hifi`；非默认情绪/语速走 `mode=controllable`。
- 音量后处理仍生效：默认样本 `-16.08 dBFS`，volume=80 样本 `-13.42 dBFS`。
- 语速后处理仍生效：1.25x 样本时长 `7.552s`，比默认 Hi-Fi 样本 `10.720s` 明显更短。
- 后续仍建议产品侧明确文案：默认高保真克隆；调整情绪/语速后进入可控克隆模式，音色相似度可能略有变化。

## 2026-06-03 完整视频生成模型池 VoxCPM 重启

用户确认直接重启完整视频生成模型池中的 VoxCPM 实例。本次只操作 VoxCPM 容器，不操作 `8100/8110` 试听服务，也不操作 LatentSync。

### 重启对象

| 端口 | 容器 | 重启后 PID | health |
|---:|---|---:|---|
| 8120 | `voxcpm-api-h20-test` | 737365 | `{"status":"ok"}` |
| 8122 | `voxcpm-api-h20-test-2` | 737680 | `{"status":"ok"}` |
| 8124 | `voxcpm-api-h20-test-3` | 737864 | `{"status":"ok"}` |
| 8126 | `voxcpm-api-h20-test-4` | 738162 | `{"status":"ok"}` |

### 校验结果

- Jenkins/test 当前软链：`/data/project/test_ai_botserver -> /data/project/test_ai_botserver.20260603195816`
- 四个容器均通过 `docker restart` 重启，保留原容器配置和挂载。
- 四个容器内 `/app/voxcpm_api.py` 均包含 `should_use_hifi_voice_clone`，grep count 均为 `2`。
- 四个端口 `8120 / 8122 / 8124 / 8126` 均监听正常，`/health` 均返回 ok。

### 结论

完整视频生成链路使用的模型池 VoxCPM 实例现在已经重新加载本次混合 Hi-Fi / 可控克隆逻辑。后续完整视频任务通过 `t_comfyui_config.config_value_audio` 分配到这些端口时，会使用同一套 `/v1/clone-voice` 逻辑：默认情绪 + 默认语速 + 有 `reference_text` 走 Hi-Fi；非默认情绪/语速走可控克隆；只改音量仍走 Hi-Fi + 音量后处理。


## 2026-06-03 试听接口并发治理落地

本轮处理待办：试听接口并发问题。目标是不让试听请求直接占用完整视频生成的 `VoxCPM + LatentSync` 成对模型池，也不让用户请求在 VoxCPM 内部长时间排队。

### 代码方案

- 新增试听专用小池配置：
  - `voice_audition_api_bases`：试听专用 VoxCPM base 列表，支持 JSON 数组、逗号/分号/空白分隔字符串。
  - `voice_audition_slot_capacity`：每个 base 可同时承载的试听 slot，默认 `2`。
  - `voice_audition_slot_ttl_seconds`：slot TTL，默认 `360` 秒。
- 未配置 `voice_audition_api_bases` 时，fallback 到现有 `h20_api_base` / 默认 base，保持兼容。
- `/crm/voice_clone_audition` 在完成参数校验和参考音频 ASR 后，再抢 Redis slot；抢不到 slot 时直接返回：

```json
{"code":503,"message":"试听服务繁忙，请稍后重试"}
```

- slot 只覆盖 VoxCPM 生成与响应下载阶段，不覆盖后续 WAV 时长检查和 CSM 上传。
- slot 释放在 `finally` 中执行；释放时会校验 token，避免 TTL 过期后误删别的请求新抢到的 slot。

### 提交与合并

- feature commit: `22173b00 feat: limit voice audition concurrency`
- test merge commit: `3acf1163 Merge branch 'h20-model-pool-productionize' into test`
- 已推送远端 `origin/test`: `4c68d298..3acf1163`

### 本地验证

- 红灯确认：新增测试先失败，缺配置、缺 acquire/release helper、缺 finally 释放、缺 Redis `SET NX EX`。
- 绿灯验证：`python -m unittest test.test_voice_clone_upload test.test_scheduled_video_voice_params test.test_voxcpm_voice_style_prompt` 通过。
  - feature 工作树：33 tests OK。
  - test 工作树合并后：32 tests OK。
- `python -m py_compile router/crm_server.py app_config/config.py` 通过。
- `git diff --check -- router/crm_server.py app_config/config.py test/test_voice_clone_upload.py` 通过，仅 Windows CRLF warning。

### h20 部署与验证

Jenkins/test 软链已更新：

```text
/data/project/test_ai_botserver -> /data/project/test_ai_botserver.20260603204131
```

`8017` 已由部署链路运行在新目录；手动将 `8100` 从旧目录重启到新目录：

```text
8100 pid=757693 cwd=/data/project/test_ai_botserver.20260603204131
8100 /status/check -> {"status":"ok"}
```

h20 内部冒烟试听：

| 测试 | 结果 |
|---|---|
| 单次试听 | HTTP 200 / `code=200` / `message=success` |
| CDN | https://videos-test.joyingai.cn/video/crm/20260603/user4_1780490654887_64179b1dc7289670.wav |

h20 内部 3 并发试听结果：

| 请求 | HTTP / 耗时 | 结果 |
|---:|---:|---|
| 1 | 200 / 5.92s | success |
| 2 | 200 / 9.28s | success |
| 3 | 200 / 12.84s | success |

结论：当前 h20 `8100` 的实际处理表现更偏串行/排队，3 并发没有形成同时抢占 slot，因此没有触发 503；这次 h20 验证可证明新代码已部署且正常试听不受影响。`503` 繁忙分支、Redis `SET NX EX` 抢占和 finally 释放由本地回归测试覆盖。后续如果要做 h20 实机 503 验收，需要在真实多 worker / 多进程入口或独立压测环境中制造同时抢占。


## 2026-06-03 试听接口并发治理落地

本轮处理待办：`线上如试听量上来，增加试听专用 VoxCPM 小池或异步试听任务，避免长请求和视频生成资源互抢。`

### 落地方案

先落地短期可上线方案：试听专用 VoxCPM 小池 + Redis slot 快速限流。

- 新增配置项：
  - `voice_audition_api_bases`：试听专用 VoxCPM base 列表，支持 JSON 数组、逗号/分号/空白分隔字符串。
  - `voice_audition_slot_capacity`：每个 base 可同时承载的试听 slot，默认 `2`。
  - `voice_audition_slot_ttl_seconds`：slot TTL，默认 `360` 秒。
- 未配置 `voice_audition_api_bases` 时，仍 fallback 到现有 `h20_api_base`，保持兼容。
- `/crm/voice_clone_audition` 在完成参数校验和参考音频 ASR 后，抢占 Redis slot；抢不到时直接返回：

```json
{
  "code": 503,
  "message": "试听服务繁忙，请稍后重试"
}
```

- slot 只覆盖 VoxCPM `/v1/clone-voice` 请求和响应下载阶段；拿到模型音频后立即在 `finally` 中释放，不覆盖后续 WAV 时长检查和 CSM 上传。
- 释放 slot 时会比对 token，避免 TTL 过期后误删新请求的 slot。

### 代码与提交

- feature commit: `22173b00 feat: limit voice audition concurrency`
- test merge commit: `3acf1163 Merge branch 'h20-model-pool-productionize' into test`
- 已推送远端 `origin/test`: `4c68d298..3acf1163`
- 相关文件：
  - `app_config/config.py`
  - `router/crm_server.py`
  - `test/test_voice_clone_upload.py`

### 本地验证

- `python -m unittest test.test_voice_clone_upload test.test_scheduled_video_voice_params test.test_voxcpm_voice_style_prompt`：feature 工作树 33 tests OK；test 工作树合并后 32 tests OK。
- `python -m py_compile router/crm_server.py app_config/config.py`：feature 工作树 OK；test 工作树提升权限后 OK。
- `git diff --check -- router/crm_server.py app_config/config.py test/test_voice_clone_upload.py`：OK，仅 Windows CRLF warning。

### h20 部署与验证

Jenkins/test 软链已更新到：

```text
/data/project/test_ai_botserver -> /data/project/test_ai_botserver.20260603204131
```

`8017` 已自动在新目录运行，`8100` 原先仍在旧目录，已手动重启到新目录：

```text
8100 pid=757693 cwd=/data/project/test_ai_botserver.20260603204131
8017 pid=755766 cwd=/data/project/test_ai_botserver.20260603204131
```

最终状态：

```text
8100 /status/check -> {"status":"ok"}
8017 /status/check -> {"status":"ok"}
```

冒烟试听结果：

```text
HTTP 200 / code=200 / elapsed=3.58s
CDN=https://videos-test.joyingai.cn/video/crm/20260603/user4_1780490654887_64179b1dc7289670.wav
```

真实 3 并发试听测试结果：

| 请求 | HTTP | 耗时 | 结果 |
|---:|---:|---:|---|
| 1 | 200 | 5.92s | success |
| 2 | 200 | 9.28s | success |
| 3 | 200 | 12.84s | success |

说明：h20 当前 `8100` 运行方式下，这 3 个请求表现为串行/排队处理，没有同时进入 Bot 侧抢 slot，所以未触发 503。代码层面的 Redis slot 抢占、抢不到返回 503、`finally` 释放已由本地回归测试覆盖。后续如果 8100 改为多 worker / 多进程并发，Redis slot 会提供跨进程保护。

### 后续增强

- 如果产品要求更高并发试听，可继续扩展 `voice_audition_api_bases` 到多个独立 VoxCPM 试听实例。
- 如果试听量继续上升，再做异步试听任务：提交返回 `audition_task_id`，前端轮询结果，避免 HTTP 长请求。

## 2026-06-03 试听接口并发治理纠正：独立 Docker + t_comfyui_config 试听池

用户纠正：不能让 `/crm/voice_clone_audition` 直接领取现有 `config_key='comfyui_url'` 的视频生成模型池，因为那会占用完整视频生成的 `VoxCPM + LatentSync` 成对资源。正确方案是重新起 VoxCPM-only 的试听 Docker 服务，并继续复用 `t_comfyui_config` 的资源锁语义。

### 修正后的设计

- 视频生成池继续使用：`config_key='comfyui_url'`，一行代表 `VoxCPM + LatentSync` 成对服务。
- 试听专用池使用：`config_key='voice_audition_url'`，一行只代表 VoxCPM 试听服务。
- 试听接口只读取 `config_value_audio` 作为 VoxCPM base，不调用 `config_value` / LatentSync。
- `is_active` 仍沿用模型池语义：`1=空闲`，`2=使用中`，抢不到时返回 `503 试听服务繁忙，请稍后重试`。
- 测试库当前查询 `voice_audition_url` 为空，后续需要先起试听 Docker 并插入 DB 行后才能实机验证。

### 本地代码状态

- 新增 `router/service/voice_audition_pool_service.py`。
- `/crm/voice_clone_audition` 已从旧 Redis slot helper 改为领取 `voice_audition_url` lease。
- `deploy/docker/docker-compose.h20.pool.yml` 补了 `voxcpm-audition-api-1`，默认端口 `8128`。
- `deploy/docker/README.md` 补了 DB 初始化 SQL 和不要覆盖现场四组 compose 的提醒。

### DB 初始化口径

```sql
INSERT INTO zhugedata_test.t_comfyui_config
  (config_key, config_value_audio, config_value, is_active, description, type)
VALUES
  ('voice_audition_url',
   'http://127.0.0.1:8128',
   'http://127.0.0.1:8128',
   1,
   'h20 voice audition voxcpm 1',
   2);
```

`config_value` 填同一个 URL 只是为了兼容旧表非空字段，Bot 实际只用 `config_value_audio`。

### 本地验证

```text
python -m unittest test.test_voice_audition_pool_service test.test_voice_clone_upload test.test_scheduled_video_voice_params
Ran 28 tests OK

python -m py_compile router/service/voice_audition_pool_service.py router/crm_server.py scheduler/collect_scheduler.py
OK

git diff --check
OK，仅有 LF/CRLF 警告
```

### 后续实机步骤

1. 确认 h20 GPU 分配，避免新的试听 VoxCPM 和视频生成池抢同一张卡。
2. 在 h20 现场 compose 里追加 `voxcpm-audition-api-1`，不要整文件覆盖现场四组视频池 compose。
3. 启动 `8128` 并检查 `/health`。
4. 插入 `voice_audition_url` DB 行。
5. 部署/重启 Bot，使 8100/48100 入口吃到新代码。
6. 调 `/crm/voice_clone_audition` 验证：正常试听走 `8128`，并且 `comfyui_url` 视频池行不被锁。

## 2026-06-04 试听专用 VoxCPM 8128 h20 落地验证

本轮按“独立 Docker + `t_comfyui_config.config_key='voice_audition_url'`”最终方案完成 h20 测试环境落地。早期 Redis slot 方案仅作为历史记录保留，当前最终口径以本节为准。

### 部署结果

- `origin/test` 已推送到 `0cddb187`，Jenkins 已生成当前目录：`/data/project/test_ai_botserver.20260604103337`。
- h20 live compose 已备份后追加 `voxcpm-audition-api-1`，没有覆盖现场运行容器。
- 新试听容器：`voxcpm-audition-api-h20-test-1`。
- 试听端口：`8128`。
- GPU：`7`。
- 健康检查：`http://127.0.0.1:8128/health` 返回 ok。
- 8100 公网入口对应 Bot 已从当前 Jenkins 目录启动：`/data/project/test_ai_botserver.20260604103337`。

### DB 配置

`t_comfyui_config` 已新增试听池行：

```text
id=12
config_key=voice_audition_url
config_value_audio=http://127.0.0.1:8128
config_value=http://127.0.0.1:8128
is_active=1
type=2
description=h20 voice audition voxcpm 1
```

### 实测结果

- 正常试听：HTTP 200 / `code=200`，返回 CDN wav：`https://videos-test.joyingai.cn/video/crm/20260604/user4_1780540878704_caf7814160974894.wav`。
- 繁忙分支：临时把 id=12 置为 `is_active=2` 后调用 `/crm/voice_clone_audition`，返回 HTTP 503 / `试听服务繁忙，请稍后重试`；测试后已恢复 id=12 为 `is_active=1`。
- DB 复查：`voice_audition_url` 行释放回 1；`comfyui_url` 视频池 h20 行 1/2/10/11 保持 1，试听接口没有领取视频生成池。

### 注意事项

- h20 当前 live compose 文件本身只包含第一组服务，额外 2/3/4 组容器仍在运行，但相对当前 compose 是 orphan。后续不要使用 `--remove-orphans`。
- 当前本机到公网 `223.112.222.90:48100` 仍 TCP 超时；h20 内网 `8100/status/check` 正常。
- h20 启动日志会打印完整配置，包含敏感字段；排查时不要 tail 完整配置日志，不要把日志原文写入回复或 Obsidian。

## 2026-06-04 h20 试听专用 VoxCPM 池实机落地

最终口径：早期 Redis slot 试听限流方案已被替代，不再作为当前实现口径。当前实现使用独立 Docker VoxCPM 服务 + `t_comfyui_config.config_key='voice_audition_url'`，试听接口不会领取 `config_key='comfyui_url'` 的完整视频生成模型池。

### h20 现场变更

- `origin/test` 已推送到 `0cddb187`，Jenkins 部署目录为 `/data/project/test_ai_botserver.20260604103337`。
- `8100` 公网入口对应的 Bot 已重启到当前 Jenkins 目录，和 `8017` 一致。
- 现场 compose 备份：`/data/project/test_ai_botserver/deploy/docker/docker-compose.h20.yml.bak.20260604101303`。
- 只追加并启动了试听服务：`voxcpm-audition-api-h20-test-1`。
- 试听服务端口：`8128`，健康检查 `http://127.0.0.1:8128/health` 返回 ok。
- 本次 h20 试听容器使用 GPU `7`。选择原因：现有 VoxCPM 视频池使用 GPU `0/1/3/5`，GPU `7` 当前显存占用极低；但它仍与 `latentsync-api-h20-test-4` 同卡，后续高并发时需要继续观察。不要默认照搬本地 `.pool.yml` 里的 GPU 占位值，未来部署前仍需重新确认 GPU 分配。

### DB 配置

测试库已插入试听池行：

```text
id=12
config_key=voice_audition_url
config_value_audio=http://127.0.0.1:8128
config_value=http://127.0.0.1:8128
is_active=1
type=2
description=h20 voice audition voxcpm 1
```

`config_value` 只作为旧表字段占位，Bot 实际只使用 `config_value_audio`。

### 实测结果

- 正常试听：`POST /crm/voice_clone_audition` 返回 HTTP 200 / `code=200`，生成 CDN wav。
- 资源释放：请求结束后 `voice_audition_url` 行恢复 `is_active=1`。
- 视频池隔离：`comfyui_url` 视频池行保持原状态，未被试听接口锁定。
- 繁忙分支：临时将 `voice_audition_url` 行置为 `is_active=2` 后，试听接口返回 HTTP 503 / `试听服务繁忙，请稍后重试`；随后已恢复为 `is_active=1`。

### 遗留观察

- 当前网络访问外部 `http://223.112.222.90:48100/status/check` 仍为 HTTP 000/TCP 超时；h20 内网 `8100/status/check` 正常。
- 8100 启动日志会打印完整配置，包含敏感字段；后续应推动配置日志脱敏。
- Machine 级临时环境变量 `H20_JUMP_PASSWORD` 需要用户在管理员 PowerShell 手动清理。
## 2026-06-04 新增三路试听 VoxCPM Docker 实例

本轮根据“提升试听接口并发”的要求，在 h20 测试服现有 `8128` 试听专用 VoxCPM 基础上，新增三个 VoxCPM-only Docker 实例，并继续接入 `t_comfyui_config.config_key='voice_audition_url'` 试听池。

### 现场变更

- 当前 Jenkins 软链：`/data/project/test_ai_botserver -> /data/project/test_ai_botserver.20260604111537`
- 备份 compose：`/data/project/test_ai_botserver/deploy/docker/docker-compose.h20.pool.yml.bak.20260604140815`
- 已追加 compose 服务：
  - `voxcpm-audition-api-2` / container `voxcpm-audition-api-h20-test-2` / port `8129` / GPU `2`
  - `voxcpm-audition-api-3` / container `voxcpm-audition-api-h20-test-3` / port `8130` / GPU `4`
  - `voxcpm-audition-api-4` / container `voxcpm-audition-api-h20-test-4` / port `8131` / GPU `6`
- 原有试听实例继续保留：`voxcpm-audition-api-h20-test-1` / port `8128` / 实际 GPU `7`

### DB 试听池

`t_comfyui_config` 当前 `voice_audition_url` 行：

```text
id=12  http://127.0.0.1:8128  is_active=1  h20 voice audition voxcpm 1
id=13  http://127.0.0.1:8129  is_active=1  h20 voice audition voxcpm 2
id=14  http://127.0.0.1:8130  is_active=1  h20 voice audition voxcpm 3
id=15  http://127.0.0.1:8131  is_active=1  h20 voice audition voxcpm 4
```

### 验证结果

健康检查：

```text
8100/status/check ok
8128/health ok
8129/health ok
8130/health ok
8131/health ok
```

4 并发验证：

```text
concurrency=4
ok=4
busy_503=0
bad400=0
total_elapsed=54.415s
```

返回 CDN：

```text
https://videos-test.joyingai.cn/video/crm/20260604/user4_1780553557579_3db4f8cac8c77688.wav
https://videos-test.joyingai.cn/video/crm/20260604/user4_1780553545882_bb40af4ad0bab085.wav
https://videos-test.joyingai.cn/video/crm/20260604/user4_1780553536155_dd9b6d38eb4d38f7.wav
https://videos-test.joyingai.cn/video/crm/20260604/user4_1780553569250_5b84bd61efa69298.wav
```

5 并发溢出验证：

```text
concurrency=5
ok=2
busy_503=0
bad400=3
total_elapsed=58.748s
```

结论：新增三路 Docker 后，测试服试听接口当前可以稳定支持 `4` 个并发成功生成。第 `5` 个并发不是理想的 `503 试听服务繁忙`，而是仍可能进入生成链路并返回短音频 `400`。后续仍需要修正试听池抢占/溢出保护逻辑，让超过池容量的请求直接返回 `503`，不要打进 VoxCPM。

## 2026-06-04 试听模型池实际调用核验

本次核验目标：确认 h20 测试服当前试听模型池是否只是写入了 `zhugedata_test.t_comfyui_config`，还是已经被 `/crm/voice_clone_audition` 真实调用。

### DB 当前状态

只读查询 `zhugedata_test.t_comfyui_config` 中 `config_key='voice_audition_url'` 的试听池行，当前 4 条均为空闲：

```text
id=12  config_key=voice_audition_url  config_value_audio=http://127.0.0.1:8128  config_value=http://127.0.0.1:8128  is_active=1  type=2  description=h20 voice audition voxcpm 1
id=13  config_key=voice_audition_url  config_value_audio=http://127.0.0.1:8129  config_value=http://127.0.0.1:8129  is_active=1  type=2  description=h20 voice audition voxcpm 2
id=14  config_key=voice_audition_url  config_value_audio=http://127.0.0.1:8130  config_value=http://127.0.0.1:8130  is_active=1  type=2  description=h20 voice audition voxcpm 3
id=15  config_key=voice_audition_url  config_value_audio=http://127.0.0.1:8131  config_value=http://127.0.0.1:8131  is_active=1  type=2  description=h20 voice audition voxcpm 4
```

`is_active=1` 表示这些试听专用 VoxCPM 实例当前都处于可领取状态。

### 8100 日志核验结果

查看 h20 上 `/tmp/bot_8100_test_ai_botserver.log` 最近日志，已经看到 `/crm/voice_clone_audition` 明确进入试听池领取逻辑，并调用对应 VoxCPM 地址：

```text
voiceAuditionPool 领取试听资源成功 config_id=12 voxcpm_api_base=http://127.0.0.1:8128
voiceAudition 调用 h20 API: config_id=12 url=http://127.0.0.1:8128/v1/clone-voice

voiceAuditionPool 领取试听资源成功 config_id=13 voxcpm_api_base=http://127.0.0.1:8129
voiceAudition 调用 h20 API: config_id=13 url=http://127.0.0.1:8129/v1/clone-voice
```

最近日志统计：

```text
config_id=12: 46 次池相关日志命中，8128 URL 69 次命中
config_id=13: 4 次池相关日志命中，8129 URL 6 次命中
config_id=14: 0 次
config_id=15: 0 次
```

### 当前结论

试听模型池已经真正被调用起来，不是只存在于 DB 表里。

但当前自然请求日志只证明：

```text
8128 / config_id=12 已被真实调用
8129 / config_id=13 已被真实调用
8130 / config_id=14 已配置、空闲，但暂未看到自然请求命中
8131 / config_id=15 已配置、空闲，但暂未看到自然请求命中
```

### 为什么 8130 / 8131 暂时没被打到

本地池领取逻辑位于 `router/service/voice_audition_pool_service.py`：

```python
session.query(model_cls)
.filter(
    model_cls.config_key == VOICE_AUDITION_CONFIG_KEY,
    model_cls.is_active == VOICE_AUDITION_AVAILABLE_STATUS,
)
.order_by(model_cls.id.asc())
.with_for_update()
.first()
```

也就是按 `id asc` 领取第一条可用资源。当前顺序是：

```text
12 -> 13 -> 14 -> 15
```

只要 `12` 在请求真正进入 VoxCPM 调用前已经释放，下一个请求就会继续拿 `12`。另外 CRM 试听接口在 `router/crm_server.py` 中是先做参考音频 ASR：

```python
reference_text = _transcribe_voice_audition_reference_text(voice_file_url)
audition_lease = acquire_voice_audition_api_base()
```

所以多个并发请求会先在 ASR 阶段错开，真正开始抢试听池时不一定同时到达，导致 `12` 经常已经空闲，后面的 `14/15` 不容易自然被选中。

### 后续待办

1. 做一次强验证：临时将 `id=12、13` 置为忙碌，发起一次试听请求，确认是否领取 `id=14 / 8130`，随后恢复。
2. 再临时将 `id=12、13、14` 置为忙碌，发起一次试听请求，确认是否领取 `id=15 / 8131`，随后恢复。
3. 优化试听池分配策略，避免永远偏向最小 id：可考虑轮询、随机、或记录最近使用时间。
4. 继续评估是否需要把资源领取提前到 ASR 前，或者将 ASR 也纳入整体并发保护，避免前端“正在生成试听”时请求已经在前置阶段排队。
5. 超过试听池容量时应稳定返回 `503 试听服务繁忙`，不要进入 VoxCPM 后再返回短音频 `400`。
