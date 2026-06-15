---
date: "2026-06-15"
project: joyingbot-new
type: changelog
tags: [changelog, h20-test, voice-clone, tts, text-normalization, voxcpm]
aliases: ["声音克隆 TTS 面积单位 m² 规范化"]
---

# 声音克隆 TTS 面积单位 m² 规范化

## 图谱链接

- 项目: [[projects/joyingbot-new/00-项目概览|joyingbot-new]]
- 索引: [[projects/joyingbot-new/changelog/00-changelog-index|更新日志索引]]

## 改动类型

- [ ] 新功能
- [x] Bug 修复
- [ ] 重构
- [ ] 配置变更
- [ ] 文档

## 背景

个人形象试听/视频生成的房产文案里经常出现 `m²`、`㎡`、`m2`、`M 2` 等面积单位。VoxCPM 声音克隆直接读这些符号时，可能读不出“平方米”的自然发音，影响试听和正式视频口播效果。

本次改动目标：在文本送入 VoxCPM clone-voice 前，把明确的面积单位统一转成中文“平方米”。

## 改动内容

相关提交：

```text
91c3172b fix: normalize area units for voice clone tts
时间: 2026-06-15 15:05:43 +0800
分支: feature/ai_v6.3.1_video -> test
```

核心改动：

1. `router/service/video_server2/voxcpm_tts.py`
   - 新增 `normalize_tts_text_for_voice_clone(text)`。
   - 在 `build_clone_voice_payload()` 中对 `text` 做规范化后再传给 VoxCPM。
   - 在 `clone_voice_and_synthesize()` 中也先规范化文本；即使降级到旧 TTS 入口，也使用规范化后的文本。

2. `router/service/video_server/voxcpm_api.py`
   - H20 VoxCPM API 侧同样新增 `normalize_tts_text_for_voice_clone(text)`。
   - `/v1/clone-voice` 内部在分段前先规范化 `req.text`，保证服务端兜底，即使调用方没清洗也能正确处理。

3. 测试覆盖
   - 新增 `test/test_voxcpm_tts_text_normalization.py`。
   - 更新 `test/test_voxcpm_voice_style_prompt.py`。

## 规范化规则

会转换：

```text
120m² -> 120平方米
90㎡ -> 90平方米
88 m2 -> 88平方米
76 M 2 -> 76平方米
m^2 / M^2 / 全角 mＭ 相关写法 -> 平方米
```

不会误转：

```text
M2芯片 -> M2芯片
```

原因：`m2/M2` 只有在数字后面出现时才按面积单位处理，避免把产品型号、芯片型号、版本号误读成平方米。

## 影响范围

- 影响声音克隆试听接口的 `text`。
- 影响正式视频生成链路调用 VoxCPM 时的 `text`。
- 影响 H20 VoxCPM 服务 `/v1/clone-voice` 内部文本分段前的文本。
- 不影响音色样本 URL、模型池端口选择、Docker 容器、DB `t_comfyui_config` 状态。

## 与 7001 试听故障的关系

这次 `m² -> 平方米` 是文本规范化改动，发生在请求进入 VoxCPM clone-voice 前或 H20 API 分段前。

2026-06-15 下午试听突然失败的直接根因是：`voice_audition_url` 资源池启用了 `http://127.0.0.1:7001`，但 H20 上 7001 没有服务监听，后端调用时报 `Connection refused`。

因此两者时间接近，但属于不同层：

- `91c3172b`: 文案/TTS 文本清洗。
- 7001 故障: 测试服运行态模型池配置指向不可用端口。

## 验证结果

提交时测试覆盖：

```text
python -m unittest test.test_voxcpm_tts_text_normalization
python -m unittest test.test_voxcpm_voice_style_prompt
```

本次记录时查看提交统计：

```text
router/service/video_server/voxcpm_api.py  |  11 ++-
router/service/video_server2/voxcpm_tts.py |  20 +++++-
test/test_voxcpm_tts_text_normalization.py | 105 +++++++++++++++++++++++++++++
test/test_voxcpm_voice_style_prompt.py     |  12 ++++
4 files changed, 144 insertions(+), 4 deletions(-)
```

## 相关文件

- `router/service/video_server2/voxcpm_tts.py`
- `router/service/video_server/voxcpm_api.py`
- `test/test_voxcpm_tts_text_normalization.py`
- `test/test_voxcpm_voice_style_prompt.py`

## 相关记录

- [[projects/joyingbot-new/bugs/2026-06-15_voice_audition_route_and_pool_7001|测试服试听接口 404 与 VoxCPM 7001 端口失效]]
- [[projects/joyingbot-new/bugs/2026-06-09_voice_clone_audition_video_consistency|试听与视频生成声音克隆行为不一致]]

## 相关 Commit

- `91c3172b fix: normalize area units for voice clone tts`
