---
name: image-vision
description: Use when you need to view or analyze an image file (PNG, JPG, WebP, GIF, BMP) but lack vision capabilities. Also use when the user asks "what's in this image" or "look at this screenshot". Invokes a Python script that calls the SiliconFlow Qwen/Qwen3.6-35B-A3B vision model API to get a detailed description of the image content.
---

# Image Vision

> ⚠️ **跨设备迁移**：本 skill 含硬编码路径和平台配置，换设备后需注意：
>
> | 硬编码/配置 | 位置 | 新设备应改为 |
> |------------|------|-------------|
> | `C:/Users/admin/.claude/skills/image-vision/vision.py` | Usage 示例 | 新设备的 skill 安装路径 |
> | `SILICONFLOW_API_KEY` 环境变量 | 不硬编码，但需在新设备重设 | `setx SILICONFLOW_API_KEY "新密钥"` |
> | `pip install requests` | 依赖 | Python 环境需装 requests 包 |

通过硅基流动（SiliconFlow）的 Qwen 视觉模型识别图片内容。

## When to Use

- 需要查看/分析图片内容，但没有视觉能力
- 用户说"看看这张图"、"这个截图里有什么"
- 需要从 UI 截图、图表、照片中提取信息

## Usage

```
python <skill-dir>/vision.py <图片路径> [可选提示词]
```

返回 JSON：`{"model": "...", "content": "图片描述...", "usage": {...}}`

### Example

```bash
python C:/Users/admin/.claude/skills/image-vision/vision.py screenshot.png "这张截图里有什么按钮和文字？"
```

## API Key

密钥通过环境变量传入，不写在代码里：

```
SILICONFLOW_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
```

设置方法（Windows PowerShell）：

```powershell
[Environment]::SetEnvironmentVariable("SILICONFLOW_API_KEY", "你的密钥", "User")
```

设置后需重启终端生效。（脚本已内置 Windows 用户环境变量自动检测，即使未重启也能读取到密钥。）

## 常见问题

### GBK 编码报错

Windows 终端默认使用 GBK 编码，Python 输出 emoji 等 Unicode 字符时会报 `UnicodeEncodeError`。解决：

```bash
export PYTHONIOENCODING=utf-8 && python <skill-dir>/vision.py <图片路径> [提示词]
```

### API Key 未生效

脚本会自动从以下两个来源加载密钥：
1. 当前进程环境变量 `SILICONFLOW_API_KEY`
2. Windows 用户级环境变量（无需重启终端）

如果都读取不到，会返回明确错误提示。

## Supported Formats

PNG, JPG/JPEG, WebP, GIF, BMP
