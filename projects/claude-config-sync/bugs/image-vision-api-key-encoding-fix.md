---
date: "2026-05-28"
status: fixed
severity: medium
tags: [bug]
---

# image-vision skill 调用报错修复

## 问题描述

调用 image-vision skill 的 vision.py 时遇到三个连续问题导致图片识别失败。

## 复现步骤

1. Clone skill 到新设备，按文档设置 `SILICONFLOW_API_KEY` 用户环境变量
2. 不重启终端直接调用 skill
3. 在 Windows Git Bash 或 bash 环境中执行

## 问题一：API Key 环境变量未生效

**原因**：用户通过 `[Environment]::SetEnvironmentVariable` 设置了 Windows 用户级环境变量（写入注册表），但当前进程的环境变量块不会自动刷新。`os.environ.get()` 只能读到进程级别的变量。

**修复**：vision.py 新增 `_load_api_key()` 函数，当进程环境变量读不到时，通过 `subprocess` 调用 PowerShell 从 Windows 注册表读取用户级环境变量。无需重启终端即可使用。

## 问题二：bash 下误用 CMD 的 SET 命令

**原因**：`SET SILICONFLOW_API_KEY=xxx` 是 Windows CMD 语法，在 bash 环境会报 `command not found`。

**修复**：问题一修复后不再需要手动临时注入环境变量，从根本上避免了这个问题。

## 问题三：Windows GBK 编码无法输出 emoji

**原因**：vision.py 调用成功返回 JSON 中含有 emoji 字符（如 `\U0001f4a1`），Windows 终端默认 GBK 编码无法编码这些字符，抛出 `UnicodeEncodeError: 'gbk' codec can't encode character`。

**修复**：main() 开头增加 `sys.stdout.reconfigure(encoding='utf-8', errors='replace')`，强制 stdout 使用 UTF-8 编码输出。同时 SKILL.md 补充了 `export PYTHONIOENCODING=utf-8` 用法说明。

## 修复方案

三处改动：

| 文件 | 改动 |
|------|------|
| `vision.py` | 新增 `_load_api_key()` — 自动从 Windows 注册表读取用户环境变量 |
| `vision.py` | `main()` 增加 `sys.stdout.reconfigure(encoding='utf-8')` — 解决 GBK 编码问题 |
| `SKILL.md` | 补充故障排查文档（GBK 编码 + API Key 加载机制说明） |

## 相关文件

- `C:\Users\admin\.claude\skills\image-vision\vision.py`
- `C:\Users\admin\.claude\skills\image-vision\SKILL.md`
