---
date: 2026-05-27
status: fixed
severity: high
tags: [bug, cuda, deploy]
---

# torchaudio 版本不匹配导致 libcudart.so.13 缺失

## 问题描述

torch 降级到 2.5.1 后，`from voxcpm import VoxCPM` 报错：

```
OSError: libcudart.so.13: cannot open shared object file: No such file or directory
```

发生在 `torchaudio/__init__.py` 加载 `_torchaudio` 扩展时。

## 原因

`voxcpm` 安装的 torchaudio 2.11.0 依赖 CUDA 13.0 运行时库（libcudart.so.13），与降级后的 torch 2.5.1（CUDA 12.4）和服务器驱动不匹配。

## 解决方案

将 torchaudio 也降级到与 torch 2.5.1 匹配的版本：

```bash
pip install torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124
```

## 优化点

- torch/torchaudio 版本必须配套，降级 torch 后务必同步降级 torchaudio

## 相关文件

- `requirements.txt`
