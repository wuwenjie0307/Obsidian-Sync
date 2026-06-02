---
date: "2026-06-02"
tags: [bug, h20, docker, latentsync, dependency]
status: fixed-in-h20-sidecar-pending-gitlab
severity: medium
---

# h20 LatentSync Docker 真实 lip-sync 500

## 问题描述

LatentSync Docker 容器 `/health` 正常，但真实调用：

```bash
POST http://127.0.0.1:8121/v1/lip-sync
```

返回 HTTP 500。

最初错误发生在导入阶段，不是视频/音频 URL 参数问题。

## 原因

容器基础镜像复用了 ComfyUI 环境，里面的 Python 依赖栈和 h20 裸机 LatentSync 可用环境不一致。

关键差异：

- Docker：Python 3.11，Torch 2.9/cu128，`scipy 1.16.3`，`jax 0.4.26`，`peft 0.18.0`。
- 裸机：Python 3.10，Torch 2.5/cu121，`scipy 1.15.3`，`jax 0.6.2`，无 `peft`。

具体触发点：

1. `scipy.special` 导入失败：`All ufuncs must have type numpy.ufunc`。
2. `ml_dtypes/jax` 组合触发递归错误。
3. 修完上面后，`scripts.inference` 又因 `peft 0.18.0` 与 `accelerate 0.26.1` 不兼容导入失败。

## 解决方案

在 LatentSync Docker 内新增独立 venv：`/opt/latentsync-venv`。

- 使用 `--system-site-packages` 复用基础镜像里的 Torch。
- 在 venv 内覆盖安装与裸机更接近、且已验证可导入的依赖版本。
- 覆盖 `peft==0.10.0`，避免基础镜像自带 `peft 0.18.0` 触发 Diffusers 导入失败。
- Docker 启动后 `python` 指向 venv。

## 验证结果

已验证导入：

```text
IMPORT_OK scipy.special
IMPORT_OK sklearn
IMPORT_OK peft
IMPORT_OK scripts.inference
```

已验证真实请求：

```text
POST /v1/lip-sync -> HTTP 200
输入视频 3.60s
输入音频 3.52s
输出视频 /tmp/latentsync-docker-test-ok.mp4
输出视频 3.60s
耗时约 135s
```

## 仍需处理

- 本地提交已生成，但 GitLab 推送时本机无法解析 `git.joyingai.cn`，需要网络恢复后补推。
- h20 直接从 GitHub clone `ByteDance/LatentSync` 超时，后续要整理为可复现的离线构建方式。
- 目前 Bot 还没有切到 Docker，因为测试库存在待处理/处理中任务，`t_comfyui_config.id=1` 仍是 `is_active=2`。

## 优化点

- Dockerfile 需要减少对外网 GitHub 的依赖。
- 后续如果要接入生产式模型池，需要将 Docker 服务地址写入并读取 `t_comfyui_config`，而不是只依赖全局配置。
- LatentSync 的测试素材必须保证全程有人脸，否则会在推理时出现 `Face not detected`，这属于素材质量问题，不是 Docker 依赖问题。

