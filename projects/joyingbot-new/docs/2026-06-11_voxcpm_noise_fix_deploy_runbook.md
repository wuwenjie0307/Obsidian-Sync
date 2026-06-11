---
date: "2026-06-11"
project: "joyingbot-new"
type: doc
tags: [doc, h20, voxcpm, deployment, runbook, audio-noise]
aliases: ["VoxCPM 试听噪音修复部署 Runbook"]
---

# VoxCPM 试听噪音修复部署 Runbook

## 图谱链接

- 项目: [[projects/joyingbot-new/00-项目概览|joyingbot-new]]
- 索引: [[projects/joyingbot-new/docs/00-docs-index|参考文档索引]]
- Bug: [[projects/joyingbot-new/bugs/2026-06-11_voice_clone_speech_buzz_noise|生成视频口播嗡嗡噪音]]
- Changelog: [[projects/joyingbot-new/changelog/2026-06-11_h20_preview_audio_reuse_flat_payload|H20 试听音频复用 flat payload]]

## 背景

2026-06-11 排查 H20 测试服“生成后视频口播有嗡嗡噪音”的问题时，用户补充了一个关键现象：试听接口生成后的原音频本身也有同类嗡嗡噪音。这个现象说明噪音不是最终视频 mux、字幕烧录、BGM 混音或对嘴阶段首次引入，而是在更早的试听生成阶段已经进入音频。

H20 日志确认，最新相关试听音频 `user4_1781158803929_bfaaa76c278a0cc6.wav` 在 `2026-06-11 14:18:59` 通过 `voice_clone_audition` 调用 VoxCPM 生成，参数为：

```text
emotion=4
speed=1.0
volume=70
text_len=16
reference_text_len=20
api=http://127.0.0.1:8128/v1/clone-voice
```

对比同一批不同情绪的试听音频后发现：`emotion=1/2/8, volume=70` 没有满幅削波；`emotion=4, volume=70` 的 wav 峰值达到 `0 dBFS`，出现满幅样本。结论是 VoxCPM 某些情绪模式输出电平偏热，再乘上 `voice_volume=70` 后会被 `np.clip(-1, 1)` 硬削波，听感表现为“有人声时才有的嗡嗡/毛刺噪音”。

因为这段试听音频会被保存为形象的原音色，后续视频生成只是复用这段已经过载的音频作为克隆参考，所以最终视频也会继承该噪音。

## 结论速览

另一台机器如果也从 `test` 分支拉取最新代码，是否“只要重启就能生效”，取决于 VoxCPM 服务的部署方式：

| 部署方式 | 拉最新 `test` 后是否只需重启 | 原因 |
| --- | --- | --- |
| 容器通过 bind mount 挂载代码到 `/app/voxcpm_api.py` | 是，重启或重新创建容器即可 | 容器启动时读取宿主机最新文件 |
| 裸进程直接运行仓库里的 `router/service/video_server/voxcpm_api.py` | 是，重启 Python 进程即可 | 进程重启后导入最新代码 |
| Docker 镜像构建时 `COPY` 代码，运行时没有 bind mount | 否，需要 rebuild 镜像并 recreate 容器 | 旧容器内 `/app/voxcpm_api.py` 仍是旧镜像文件 |

最终判断不要只看 Git 是否拉到最新，而要看“正在运行的 VoxCPM 进程实际加载的文件”里有没有以下标记：

```text
VOICE_OUTPUT_TARGET_PEAK = 0.92
def limit_audio_peak(...)
audio = limit_audio_peak(audio)
```

如果运行时文件能看到这三个标记，并且 `/health` 正常，才说明这次试听噪音修复已经生效。

## 本次修复内容

Git 提交：

```text
c98b6e55 fix: limit VoxCPM output peak
```

已合并到：

```text
origin/test
```

涉及文件：

```text
router/service/video_server/voxcpm_api.py
test/test_voxcpm_voice_style_prompt.py
```

核心代码逻辑：

```python
VOICE_OUTPUT_TARGET_PEAK = 0.92


def limit_audio_peak(audio: np.ndarray, target_peak: float = VOICE_OUTPUT_TARGET_PEAK) -> np.ndarray:
    """Keep generated speech below full scale before WAV encoding."""
    if audio is None or len(audio) == 0:
        return audio
    if not 0 < target_peak < 1.0:
        raise ValueError("target_peak must be between 0 and 1")

    peak = float(np.max(np.abs(audio)))
    if peak > target_peak:
        audio = audio * (target_peak / peak)
    return audio
```

并在 `apply_audio_effects` 中、原有 `np.clip(-1.0, 1.0)` 之前调用：

```python
audio = limit_audio_peak(audio)
audio = np.clip(audio, -1.0, 1.0)
```

这样做的目的不是改变情绪、语速、音量参数，也不是让前端额外传字段，而是在 VoxCPM 输出写 WAV 前做峰值保护，避免偏热输出被硬削波。

## 判断另一台机器是否只需要重启

### 1. 先确认代码已经拉到包含修复的 test

在目标机器的项目目录执行：

```bash
git fetch origin --prune
git rev-parse --short origin/test
git log --oneline -1 origin/test
```

至少要确认 `origin/test` 包含 `c98b6e55` 或后续提交。如果 `test` 已经继续往前走，也可以直接检查文件标记：

```bash
grep -n 'VOICE_OUTPUT_TARGET_PEAK\|limit_audio_peak' router/service/video_server/voxcpm_api.py
```

预期能看到类似：

```text
VOICE_OUTPUT_TARGET_PEAK = 0.92
def limit_audio_peak(...)
audio = limit_audio_peak(audio)
```

### 2. 判断 VoxCPM 是怎么运行的

查看进程：

```bash
ps -ef | grep -E 'voxcpm_api.py|8120|8128' | grep -v grep
```

如果是裸进程，通常类似：

```text
python router/service/video_server/voxcpm_api.py --port 8128
```

这种情况下重启该 Python 进程即可。

如果是 Docker 容器，查看容器挂载：

```bash
docker ps --format '{{.ID}} {{.Names}} {{.Image}} {{.Ports}}' | grep -i voxcpm

docker inspect <container_name> \
  --format '{{range .Mounts}}{{.Source}} -> {{.Destination}};{{end}}'
```

如果能看到类似：

```text
/data/project/test_ai_botserver/router/service/video_server/voxcpm_api.py -> /app/voxcpm_api.py
```

说明是 bind mount，拉最新 `test` 后重启或重新创建容器即可。

如果看不到 `/app/voxcpm_api.py` 的挂载，说明代码大概率是在镜像里通过 Dockerfile `COPY` 进去的。此时只重启旧容器不够，必须重新 build 镜像并 recreate 容器。

### 3. 不要只信宿主机文件，要查运行时文件

对于 Docker 进程，建议用进程命名空间检查真正运行时的 `/app/voxcpm_api.py`：

```bash
pid=$(ss -ltnp 2>/dev/null \
  | awk '$4 ~ /:8128/ {print}' \
  | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' \
  | sort -u \
  | head -1)

grep -n 'VOICE_OUTPUT_TARGET_PEAK\|limit_audio_peak' \
  "/proc/$pid/root/app/voxcpm_api.py"
```

如果这里仍然没有标记，说明服务实际还在跑旧代码，即使宿主机代码已经拉新也没有生效。

## 标准部署流程

### 场景 A：Docker bind mount 方式

适用条件：`docker inspect` 能看到宿主机 `voxcpm_api.py` 挂载到容器 `/app/voxcpm_api.py`。

推荐流程：

```bash
cd /data/project/test_ai_botserver

git fetch origin --prune
git checkout test
git pull --ff-only origin test

grep -n 'VOICE_OUTPUT_TARGET_PEAK\|limit_audio_peak' \
  router/service/video_server/voxcpm_api.py
```

如果是 docker compose 管理：

```bash
docker compose -f deploy/docker/docker-compose.h20.yml up -d --force-recreate voxcpm-api
```

如果是多个容器手动运行或历史 compose 生成，可以按容器名重启：

```bash
docker restart voxcpm-api-h20-test
docker restart voxcpm-api-h20-test-2
docker restart voxcpm-api-h20-test-3
docker restart voxcpm-api-h20-test-4
docker restart voxcpm-audition-api-h20-test-1
docker restart voxcpm-audition-api-h20-test-2
docker restart voxcpm-audition-api-h20-test-3
docker restart voxcpm-audition-api-h20-test-4
```

重启后检查：

```bash
for p in 8120 8122 8124 8126 8128 8129 8130 8131; do
  printf '%s ' "$p"
  curl -sS --connect-timeout 2 --max-time 8 "http://127.0.0.1:$p/health"
  printf '\n'
done
```

并逐个检查运行时标记：

```bash
for p in 8120 8122 8124 8126 8128 8129 8130 8131; do
  pid=$(ss -ltnp 2>/dev/null \
    | awk -v port=":$p" '$4 ~ port {print}' \
    | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' \
    | sort -u \
    | head -1)
  echo "PORT=$p PID=$pid"
  grep -n 'VOICE_OUTPUT_TARGET_PEAK\|limit_audio_peak' \
    "/proc/$pid/root/app/voxcpm_api.py"
done
```

### 场景 B：裸进程方式

适用条件：`ps -ef` 能看到直接运行仓库文件。

推荐流程：

```bash
cd /data/project/test_ai_botserver

git fetch origin --prune
git checkout test
git pull --ff-only origin test

grep -n 'VOICE_OUTPUT_TARGET_PEAK\|limit_audio_peak' \
  router/service/video_server/voxcpm_api.py
```

找到端口和 PID：

```bash
ss -ltnp | grep -E ':8120|:8128'
```

按精确 PID 停止，避免误杀其他模型：

```bash
kill <pid>
```

再用原来的启动命令重启，例如：

```bash
nohup python router/service/video_server/voxcpm_api.py \
  --host 0.0.0.0 \
  --port 8128 \
  >> logs/voxcpm_8128.log 2>&1 &
```

验证：

```bash
curl -s http://127.0.0.1:8128/health
```

### 场景 C：代码打进 Docker 镜像，无 bind mount

适用条件：容器内 `/app/voxcpm_api.py` 不是宿主机挂载，而是镜像构建时 `COPY` 进去。

此时只拉 `test`、只重启容器不会生效。需要 rebuild 镜像：

```bash
cd /data/project/test_ai_botserver

git fetch origin --prune
git checkout test
git pull --ff-only origin test

docker build \
  -t joying/voxcpm-api:h20-test \
  -f deploy/docker/voxcpm/Dockerfile \
  .
```

然后重新创建容器：

```bash
docker compose -f deploy/docker/docker-compose.h20.yml up -d --force-recreate voxcpm-api
```

如果是多容器池，需要对所有 VoxCPM 服务执行 recreate。只 restart 旧容器无法加载新镜像，必须 recreate。

## H20 本次部署记录

本次 H20 测试服部署可作为参考样例。

Git 状态：

```text
origin/test -> c98b6e55 fix: limit VoxCPM output peak
```

H20 release：

```text
/data/project/test_ai_botserver.20260611151759
```

release 文件标记：

```text
/data/project/test_ai_botserver/router/service/video_server/voxcpm_api.py
182:VOICE_OUTPUT_TARGET_PEAK = 0.92
185:def limit_audio_peak(...)
207:    audio = limit_audio_peak(audio)
```

重启前：

```text
8100 cwd=/data/project/test_ai_botserver.20260611115843  # 旧 release
8017 cwd=/data/project/test_ai_botserver.20260611151759
18017 cwd=/data/project/test_ai_botserver.20260611151759
VoxCPM 8120/8122/8124/8126/8128/8129/8130/8131 容器内 /app/voxcpm_api.py 仍是旧文件，无 limit_audio_peak 标记
```

重启动作：

```text
1. 精确 kill 旧 8100 PID，并从 /data/project/test_ai_botserver 当前 symlink 重启。
2. supervisorctl restart ai_botserver
3. supervisorctl restart ai_botserver_sch
4. docker restart 所有 VoxCPM 容器：8120/8122/8124/8126/8128/8129/8130/8131
```

重启后：

```text
8100 cwd=/data/project/test_ai_botserver.20260611151759
8017 cwd=/data/project/test_ai_botserver.20260611151759
18017 cwd=/data/project/test_ai_botserver.20260611151759
```

VoxCPM 各端口运行时文件均已出现标记：

```text
/proc/<pid>/root/app/voxcpm_api.py
VOICE_OUTPUT_TARGET_PEAK = 0.92
def limit_audio_peak(...)
audio = limit_audio_peak(audio)
```

健康检查：

```text
8100 /status/check => {"status":"ok"}
8017 /status/check => {"status":"ok"}
8120 /health => {"status":"ok"}
8122 /health => {"status":"ok"}
8124 /health => {"status":"ok"}
8126 /health => {"status":"ok"}
8128 /health => {"status":"ok"}
8129 /health => {"status":"ok"}
8130 /health => {"status":"ok"}
8131 /health => {"status":"ok"}
```

scheduler 日志：

```text
待生成任务数: 0
无待生成任务。总任务数=986, task_status=0的任务数=0
```

## 验证清单

部署后按下面清单逐项确认。

### 代码层

```bash
grep -n 'VOICE_OUTPUT_TARGET_PEAK\|limit_audio_peak' \
  router/service/video_server/voxcpm_api.py
```

预期：看到三个标记。

### 运行时层

Docker 方式：

```bash
pid=$(ss -ltnp 2>/dev/null \
  | awk '$4 ~ /:8128/ {print}' \
  | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' \
  | sort -u \
  | head -1)

grep -n 'VOICE_OUTPUT_TARGET_PEAK\|limit_audio_peak' \
  "/proc/$pid/root/app/voxcpm_api.py"
```

裸进程方式：

```bash
readlink -f /proc/<pid>/cwd
tr '\0' ' ' < /proc/<pid>/cmdline
```

确认进程 cwd 或命令指向最新代码目录。

### 服务健康

VoxCPM：

```bash
curl -s http://127.0.0.1:<voxcpm_port>/health
```

预期：

```json
{"status":"ok"}
```

Bot 服务：

```bash
curl -s http://127.0.0.1:8100/status/check
curl -s http://127.0.0.1:8017/status/check
```

预期：

```json
{"status":"ok"}
```

注意：Flask bot 服务访问 `/health` 返回 404 不等于服务异常，应该以 `/status/check` 为准。

### 业务层

建议重新调用一次试听接口，使用之前容易触发问题的参数做回归：

```text
emotion=4
speed=1.0
volume=70
```

回归重点：

- 试听音频不应再出现明显满幅削波造成的嗡嗡/毛刺。
- 下载 wav 后可检查峰值是否低于满幅。
- 如果仍有声音底噪，应继续区分是模型生成底噪，还是削波失真。当前修复解决的是写 WAV 前的硬削波问题。

## 常见问题和处理

### 1. 宿主机文件有新代码，但容器里没有

症状：

```bash
grep router/service/video_server/voxcpm_api.py  # 有标记
grep /proc/<pid>/root/app/voxcpm_api.py        # 无标记
```

常见原因：

- 容器启动时挂载到了旧 release 的 inode。
- 容器没有 bind mount，代码来自旧镜像。
- 重启的是 botserver，不是 VoxCPM 容器。

处理：

- 有 bind mount：recreate 或 restart VoxCPM 容器。
- 无 bind mount：rebuild 镜像并 recreate 容器。

### 2. 只重启 8100 没有效果

`8100` 是 botserver，不是 VoxCPM 模型服务。试听接口最终会调用 `8128` 等 VoxCPM 端口。音频生成噪音修复在 `voxcpm_api.py`，因此必须重启 VoxCPM 服务本身。

### 3. `/health` 返回 404

区分服务类型：

- VoxCPM FastAPI：使用 `/health`。
- botserver Flask：使用 `/status/check`。

H20 上 `8100 /health` 返回 404 是正常现象，不能用它判断 botserver 异常。

### 4. 拉了 test 但 `origin/test` 不是预期提交

先确认远端：

```bash
git fetch origin --prune
git log --oneline -5 origin/test
```

如果看不到 `c98b6e55` 或后续包含该改动的提交，说明目标机器还没有拉到包含修复的 `test`。

### 5. 试听仍有一点噪声

这次修复的直接目标是避免 `voice_volume` 放大后硬削波。它不能保证模型本身永远没有自然底噪。如果回归后仍听到轻微底噪，需要继续做分层排查：

- 参考音频是否本身带噪。
- VoxCPM 原始输出是否带噪。
- 峰值保护后是否仍有固定频率嗡声。
- 后续混音是否又放大了人声底噪。

## 安全注意事项

- 不要把服务器密码、数据库密码、GitLab token 写入 Obsidian、命令历史、脚本文件或提交。
- 重启前尽量确认没有正在生成的视频任务，至少查看 scheduler 日志或任务表。
- 不要使用宽泛的 `pkill python`、`pkill voxcpm`，应按端口找到精确 PID 或按明确容器名重启。
- 多端口模型池必须逐个确认，不能只验证一个端口。
- 对 Docker 部署，不要只看宿主机文件，要检查 `/proc/<pid>/root/app/voxcpm_api.py`。
- 对 shared branch，先推个人分支并确认无冲突，再合并 `test`。

## 相关文件

- `router/service/video_server/voxcpm_api.py`
- `test/test_voxcpm_voice_style_prompt.py`
- `deploy/docker/voxcpm/Dockerfile`
- `deploy/docker/docker-compose.h20.yml`
- `deploy/docker/docker-compose.h20.pool.yml`
- `deploy/docker/README.md`
- `router/crm_server.py`
- `router/service/voice_audition_pool_service.py`
- `router/service/video_server2/voxcpm_tts.py`

## 相关记录

- [[projects/joyingbot-new/bugs/2026-06-11_voice_clone_speech_buzz_noise|生成视频口播嗡嗡噪音]]
- [[projects/joyingbot-new/changelog/2026-06-11_h20_preview_audio_reuse_flat_payload|H20 试听音频复用 flat payload]]