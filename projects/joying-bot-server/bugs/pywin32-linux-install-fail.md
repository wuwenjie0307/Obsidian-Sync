---
date: 2026-05-27
status: fixed
severity: medium
tags: [bug, deploy]
---

# pywin32/pypiwin32 Linux 安装失败

## 问题描述

在 h20（Ubuntu 22.04, Python 3.10.13）上 `pip install -r requirements.txt` 时报错：

```
ERROR: Could not find a version that satisfies the requirement pywin32==306
ERROR: No matching distribution found for pywin32==306
ERROR: Could not find a version that satisfies the requirement pywin32>=223 (from pypiwin32)
```

pypiwin32 也因依赖 pywin32 无法安装。

## 原因

`pywin32` 是 **Windows 专属包**（Win32 API 绑定），在 Linux 系统上没有对应的 wheel，pip 找不到任何可用版本。

`pypiwin32` 依赖 `pywin32>=223`，所以也装不了。这两个包在 `requirements.txt` 中是从 Windows 开发环境带过来的，不应出现在 Linux 部署的依赖列表中。

## 解决方案

从 `requirements.txt` 中移除这两个包：

```bash
grep -v "pywin32\|pypiwin32" requirements.txt > requirements.tmp && mv requirements.tmp requirements.txt
```

然后在 git 中将对应行注释掉而非删除（保留给 Windows 开发用）：

```
# pywin32==306  # Windows only, removed for Linux
# pypiwin32==223  # Windows only, removed for Linux
```

## 优化点

- `requirements.txt` 应区分平台，或使用 `sys_platform` 条件：`pywin32==306; sys_platform == 'win32'`

## 相关文件

- `requirements.txt`
