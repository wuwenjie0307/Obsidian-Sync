---
date: 2026-06-11
project: joyingbot-new
type: changelog
tags: [changelog, h20, voxcpm, voice-clone, audio-noise, voice-drift]
aliases: [VoxCPM 长文本分段生成]
---

# VoxCPM 长文本分段生成

## 改动类型

- 后端音色克隆稳定性优化
- H20 VoxCPM 服务端内部实现调整
- 回归测试补充

## 改动内容

- 基于 VoxCPM 官方文档和 GitHub Issue #302 中对长文本音色漂移的说明，采用服务端分段生成方案，不改前端、不改请求协议、不改 VoxCPM 上游源码。
- 在 `router/service/video_server/voxcpm_api.py` 中新增长文本分段逻辑：
  - 默认目标段长 `VOICE_CLONE_SEGMENT_TARGET_CHARS = 80`。
  - 硬上限 `VOICE_CLONE_SEGMENT_HARD_LIMIT_CHARS = 120`。
  - 优先按 `。！？!?；;` 切分并保留标点。
  - 单段过长时再按 `，,、：:` 软切，仍过长则按硬长度切分。
- `/v1/clone-voice` 下载参考音频仍只做一次，但会把 `text` 拆成多个短段，每段都重新向 VoxCPM 注入同一个参考音频，再用 `np.concatenate` 合并为一条音频。
- Hi-Fi 模式每段调用 `voxcpm_model.generate(text=segment_text, prompt_wav_path=ref_path, prompt_text=reference_text)`。
- controllable 模式每段先重新套 `build_voice_style_prompt(...)`，再调用 `voxcpm_model.generate(text=styled_segment, reference_wav_path=ref_path)`。
- 合并音频后继续统一执行既有 `apply_audio_effects(...)`，保留前一轮 `limit_audio_peak(...)` 峰值保护，避免写 WAV 前硬削波。
- 日志补充 `mode`、`segment_count`、`segment_index`、`segment_text_len`、`segment_preview`、`raw_text_len`、`reference_text_len`，方便后续排查长文本漂移和分段效果。

## 影响范围

- `POST /v1/clone-voice` 请求体和返回仍保持不变。
- `router/service/video_server2/voxcpm_tts.py` payload 不需要调整。
- `router/crm_server.py` 的试听接口不需要调整。
- 试听音色克隆和正式视频生成都会自动受益，因为两条链路最终都调用同一个 VoxCPM HTTP 服务。
- 当前修复目标是降低长文本单次生成导致的音色漂移、后半段不稳定、嗡嗡/毛刺风险；不引入 `voice_anchor_strength` 源码补丁。

## 验证结果

- 先按 TDD 写入分段和 AST 约束测试，首次运行 `python -m unittest test.test_voxcpm_voice_style_prompt` 失败，失败点符合预期：缺少 `split_voice_clone_text`、分段常量、`generate_voice_clone_segment` 和分段日志字段。
- 实现后运行系统 Python：
  - `python -m unittest test.test_voxcpm_voice_style_prompt`
  - 结果：`Ran 25 tests`，`OK (skipped=2)`。
  - 跳过原因：系统 Python 缺少 numpy，峰值相关测试跳过。
- 使用 Codex bundled Python 运行：
  - `C:\Users\admin\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe -m unittest test.test_voxcpm_voice_style_prompt`
  - 结果：`Ran 25 tests`，`OK`。
- 语法检查：
  - `python -m compileall router/service/video_server/voxcpm_api.py`
  - 结果：退出码 0。

## GitLab 与测试服生效注意

- 个人分支：`lucky-test/voxcpm-long-text-segments`。
- 提交：`3ef3d51e fix: segment VoxCPM long text generation`。
- 已 fast-forward 合并并推送到 `origin/test`。
- 服务吃到这次新代码的关键不在 `8100` botserver，而在 VoxCPM 模型 API 服务是否重新加载了 `router/service/video_server/voxcpm_api.py`。
- 如果测试服通过 Docker 跑 VoxCPM，必须重启或 recreate 所有 VoxCPM 容器/端口，例如 `8120/8122/8124/8126/8128/8129/8130/8131`。
- `8100 / 8017 / 18017` 这次理论上不是必须重启，因为请求协议和 `voxcpm_tts.py` payload 没变；但如果发布流程切换 release symlink，为保证整套服务指向同一 release，可以一起重启 botserver 和 scheduler。
- 生效检查不要只看宿主机 Git 代码，要检查运行时文件是否有分段标记：
  - `VOICE_CLONE_SEGMENT_TARGET_CHARS`
  - `split_voice_clone_text`
  - `generate_voice_clone_segment`
- VoxCPM 健康检查使用 `/<voxcpm_port>/health`；botserver 使用 `/status/check`。`8100 /health` 返回 404 不代表 VoxCPM 异常。

## 相关文件

- `router/service/video_server/voxcpm_api.py`
- `test/test_voxcpm_voice_style_prompt.py`

## 相关记录

- [[projects/joyingbot-new/bugs/2026-06-11_voice_clone_speech_buzz_noise|生成视频口播嗡嗡噪音]]
- [[projects/joyingbot-new/docs/2026-06-11_voxcpm_noise_fix_deploy_runbook|VoxCPM 试听噪音修复部署 Runbook]]
- [[projects/joyingbot-new/changelog/2026-06-11_h20_preview_audio_reuse_flat_payload|H20 试听音频复用 flat payload]]

## 图谱链接

- [[projects/joyingbot-new/00-项目概览|joyingbot-new 项目概览]]
- [[projects/joyingbot-new/changelog/00-changelog-index|更新日志索引]]
