---
tags: [h20, docker, voxcpm, latentsync, plan]
updated: 2026-05-29
---

# h20 模型 Docker 打包初步计划

## 目标

把 h20 测试服视频生成链路里的两个模型服务分别 Docker 化：

- VoxCPM：音色克隆 / 文本转克隆语音
- LatentSync：唇形同步 / 数字人口型对齐

Bot 主服务和调度服务暂时不进 Docker，继续由当前测试服部署链路管理。

## 当前链路

```text
CRM
-> Bot /crm/generate_video_task
-> ai_botserver_sch 调度
-> VoxCPM 生成克隆音频
-> LatentSync 生成唇形同步视频
-> 字幕、封面、上传、回调 CRM
```

## 两个模型分别做什么

### VoxCPM

当前 h20 内部端口：

```text
8110
```

当前启动文件：

```text
router/service/video_server/voxcpm_api.py
```

作用：

```text
输入参考音频 + 文案 + voice_emotion/voice_speed/voice_volume
输出克隆后的语音音频
```

也就是“用这个参考音色，把这段文案说出来”。

### LatentSync

当前 h20 内部端口：

```text
8101
```

当前启动文件：

```text
router/service/video_server/latentsync_api.py
```

作用：

```text
输入数字人原视频 + VoxCPM 生成的音频
输出口型和音频对齐的新视频
```

也就是“让视频里的人按新音频开口说话”。

## 为什么分成两个镜像

建议分别打包：

```text
voxcpm-api
latentsync-api
```

原因：

- 两个模型依赖不同。
- CUDA / torch / conda 环境可能不同。
- LatentSync 显存压力更大，通常需要单并发。
- VoxCPM 后续可能允许更高并发。
- 单独升级、回滚、重启更清楚。
- 出问题时日志边界更明确。

## 推荐短期目标形态

测试服第一阶段建议使用 host network，减少 Bot 配置变更：

```text
Bot 主服务：宿主机运行
VoxCPM 容器：宿主机 8110
LatentSync 容器：宿主机 8101
```

Bot 配置保持：

```json
{
  "voxcpm_api_base": "http://127.0.0.1:8110",
  "latentsync_api_base": "http://127.0.0.1:8101"
}
```

## VoxCPM Docker 化步骤

1. 整理当前能跑通的 Python / torch / voxcpm 依赖版本。
2. 确认模型缓存目录和 HuggingFace cache 目录。
3. 写 `voxcpm-api` Dockerfile。
4. 构建镜像。
5. 挂载模型目录和 cache。
6. 使用 GPU 启动容器。
7. 监听宿主机 `8110`。
8. 验证 `/health`。
9. 验证 `/v1/clone-voice`。
10. 再让 Bot 调容器里的 `8110`。

推荐模型不要打进镜像，先用 volume 挂载：

```text
/data/models
/root/.cache/huggingface
```

## LatentSync Docker 化步骤

1. 整理当前能跑通的 LatentSync conda 环境。
2. 确认 CUDA / torch / xformers / onnxruntime / ffmpeg 依赖。
3. 确认 `ByteDance/LatentSync-1.6` checkpoints 目录。
4. 写 `latentsync-api` Dockerfile。
5. 构建镜像。
6. 挂载 checkpoints 和临时视频目录。
7. 使用 GPU 启动容器。
8. 监听宿主机 `8101`。
9. 验证 `/health`。
10. 用短视频 + 短音频验证唇形同步。

推荐 checkpoints 放在宿主机统一目录，例如：

```text
/data/models/LatentSync-1.6
```

## 推荐实施顺序

```text
1. 先 Docker 化 VoxCPM
2. 验证 /health 和音色克隆
3. Bot 调容器 8110
4. 跑 /crm/voice_clone_audition
5. 再 Docker 化 LatentSync
6. 验证 /health 和短视频唇形同步
7. Bot 调容器 8101
8. 跑 /crm/generate_video_task 完整链路
9. 再考虑 docker compose / supervisor / systemd 托管
```

## 关键验证项

- `docker ps` 确认容器运行。
- `curl http://127.0.0.1:8110/health`。
- `curl http://127.0.0.1:8101/health`。
- 单测 VoxCPM 音频生成。
- 单测 LatentSync 唇形同步。
- 再测 Bot 的 `/crm/voice_clone_audition`。
- 最后测 `/crm/generate_video_task` 完整视频生成。
- 并发 2 条任务观察 GPU 是否 OOM。
- 确认失败后 `t_comfyui_config` 资源锁释放。

## 容易踩的坑

- 容器里没有 `ffmpeg`。
- 容器启动后还要访问 HuggingFace，外网不通会卡住。
- 模型路径写死在宿主机，容器里不存在。
- CUDA runtime 和 torch 版本不匹配。
- LatentSync 需要的动态库缺失。
- 容器临时目录空间不足。
- 输出文件路径在容器内，Bot 或宿主机访问不到。
- Bot 仍调 `127.0.0.1:8110/8101`，但容器没用 host network。
- LatentSync 并发没限制，导致 GPU OOM。
- 容器重启后重新下载模型，启动很慢。

## 建议目录结构

```text
deploy/docker/
  voxcpm/
    Dockerfile
    requirements.txt
    start.sh
  latentsync/
    Dockerfile
    requirements.txt
    start.sh
  docker-compose.h20.yml
```

模型和临时目录建议：

```text
/data/models/voxcpm
/data/models/LatentSync-1.6
/data/model_cache/huggingface
/data/video_tmp
```

## 当前结论

短期最稳方案：

```text
Bot 和 ai_botserver_sch 仍在宿主机跑。
VoxCPM 和 LatentSync 分别做成容器。
两个容器先用 host network 保持端口不变。
模型文件使用宿主机 volume 挂载。
```

这样业务链路改动最小，后续如果要扩容，也可以单独迁移 VoxCPM 或 LatentSync。

## 生产旧口型 Docker 交接信息（2026-06-01 补充）

交接同事提供的生产旧口型 Docker 信息：

```text
口型 docker 服务：
镜像版本：guiji2025/duix.avatar:2.9
注意：镜像和官方镜像不一致，启动脚本修改过，不要使用官方镜像。
容器 yml 文件地址：/data/Comfyui_Duix/Duix-Avatar/deploy/docker-employ
文件名和容器名对应，端口需要查看 yml 文件确认，不要凭文件名猜端口。
docker 文件日志地址也需要通过 yml 文件确认。
docker 启动后必须做接口测试。
后续 docker 化注意：有部分模型是代码中加载，有模型池操作，需要注意。
旧启动方式示例：nohup python app_local.py > app_run.log 2>&1 &
```

对新模型 Docker 化的影响：

- 不要直接使用官方 duix.avatar 镜像作为参照结论，生产实际用的是改过启动脚本的镜像。
- 后续对接晋良哥/运维时，需要先读取旧 yml，确认：
  - 容器名
  - 宿主机端口和容器端口映射
  - GPU 分配
  - volume 挂载
  - 日志文件路径
  - 容器启动命令
  - 是否有模型池/多实例管理逻辑
- VoxCPM / LatentSync Docker 化仍建议分别做容器，但启动方式、日志规范、端口暴露和 yml 管理方式应尽量贴近旧生产口型服务，方便运维统一管理。
- `inference_steps` / `guidance_scale` 不暴露给前端，但应做成容器启动配置（环境变量或 yml 配置），避免每次调参都重新打镜像。
- Docker 启动后必须验证：
  - `/health`
  - VoxCPM `/v1/clone-voice`
  - LatentSync `/v1/lip-sync`
  - Bot `/crm/generate_video_task` 端到端任务
  - `t_comfyui_config` 锁领取和释放

## 官方 Docker/容器化参考调研（2026-06-01 补充）

### LatentSync

官方仓库：

```text
https://github.com/bytedance/LatentSync
```

结论：

- 没查到 ByteDance 官方发布的可直接 `docker pull bytedance/latentsync` 这类生产 Docker 镜像。
- 官方仓库包含 `cog.yaml` 和 `predict.py`，这是 Replicate Cog 风格的容器化部署配置，可作为 Docker 化环境参考。
- 官方 `cog.yaml` 里关键环境：
  - GPU: true
  - CUDA: 12.1
  - Python: 3.10.13
  - system packages: `ffmpeg`, `libgl1`
  - Python requirements: `requirements.txt`
- 官方 `predict.py` 暴露参数：
  - `guidance_scale`: 1-3，默认 2.0
  - `inference_steps`: 20-50，默认 20
- 官方 `inference.sh` 里示例参数：
  - `inference_steps=20`
  - `guidance_scale=1.5`
  - `--enable_deepcache`

对我们有用的地方：

- 可以参考官方 Cog 配置确定基础 CUDA / Python / ffmpeg / libgl1 / requirements。
- 不能直接替代我们当前的 `latentsync_api.py`，因为我们需要保留：
  - `/health`
  - `/v1/lip-sync`
  - URL 下载输入、流式返回 mp4
  - `inference_steps` / `guidance_scale` 后端配置化
  - 单并发控制

### VoxCPM

官方仓库：

```text
https://github.com/OpenBMB/VoxCPM
```

官方文档：

```text
https://voxcpm.readthedocs.io/
```

结论：

- OpenBMB 官方仓库没查到普通 Dockerfile / docker-compose，可直接参考的是 `pip install voxcpm`、Python API、CLI 和 `app.py` Web Demo。
- 官方生产部署推荐之一是 vLLM-Omni；vLLM-Omni 是官方 vLLM 项目的 omni-modal serving stack，支持 VoxCPM2，并有官方 Docker 镜像：

```text
vllm/vllm-omni
```

- vLLM-Omni 提供的是 OpenAI-compatible `/v1/audio/speech` 这类接口，不等于我们当前的 `/v1/clone-voice`。

对我们有用的地方：

- 如果将来追求高并发、连续批处理、多租户 GPU serving，可以评估 vLLM-Omni。
- 当前阶段更适合继续封装我们自己的 `voxcpm_api.py`，因为它已经适配：
  - `/health`
  - `/v1/clone-voice`
  - `text`
  - `reference_audio_url`
  - `reference_text`
  - `voice_emotion`
  - `voice_speed`
  - `voice_volume`

### 当前建议

- LatentSync：参考官方 Cog 环境，但保留我们自己的 FastAPI 服务层。
- VoxCPM：参考官方 Python API / CLI；短期继续 Docker 化我们自己的 `voxcpm_api.py`。
- 不建议直接切 vLLM-Omni，除非后续单独评估 API 兼容、voice clone 参数映射、并发收益和迁移成本。
