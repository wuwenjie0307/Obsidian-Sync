---
date: "2026-06-01"
tags: [changelog, h20, docker, voxcpm, latentsync, crm, video-generation]
---

# h20 Docker 试运行进度与当天工作总结

## 改动类型

- [x] deployment progress
- [x] docker trial
- [x] bug fix
- [x] verification

## 今天完成的主要工作

1. h20 测试服视频生成链路继续保持“生产成熟调度流程为底座，只替换两个模型”的方向。
   - CRM 视频任务主入口仍按调度链路走 `/crm/generate_video_task`。
   - `/crm/submit_heygem_whisper_video_task` 不作为主流程。
   - 声音克隆保留 VoxCPM，唇形同步保留 LatentSync。
   - 试听接口 `/crm/voice_clone_audition` 继续保留，用于产品测试音色参数。

2. 声音克隆试听相关问题已处理和确认。
   - 之前 0 秒音频主要是 text 太短加上 `voice_speed=3` 造成输出极短。
   - 已加短音频保护：生成音频过短时提示增加 text 或降低 voice_speed。
   - 参考音频 ASR 逻辑已用于给 VoxCPM 提供 `reference_text`，对 CRM 前端传参没有新增要求。

3. LatentSync 参数调试继续保留后端控制。
   - `guidance_scale` 当前 h20 手动服务按产品试测方向调过。
   - `inference_steps` / `guidance_scale` 不做前端选项，先放后端配置或默认值里控制。
   - 产品要调这两个参数时，可以后端改默认值、重启模型服务再测试。

4. h20 Docker 试运行产物已经提交到 GitLab `test` 分支。
   - Docker 文件目录：`deploy/docker/`
   - VoxCPM Docker：`deploy/docker/voxcpm/Dockerfile`
   - LatentSync Docker：`deploy/docker/latentsync/Dockerfile`
   - h20 compose：`deploy/docker/docker-compose.h20.yml`
   - README：`deploy/docker/README.md`

## Docker 当前部署进度

当前 Docker 试运行仍是旁路验证，不影响现有裸机服务：

| 服务 | 当前正式/测试裸机地址 | Docker 试运行地址 | 状态 |
|---|---|---|---|
| VoxCPM | `127.0.0.1:8110` | `127.0.0.1:8120` | Docker 已启动，`/health` 已返回 ok，直接生成音频已成功 |
| LatentSync | `127.0.0.1:8101` | `127.0.0.1:8121` | Docker 已启动，`/health` 已返回 ok，直接 lip-sync 还未验证 |
| Bot/CRM | `8017` / `8100` | 不进 Docker | 未切换，仍走现有服务 |

已确认的 h20 Docker 环境：

- Docker CLI：`/cm/local/apps/docker/current/bin/docker`
- Docker Compose：`v2.29.2`
- h20 Docker daemon 没有注册 `runtime: nvidia`。
- h20 已安装 NVIDIA Container Toolkit。
- Compose 里 GPU 必须用：

```yaml
deploy:
  resources:
    reservations:
      devices:
        - driver: nvidia
          device_ids: ["1"]
          capabilities: [gpu]
```

不要在 h20 的 compose 里使用：

```yaml
runtime: nvidia
```

## 今天 Docker 排查和修复点

1. Docker Hub 原始 CUDA 基础镜像下载太慢。
   - 改为复用 h20 已缓存基础镜像。
   - VoxCPM 使用：`vllm/vllm-openai:v0.8.5.post1`
   - LatentSync 使用：`registry.hd-04.alayanew.com:8443/.../comfyui-0.3.75:1.53`

2. h20 compose `runtime: nvidia` 启动失败。
   - 报错：`unknown or invalid runtime name: nvidia`
   - 根因：Docker daemon 没注册 `nvidia` runtime 名称。
   - 修复：改用 `deploy.resources.reservations.devices` 申请 GPU。
   - 验证：临时 compose 能通过 GPU device request 运行 `nvidia-smi`。

3. VoxCPM 基础镜像自带 vLLM ENTRYPOINT。
   - 报错表现：容器把 `python /app/voxcpm_api.py` 当成 vLLM API server 参数。
   - 修复：VoxCPM Dockerfile 增加 `ENTRYPOINT []`。

4. VoxCPM Python 3.12 与 `pkg_resources` 兼容问题。
   - 报错：`pkgutil.ImpImporter` 不存在。
   - 根因：setuptools 82 没提供本地 `pkg_resources`，Python 回退到系统旧版 `pkg_resources`。
   - 修复：VoxCPM Dockerfile 固定 `setuptools==80.9.0`。

5. ModelScope 与 datasets 版本不兼容。
   - 报错：`cannot import name get_metadata_patterns from datasets.data_files`
   - 验证结果：`datasets 3.0.0` 到 `3.3.2` 可用，`3.4.1` 起不可用。
   - 修复：VoxCPM Dockerfile 固定 `datasets==3.3.2`。

## 已提交到 GitLab test 的 Docker 相关提交

- `8a70964e` `chore: add h20 model docker trial artifacts`
- `858b6c7f` `chore: reuse cached h20 docker bases`
- `b31d30b9` `fix: loosen voxcpm docker hub dependency`
- `6b761790` `fix: reuse torch in h20 docker builds`
- `056f5d59` `fix: constrain audio torch packages in docker builds`
- `2e748424` `fix: use matched torch base for voxcpm docker`
- `7a73add6` `fix: constrain jax for latentsync docker build`
- `408478bf` `fix: use compose device reservations for h20 gpu`
- `12f531d0` `fix: reset voxcpm docker entrypoint`
- `98eee40f` `fix: pin voxcpm docker setuptools`
- `f2dc0bd2` `fix: pin voxcpm docker datasets`

## h20 当前 Docker 验证结果

已完成：

```bash
curl -s http://127.0.0.1:8120/health
# {"status":"ok"}

curl -s http://127.0.0.1:8121/health
# {"status":"ok"}
```

VoxCPM Docker 直接生成音频已通过：

- 请求接口：`POST http://127.0.0.1:8120/v1/clone-voice`
- 参考音频：`https://files.joyingai.cn/crm/20260114/user4_1768388268372_3900b285138e29f3.m4a`
- 输出文件：`/tmp/voxcpm-docker-test.wav`
- HTTP 状态：`200`
- 输出格式：WAV，mono，48000 Hz
- 输出大小：约 `106 KB`
- 输出时长：约 `1.12s`
- GPU：VoxCPM Docker 使用 GPU1，生成时 GPU1 有计算占用。

LatentSync Docker 已完成健康检查，但还没完成直接 `/v1/lip-sync` 验证。

原因：`/v1/lip-sync` 需要一个 h20 能访问的视频 URL 和音频 URL。当前本地生成的 `/tmp/voxcpm-docker-test.wav` 是 h20 本机文件，不是 URL；需要先找或上传一个短音频 URL，再配一个短视频 URL 测试。

## 当前 h20 状态

当前是旁路 Docker 试运行状态：

- 不影响现有裸机服务。
- 不影响 CRM 当前联调链路。
- Bot 配置仍不切到 `8120/8121`。
- 当前裸机模型仍是：
  - VoxCPM：`127.0.0.1:8110`
  - LatentSync：`127.0.0.1:8101`
- 当前 Docker 试运行模型是：
  - VoxCPM：`127.0.0.1:8120`
  - LatentSync：`127.0.0.1:8121`

## 明天继续步骤

1. 先确认 Docker 容器仍然存活。

```bash
/cm/local/apps/docker/current/bin/docker ps
curl -s http://127.0.0.1:8120/health
curl -s http://127.0.0.1:8121/health
nvidia-smi
```

2. 找一个 5-10 秒的公开视频 URL 和一个公开音频 URL。
   - 视频 URL 必须 h20 能访问。
   - 音频 URL 可以用 VoxCPM Docker 生成结果上传到测试 CDN 后得到，也可以使用已有的公开 wav/m4a。
   - 不建议直接用很长视频做第一轮 Docker lip-sync 测试。

3. 直接验证 LatentSync Docker：

```bash
curl -s -X POST http://127.0.0.1:8121/v1/lip-sync \
  -H "Content-Type: application/json" \
  -d '{
    "video_url": "可被 h20 访问的短视频 URL",
    "audio_url": "可被 h20 访问的短音频 URL",
    "inference_steps": 30,
    "guidance_scale": 1.8
  }' \
  -o /tmp/latentsync-docker-test.mp4
```

验证：

```bash
ls -lh /tmp/latentsync-docker-test.mp4
ffprobe -v error -show_entries format=duration,size -of default=nw=1:nk=1 /tmp/latentsync-docker-test.mp4
```

4. 如果 LatentSync Docker 直接验证通过，再做受控 Bot 切换测试。
   - 前提：确认没有正在处理的视频任务。
   - 临时把 h20 Bot 模型地址从裸机切到 Docker：

```json
{
  "voxcpm_api_base": "http://127.0.0.1:8120",
  "latentsync_api_base": "http://127.0.0.1:8121"
}
```

5. 切换后只跑一个 CRM 视频任务做端到端验证。
   - 不并发压测。
   - 确认声音克隆、唇形同步、字幕、上传、回调、锁释放都正常。

6. 若 Bot 切换测试失败，立即回滚配置：

```json
{
  "voxcpm_api_base": "http://127.0.0.1:8110",
  "latentsync_api_base": "http://127.0.0.1:8101"
}
```

## 注意事项

- 不要把 Bot 配置提前切到 Docker，必须等 LatentSync Docker 直接接口通过。
- 不要动生产服。
- 不要推 master，上线前只合并到 `test`。
- 不要把密码写进 Obsidian、Git 或最终回复。
- 当前 Docker 还没有接入 `t_comfyui_config` 模型池，只是固定端口旁路试运行。
- 后续要完全沿用生产 Docker 调度池，需要另起计划：让调度领取 `t_comfyui_config` 后，把 config 里的 VoxCPM/LatentSync 地址传给生成逻辑，而不是继续读全局配置。
