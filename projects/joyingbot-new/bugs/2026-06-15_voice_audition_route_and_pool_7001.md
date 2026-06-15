---
date: "2026-06-15"
project: joyingbot-new
type: bug
status: resolved
severity: high
tags: [bug, h20-test, voice-clone, voice-audition, voxcpm, model-pool, apidoc]
aliases: ["测试服试听接口 404 与 VoxCPM 7001 端口失效"]
---

# 测试服试听接口 404 与 VoxCPM 7001 端口失效

## 图谱链接

- 项目: [[projects/joyingbot-new/00-项目概览|joyingbot-new]]
- 索引: [[projects/joyingbot-new/bugs/00-bugs-index|Bug 记录索引]]

## 问题描述

2026-06-15 测试服前端个人形象页点击“试听”失败。前端反馈页面显示 `success`，并提供一张接口返回截图，截图内容类似：

```json
{
  "code": 200,
  "data": {
    "voice_emotion": 0,
    "voice_file_url": "",
    "voice_speed": 0,
    "voice_volume": 0
  },
  "message": "success"
}
```

这张截图不是试听合成接口的成功返回，而是个人形象详情接口返回的空音色配置。

## 涉及 apidoc 接口

- `api/702` 短视频 | 个人形象 | 详情_PC
  - `POST /crm/agent/pc/video/userProfileInfo`
  - 返回 `voice_file_url`、`voice_emotion`、`voice_speed`、`voice_volume`，为空表示当前个人形象没有保存有效音色样本。
- `api/1936` 短视频 | 个人形象 | 详情声音试听_PC
  - `POST /crm/agent/pc/video/userProfileVoiceAudition`
  - 请求必须带非空 `voice_file_url`，来源可以是用户上传音频，也可以是上一次试听返回的 `data.reference_sample.voice_file_url`。
- `api/707` 短视频 | 个人形象 | 添加修改_PC
  - `POST /crm/agent/pc/video/userProfileAdd`
  - 若把试听结果作为音色样本保存，应保存 `reference_sample` 里的 `voice_file_url/voice_emotion/voice_speed/voice_volume`，避免二次叠加情绪或语速。

## 复现步骤

1. 打开测试服个人形象页面。
2. 上传或选择声音后点击试听。
3. 前端显示失败或没有正常播放试听音频。
4. 后端日志中出现 `voiceAudition` 相关错误。

## 实际行为

本次故障分两层：

1. 路由层：apidoc 写的是 `/crm/agent/pc/video/userProfileVoiceAudition`，测试服后端当时只挂了旧路由 `/crm/voice_clone_audition`，新 PC 路径返回 404。
2. 模型池层：修复路由后，前端已经能打到后端，后端也完成了 Whisper ASR，但试听池领取到 `t_comfyui_config.id=12`，其 `config_value_audio=http://127.0.0.1:7001`，H20 上 7001 没有服务监听，导致 `Connection refused`，接口返回 500。

关键日志证据：

```text
[voiceAudition] 参考音频 ASR 完成: text_len=20
[voiceAuditionPool] 领取试听资源成功 config_id=12 voxcpm_api_base=http://127.0.0.1:7001
[voiceAudition] 调用 h20 API: config_id=12 url=http://127.0.0.1:7001/v1/clone-voice
[voiceAudition] 无法连接 h20 服务
ConnectionRefusedError: [Errno 111] Connection refused
POST /crm/voice_clone_audition HTTP/1.1 500
```

## 期望行为

- apidoc 中的 PC 路径和旧路径都能进入同一个后端试听处理函数。
- `voice_audition_url` 资源池只启用当前真实健康的 VoxCPM 试听端口。
- 前端点击试听时，后端返回 `code=200` 且 `data.voice_file_url` 为新生成的试听音频 URL。

## 原因

- 后端缺少 apidoc PC 路由别名，造成前端如果切到新路径就 404。
- H20 测试库 `t_comfyui_config` 中 `voice_audition_url` 仍启用了过期端口 7001，但 H20 上 7001 无监听。
- 健康的试听服务实际在 8129、8130、8131，其中本次按 GPU 使用约束只启用 1-4 卡范围内可用的 8129、8130，未启用 8131。

## 解决方案

1. 后端代码修复：给 `voice_clone_audition` 增加 PC 路由别名。

```python
@crm_bp.route('/agent/pc/video/userProfileVoiceAudition', methods=['POST'])
@crm_bp.route('/voice_clone_audition', methods=['POST'])
def voice_clone_audition():
    ...
```

2. 添加回归测试：确认同一个函数同时注册：

```text
/agent/pc/video/userProfileVoiceAudition
/voice_clone_audition
```

3. Git 与部署：

```text
commit: a7c7d42c fix: add pc voice audition route alias
branch: feature/ai_v6.3.1_video
target: test
H20 release: /data/project/test_ai_botserver.20260615161623
```

4. H20 运行态修复：

```sql
update t_comfyui_config
set is_active=0, updated_time=now()
where config_key='voice_audition_url'
  and config_value_audio='http://127.0.0.1:7001';

update t_comfyui_config
set is_active=1, updated_time=now()
where config_key='voice_audition_url'
  and config_value_audio in ('http://127.0.0.1:8129', 'http://127.0.0.1:8130');
```

修复后状态：

```text
id=12 voice_audition_url http://127.0.0.1:7001 is_active=0
id=13 voice_audition_url http://127.0.0.1:8129 is_active=1
id=14 voice_audition_url http://127.0.0.1:8130 is_active=1
id=15 voice_audition_url http://127.0.0.1:8131 is_active=0
```

## 验证结果

路由验证：

```text
8100 /crm/agent/pc/video/userProfileVoiceAudition -> 400 voice_file_url 不能为空
8100 /crm/voice_clone_audition -> 400 voice_file_url 不能为空
8017 /crm/agent/pc/video/userProfileVoiceAudition -> 400 voice_file_url 不能为空
8017 /crm/voice_clone_audition -> 400 voice_file_url 不能为空
```

说明两个路径都已进入后端逻辑，不再 404。

模型池与接口验证：

```text
7001 curl failed: Could not connect to server
8129 /health -> {"status":"ok"}
8130 /health -> {"status":"ok"}
8131 /health -> {"status":"ok"}  # 本次未启用
```

内网试听接口验证成功：

```text
POST /crm/agent/pc/video/userProfileVoiceAudition HTTP=200
voice_file_url=https://videos-test.joyingai.cn/video/crm/20260615/user4_1781512551669_b60bf8ba55414e78.wav
```

## 下次排查 Runbook

### 1. 先确认 apidoc 路径是否存在

```bash
curl -sS -o /tmp/audition_pc.out -w '%{http_code}\n' \
  -H 'Content-Type: application/json' \
  -d '{}' \
  http://127.0.0.1:8100/crm/agent/pc/video/userProfileVoiceAudition

curl -sS -o /tmp/audition_legacy.out -w '%{http_code}\n' \
  -H 'Content-Type: application/json' \
  -d '{}' \
  http://127.0.0.1:8100/crm/voice_clone_audition
```

判断：

- `404`: 后端路由没有挂上或运行进程不是最新 release。
- `400 voice_file_url 不能为空`: 路由已通，参数校验正常。
- `500`: 继续查后端日志和 VoxCPM 试听池。

### 2. 查 H20 当前 release 和进程 cwd

```bash
readlink -f /data/project/test_ai_botserver

for p in 8100 8017 18017; do
  pids=$(ss -ltnp 2>/dev/null | awk -v port=":$p" '$4 ~ port {print}' | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | sort -u)
  echo "PORT $p PIDS ${pids:-none}"
  for pid in $pids; do
    echo "PID $pid CWD $(readlink -f /proc/$pid/cwd 2>/dev/null)"
    ps -p "$pid" -o pid,lstart,cmd --no-headers
  done
done
```

如果某个端口 cwd 不是当前 release，只重启对应端口即可。路由变更只需要 API 服务生效，不需要重启 VoxCPM。

### 3. 查试听接口日志

```bash
cd /data/project/test_ai_botserver
grep -nE 'userProfileVoiceAudition|voice_clone_audition|voiceAudition|voice_audition|无法连接|Connection refused|CSM 上传成功|h20 API 返回' logs/run.log | tail -n 120
```

重点看：

- 是否完成 `参考音频 ASR 完成`
- 领取到哪个 `config_id`
- 调用的 `voxcpm_api_base` 是哪个端口
- 是 `Connection refused`、超时，还是 VoxCPM 返回业务错误

### 4. 查试听模型池 DB 与端口健康

```sql
select id, config_key, config_value, config_value_audio, is_active, type, description, updated_time
from t_comfyui_config
where config_key='voice_audition_url'
order by id;
```

```bash
for p in 7001 8129 8130 8131; do
  echo "-- port $p --"
  ss -ltnp 2>/dev/null | grep ":$p" || true
  curl -sS --connect-timeout 1 --max-time 3 "http://127.0.0.1:$p/health" || true
  echo
done
```

判断：

- DB 中 `is_active=1` 的端口必须真实监听且 `/health` 正常。
- 如果 active 端口不通，先把它置为 `0`，再启用健康端口。
- 遵守 GPU 使用约束：不要启用或重启 5/6/7 GPU 对应服务，除非用户明确允许。

### 5. 前端截图怎么解释

如果前端截图是：

```json
{"code":200,"data":{"voice_file_url":"","voice_emotion":0,"voice_speed":0,"voice_volume":0}}
```

这通常是 `userProfileInfo` 详情接口返回“当前未保存音色样本”，不是试听合成成功。试听成功应该看 `userProfileVoiceAudition` 的返回，并且 `data.voice_file_url` 应为非空新音频 URL。

## 优化点

- 后端 `voice_audition_pool_service` 领取资源前可以探测 `/health`，避免领取到不可用端口。
- `voice_audition_url` 配置应增加运维巡检，发现 active 端口无监听时报警或自动禁用。
- 试听失败返回给前端时，建议把 `连接 VoxCPM 服务失败` 与 `参数为空` 区分清楚，减少前端误判为 success。
- 前端不应把 `userProfileInfo` 的空 `voice_file_url` 当作可试听音频；只有上传/录音成功后的 URL 或试听接口返回的 `reference_sample.voice_file_url` 才能继续试听或保存。

## 相关文件

- `router/crm_server.py`
- `test/test_voice_clone_upload.py`
- `router/service/voice_audition_pool_service.py`
- `router/service/video_server2/voxcpm_tts.py`

## 相关记录

- [[projects/joyingbot-new/changelog/2026-06-15_voice_clone_tts_area_unit_normalization|声音克隆 TTS 面积单位 m² 规范化]]
- [[projects/joyingbot-new/bugs/2026-06-09_voice_clone_audition_video_consistency|试听与视频生成声音克隆行为不一致]]
- [[projects/joyingbot-new/docs/2026-06-11_voxcpm_noise_fix_deploy_runbook|VoxCPM 试听噪音修复部署 Runbook]]


## 追加校正：15:20-16:36 实际调用时间线

用户指出“下午一开始并没有调用 7001”。为避免把最后抓到的故障点误写成全程原因，重新按 2026-06-15 15:20-16:36 的日志解析了 `voiceAudition` 调用端口和接口状态。

解析结果：

```text
port 7001: count=41 first=2026-06-15 15:30:54 last=2026-06-15 16:33:48
port 8129: count=4 first=2026-06-15 16:34:29 last=2026-06-15 16:35:48
agent/pc/video/userProfileVoiceAudition status 200: count=1 first=2026-06-15 16:34:48 last=2026-06-15 16:34:48
voice_clone_audition status 200: count=3 first=2026-06-15 16:34:32 last=2026-06-15 16:35:50
```

更准确的结论：

- 不能笼统说“下午一开始就是 7001 导致”。
- 现有 H20 日志能确认的是：从 `2026-06-15 15:30:54` 开始，试听链路实际开始大量领取/调用 `7001`，直到 `16:33:48`。
- `16:34:29` 之后，修正 DB 试听池配置，后端开始调用健康的 `8129`。
- `16:34:32` 起旧接口 `/crm/voice_clone_audition` 返回 200；`16:34:48` 起 apidoc PC 接口 `/crm/agent/pc/video/userProfileVoiceAudition` 返回 200。
- 因此，用户记忆中更早之前试听正常并不矛盾；日志只能证明故障阶段从 15:30 左右开始进入 7001。

更新后的根因描述：

- `m² -> 平方米` 的提交 `91c3172b` 仍然不是端口故障根因，它只改文本规范化。
- 真正导致 15:30 后连续失败的是运行态 DB 中 `voice_audition_url id=12 / 7001` 处于 `is_active=1`，而领取逻辑按 `id asc` 优先取到 id=12。
- 由于 H20 上 `127.0.0.1:7001` 没有监听，调用 `/v1/clone-voice` 失败。

下次遇到“之前能试听，突然不行”，不要只查代码提交；要先按时间线查：

```bash
# 看试听实际调用了哪个 VoxCPM 端口
grep -nE 'voiceAudition|voice_audition|调用 h20 API|领取试听资源|无法连接 h20 服务|POST /crm/(agent/pc/video/userProfileVoiceAudition|voice_clone_audition)' \
  /data/project/test_ai_botserver/logs/run.log \
  /data/server_logs/supervisord/ai_botserver.out | tail -n 200

# 看 active 的试听池端口是否真实健康
select id, config_key, config_value_audio, is_active, updated_time
from t_comfyui_config
where config_key='voice_audition_url'
order by id;
```
