---
tags: [reference, tools]
date: 2026-05-28
---

# Image-Vision 视觉识别 Skill 配置

## 用途

Claude Code（DeepSeek-V4-Pro）没有视觉能力，遇到需要看图时调用此 skill，通过硅基流动的 Qwen 视觉模型来识别图片内容。

## 技术方案

| 项 | 值 |
|------|-----|
| 平台 | 硅基流动（SiliconFlow） |
| 模型 | Qwen/Qwen3.6-35B-A3B |
| API 地址 | `https://api.siliconflow.cn/v1/chat/completions` |
| 调用方式 | Python 脚本 `vision.py` → HTTP POST → 返回 JSON |
| Skill 路径 | `C:\Users\admin\.claude\skills\image-vision\` |
| 默认 max_tokens | 16384（可通过 `SILICONFLOW_MAX_TOKENS` 环境变量覆盖） |

## 使用方式

```bash
python C:/Users/admin/.claude/skills/image-vision/vision.py "图片路径" "可选提示词"
```

返回 JSON：
```json
{
  "model": "Qwen/Qwen3.6-35B-A3B",
  "content": "图片描述...",
  "usage": {"prompt_tokens": 131, "completion_tokens": 505, "total_tokens": 636}
}
```

---

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `SILICONFLOW_API_KEY` | API 密钥（必填） | 无 |
| `SILICONFLOW_MODEL` | 模型名 | `Qwen/Qwen3.6-35B-A3B` |
| `SILICONFLOW_MAX_TOKENS` | 最大输出 token 数 | `16384` |

设置方式同 API Key，通过 `setx` 写入注册表或 PowerShell `[Environment]::SetEnvironmentVariable`。

---

## API 密钥管理

### 密钥存储位置

| 存储方式        | 路径                                                  |
| ----------- | --------------------------------------------------- |
| Windows 注册表 | `HKEY_CURRENT_USER\Environment\SILICONFLOW_API_KEY` |
| 设置命令        | `setx SILICONFLOW_API_KEY "sk-xxxxxxxx"`            |

`setx` 命令将环境变量永久写入注册表，所有新启动的进程都能读取。

### 离职前删除密钥

**方法一：PowerShell 命令（推荐）**

```powershell
Remove-ItemProperty -Path "HKCU:\Environment" -Name "SILICONFLOW_API_KEY" -Force
```

**方法二：CMD 命令**

```cmd
REG DELETE HKCU\Environment /v SILICONFLOW_API_KEY /f
```

**方法三：GUI 手动删除**

1. 按 `Win + R` → 输入 `sysdm.cpl` → 回车
2. 点击「高级」→「环境变量」
3. 在「用户变量」中找到 `SILICONFLOW_API_KEY` → 点击「删除」
4. 确定保存

### 验证是否删除成功

**PowerShell：**
```powershell
Get-ItemProperty -Path "HKCU:\Environment" -Name "SILICONFLOW_API_KEY"
# 报错 "Property SILICONFLOW_API_KEY does not exist" = 已删除
```

**CMD：**
```cmd
REG QUERY HKCU\Environment /v SILICONFLOW_API_KEY
# 报错 "错误: 系统找不到指定的注册表项或值" = 已删除
```

### 注意事项

- `setx` 设置的变量**对当前已打开的终端不生效**，只对新打开的窗口生效
- 删除后需要**重启终端**（VS Code / CMD / PowerShell）才会在环境中消失
- 如果有多个用户账号，只影响当前用户（HKCU）
- 硅基流动平台本身的 API Key 也应在平台侧删除/禁用（登录 siliconflow.cn → API 密钥管理）
