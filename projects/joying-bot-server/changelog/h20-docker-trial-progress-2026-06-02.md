---
date: "2026-06-02"
tags: [changelog, h20, docker, latentsync, voxcpm, crm, video-generation]
---

# h20 Docker 试运行进度 2026-06-02

## 改动类型

- [x] docker trial
- [x] bug fix
- [x] verification
- [x] deployment note

## 今日结论

h20 上 VoxCPM / LatentSync 继续按“一个模型一个 Docker 容器、一套 compose 统一管理”的方式推进。

当前 Docker 仍是旁路试运行，不影响 CRM 当前裸机测试链路：

| 服务 | 裸机地址 | Docker 旁路地址 | 今日状态 |
|---|---|---|---|
| VoxCPM | `127.0.0.1:8110` | `127.0.0.1:8120` | 已健康，直接声音克隆已通过 |
| LatentSync | `127.0.0.1:8101` | `127.0.0.1:8121` | 已健康，直接 lip-sync 已通过 |
| Bot/CRM | `8017` / `8100` | 未切换 | 仍走裸机模型服务 |

## LatentSync Docker 问题与修复

昨天 LatentSync Docker 的 `/health` 正常，但真实 `/v1/lip-sync` 返回 500。

今天确认根因不是接口参数，也不是视频下载问题，而是容器内 Python 依赖栈不兼容：

- 容器基础镜像是 ComfyUI 环境，Python 3.11 + Torch 2.9/cu128。
- 裸机可用环境是 Python 3.10 + Torch 2.5/cu121。
- 容器里 `scipy.special` 导入失败，报错：`All ufuncs must have type numpy.ufunc`。
- 容器里 `jax 0.4.26` 和 `ml_dtypes 0.5.4` 组合会触发递归错误。
- 修完 SciPy/JAX 后又暴露第二层问题：基础镜像自带 `peft 0.18.0`，但项目依赖 `accelerate 0.26.1`，二者不兼容，`scripts.inference` 导入失败。
- 裸机环境没有安装 `peft`，因此裸机不会触发这个问题。

修复方式：

- 在 LatentSync Docker 内创建独立 venv：`/opt/latentsync-venv`。
- venv 使用 `--system-site-packages` 复用基础镜像中的 Torch，避免重新下载大体积 GPU 包。
- 在 venv 中覆盖安装：
  - `numpy==1.26.4`
  - `scipy==1.15.3`
  - `scikit-learn==1.7.2`
  - `ml_dtypes==0.5.4`
  - `jax==0.6.2`
  - `jaxlib==0.6.2`
  - `peft==0.10.0`
- 验证 `scipy.special`、`sklearn`、`scripts.inference` 都可以正常导入。

## 今日 h20 验证结果

LatentSync Docker 修复后重新拉起：

```bash
curl -s http://127.0.0.1:8121/health
# {"status":"ok"}
```

第一次真实请求使用 `agent/video.mp4`，已进入推理，但失败于素材本身：

```text
RuntimeError: Face not detected
```

这说明 Docker 依赖问题已经越过，失败变成测试视频中途检测不到人脸。

随后改用之前裸机端到端成功产物 `/tmp/e2e_result.mp4` 做短视频验证：

- 输入视频：3.60 秒，约 807 KB。
- 输入音频：3.52 秒，约 331 KB。
- 请求：`POST http://127.0.0.1:8121/v1/lip-sync`。
- 参数：`inference_steps=30`，`guidance_scale=1.8`。
- 返回：HTTP 200。
- 输出：`/tmp/latentsync-docker-test-ok.mp4`。
- 输出视频：3.60 秒，约 774 KB。
- 端到端耗时：约 135 秒。

结论：LatentSync Docker 旁路服务真实 lip-sync 已通过。

## Git 与部署状态

本地仓库已提交：

```text
f0275ea1 fix: isolate latentsync docker dependencies
```

但本机推送 GitLab 失败：

```text
Could not resolve host: git.joyingai.cn
```

因此今天先把同一个修复 patch 应用到了 h20 当前测试部署目录：

```text
/data/project/test_ai_botserver -> /data/project/test_ai_botserver.20260602095618
```

注意：h20 上直接执行 compose build 时，构建过程还会尝试从 GitHub 拉取 `ByteDance/LatentSync`，当前 h20 访问 GitHub 超时。为不中断验证，今天采用了离线增量镜像方式：基于已有 `joying/latentsync-api:h20-test` 镜像继续加 venv 修复层，再重新标记为 `joying/latentsync-api:h20-test`。

后续需要把 GitLab 推送补上，并把 h20 的 Dockerfile/README 进一步整理成可复现的离线构建方式，避免每次构建都依赖 GitHub。

## 为什么今天没有切 Bot 到 Docker

按计划，VoxCPM 和 LatentSync Docker 直测都通过后，下一步可以做“受控 Bot 切换测试”。但今天查询测试库发现当前并非空闲状态：

- `t_video_generate_task.task_status=0` 待处理任务：18 条。
- `t_video_generate_task.task_status=2` 任务：1 条。
- `t_comfyui_config.id=1` 当前 `is_active=2`，说明调度锁仍被占用。

因此今天没有把 Bot 配置从裸机模型服务切到 Docker：

```json
{
  "voxcpm_api_base": "http://127.0.0.1:8110",
  "latentsync_api_base": "http://127.0.0.1:8101"
}
```

仍保持现状，避免影响产品当前测试。

## 下一步

1. 等测试库没有正在处理任务，且 `t_comfyui_config.id=1` 释放回 `is_active=1`。
2. 重试推送本地提交到 GitLab `test` 分支。
3. 整理 h20 LatentSync Docker 构建方式，减少对 GitHub clone 的依赖。
4. 受控切 Bot 模型地址到 Docker：

```json
{
  "voxcpm_api_base": "http://127.0.0.1:8120",
  "latentsync_api_base": "http://127.0.0.1:8121"
}
```

5. 只提交 1 个 CRM 视频任务做端到端验证。
6. 验证通过后，再决定是否把 `8120/8121` 作为测试服正式模型入口。

## 注意事项

- 不要动生产服。
- 不要推 master，上线前只合并到 `test`。
- 不要把密码写入 Obsidian、Git 或聊天回复。
- 当前 Docker 还没有接入 `t_comfyui_config` 模型池，只是固定端口旁路试运行。
- 后续完整沿用生产模型池逻辑时，需要让调度领取 `t_comfyui_config` 后，按配置行传递 VoxCPM/LatentSync 地址，而不是继续只读全局配置。


## 最终状态补充

GitLab `test` 推送成功后，Jenkins 已部署到：

```text
/data/project/test_ai_botserver -> /data/project/test_ai_botserver.20260602102443
```

最终确认：

- Bot 配置仍是裸机模型服务：`voxcpm_api_base=http://127.0.0.1:8110`，`latentsync_api_base=http://127.0.0.1:8101`。
- Docker 旁路容器仍健康：`127.0.0.1:8120/health` 和 `127.0.0.1:8121/health` 都返回 ok。
- Bot `127.0.0.1:8017/status/check` 返回 ok。
