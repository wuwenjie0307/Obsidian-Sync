---
date: 2026-05-28
tags: [changelog]
---

# 新模型 API 测试全部通过

## 改动类型

- [x] 新功能
- [x] Bug 修复
- [ ] 重构
- [x] 配置变更

## 改动内容

### VoxCPM 声音克隆测试

1. 初测 → 效果差，音频模糊听不懂
2. 排查：`reference_text` 未传，模型无法对齐音素
3. 修复：换用正确 reference_text 的参考音频 → 效果清晰
4. 修代码：voxcpm_tts.py 函数签名新增 `reference_text`、`voice_emotion`、`voice_speed`、`voice_volume` 可选参数
5. 复测：效果 OK，吐字准确

### LatentSync 唇形同步测试

1. 用 17s 测试视频 + VoxCPM 合成音频
2. API 调用成功，输出 3.44s 嘴型对齐视频
3. 效果确认 OK

### 端到端串联测试（2026-05-28 17:10）

完整链路测试通过：VoxCPM → LatentSync

| 阶段 | 耗时 | 输出 |
|------|------|------|
| VoxCPM 声音克隆 | 1.8s | 338 KB WAV |
| LatentSync 唇形同步 | 65.7s | 826 KB MP4 |
| **总耗时** | **67.5s** | — |

- 输出格式：h264 + aac 16000Hz mono
- 测试文本："今天天气真好，适合出去走走"
- 测试脚本：`tools/test_e2e_video.py`
- 并发保护已启用（VoxCPM Semaphore(2), LatentSync Semaphore(1)）

### 参数链路修复

- CRM voice_emotion/speed/volume → submit 路由 → video_work → clone 函数 → VoxCPM API
- 6 个文件修改，旧代码未删除
- voice_speed 白名单对齐 CRM 规范（移除 0.5，仅 0.75~3.0）
- voice_emotion 兼容 int/str 两种格式

### 代码同步到 h20

- 全量打包上传覆盖
- VoxCPM API 重启加载新代码

## 影响范围

- `router/service/video_server/voxcpm_tts.py`
- `router/service/video_server2/voxcpm_tts.py`
- `router/service/video_server/video_work.py`
- `router/service/video_server2/video_work.py`
- `router/crm_server.py`
- `router/service/video_server/voxcpm_api.py`

## 相关 Commit

- 未推送（通过 SCP 同步到 h20）
