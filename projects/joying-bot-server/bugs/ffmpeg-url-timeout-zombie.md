---
date: "2026-05-25"
status: fixed
severity: medium
tags: [bug]
---

# URL模式ffmpeg超时导致进程僵尸

## 问题描述

URL 模式下的 ffmpeg 抽音过程没有超时限制，当远端 URL 无响应或网络异常时，ffmpeg 进程会一直挂起，导致系统资源泄露。

## 原因

`comfyui_src/` 中调用 ffmpeg 时未设置 `timeout` 参数，ffmpeg 默认会无限等待远端数据。

## 复现步骤

1. 向服务器发送一个指向不可达 URL 的音频处理请求
2. ffmpeg 开始拉流但远端无响应
3. 进程卡死，不释放资源

## 修复方案

在 ffmpeg 命令行中添加 `-timeout` 参数（单位微秒），限制拉流等待时间。超时后 ffmpeg 自动退出，上层代码捕获异常后走下载模式回退。

## 优化点

- 同时给 ffmpeg 进程外层加了 `subprocess.run(timeout=...)` 双重保险
- URL 模式失败后自动回退到下载模式，提高成功率

## 相关文件

- comfyui_src/
