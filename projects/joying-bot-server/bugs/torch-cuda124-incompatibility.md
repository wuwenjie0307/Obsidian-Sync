---
date: 2026-05-27
status: fixed
severity: high
tags: [bug, cuda, deploy]
---

# torch 2.12.0 CUDA 12.4 驱动不兼容

## 问题描述

在 h20（CUDA 12.4）上 `pip install voxcpm` 自动安装了 torch 2.12.0（CUDA 12.8），导致：

```python
>>> import torch; torch.cuda.is_available()
False

# 警告信息:
# The NVIDIA driver on your system is too old (found version 12040).
# Please update your GPU driver...
```

VoxCPM 模型无法使用 GPU 推理。

## 原因

`voxcpm` 依赖的 torch 最新版（2.12.0）编译时使用 CUDA 12.8，而 h20 服务器的 NVIDIA 驱动仅支持到 CUDA 12.4。CUDA 版本不匹配导致 PyTorch 无法加载 GPU。

## 解决方案

降级到 CUDA 12.4 兼容版本：

```bash
pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cu124
```

## 优化点

- `requirements.txt` 中建议锁定 torch 版本以防 pip 自动升级
- 注意 `pip install voxcpm` 会重新拉取最新 torch，应在装完 voxcpm 后立即降级

## 相关文件

- `requirements.txt`
