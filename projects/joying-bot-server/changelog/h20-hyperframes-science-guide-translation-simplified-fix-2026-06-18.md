---
date: 2026-06-18
project: joying-bot-server
type: changelog
tags: [changelog, h20, hyperframes, science-guide, subtitles, llm]
aliases: [h20-hyperframes-science-guide-translation-simplified-fix-2026-06-18]
---

# H20 HyperFrames science_guide 翻译与简体字幕修复

## 改动类型

Bugfix / 网感视频后处理对齐。

## 背景

测试库 `t_video_generate_task` 中 `task_id=1289` 的 `science_guide` 产物出现两个问题：

- 中文字幕看起来混有繁体字。
- 原项目应有的英文翻译字幕没有出现在视频中。

只读排查测试服产物时，`subtitle_timeline.json` 中 `styled_cards translated=0`，且字幕卡文本本身已经包含繁体字符，例如 `這`、`視頻`、`關注`、`優質`。因此根因不是字体把简体显示成繁体，而是进入 HyperFrames 模板前的数据已经偏繁体，同时翻译步骤没有拿到可用 LLM 配置。

## 原项目对照

`C:\Users\admin\Desktop\AIGCVideo_副本` 的相关逻辑：

- `src/steps/2-asr.js` 调豆包 ASR 时显式传 `language: zh-CN`，原项目输入通常天然是简体。
- `src/steps/3.6-styled-subtitles.js` 在 `buildRawCards()` 后调用 `translateCards()`，批量把字幕卡文本翻译成英文，填入 `translation` 字段。
- 原项目翻译依赖 Ark `/responses` 与 `DOUBAO_ARK_API_KEY`。

H20 当前链路使用 Whisper 产出时间轴，不复用原项目 ASR，所以需要在 H20 adapter 层补简体标准化；翻译调用则沿用 H20 已有 OpenAI-compatible `vllm_api + /chat/completions`，避免混用 proxy 配置或新增另一套不可维护的 key 方式。

## 改动内容

- `hyperframes-postprocess/index.js`
  - 自动读取 H20 app config：优先 `APP_CONFIG_FILE`，再尝试 release 目录下 `config/config-dev.json`、`config-dev.json`、`config/config.json`。
  - LLM 配置推断新增 `vllm_api` 兜底：无 Ark key 时使用 H20 现有 `vllm_api`，`apiKey=EMPTY`，默认模型 `/models/Qwen3-14B`。
  - 保持 `DOUBAO_ARK_API_KEY`、`HF_POSTPROCESS_LLM_*` 的显式覆盖优先级。
  - 增加字幕文本繁转简归一化，将 Whisper segment text 与 keyword 在进入 styled cards 前转成简体。
  - 这不是替代原项目翻译逻辑，而是在 H20 adapter 层补齐原项目 ASR `zh-CN` 带来的前置保证。
- `hyperframes-postprocess/templates/template4.html`
  - 保留 diary 开场标题自适应逻辑，避免长标题溢出封面框。
- `test/test_hyperframes_postprocess.py`
  - 新增 H20 `vllm_api` 配置兜底翻译测试。
  - 新增繁体 Whisper 文本归一化为简体的测试。
  - 增加 diary 开场标题 fit 逻辑断言。
  - 修复 fake ffprobe 测试辅助脚本漏 `import os` 的问题，避免测试环境误报。

## 影响范围

- 影响 `science_guide` 的 styled subtitle 生成和翻译。
- 影响 `video_diary` 开场标题自适应。
- `minimal` 仍为旧链路，不进入 HyperFrames postprocess。
- 不改数据库字段，不改 CRM/CSM 回调口径，不改测试服专属逻辑。

## 验证结果

本地通过：

```powershell
node --check hyperframes-postprocess\index.js
python -m unittest test.test_hyperframes_postprocess test.test_hyperframes_cli test.test_hyperframes_analysis test.test_hyperframes_upload_callback test.test_template_route -v
python -m py_compile scheduler/collect_scheduler.py router/service/video_server2/hyperframes_analysis.py router/service/video_server2/hyperframes_cli.py
```

结果：101 个相关单测通过；Python 编译通过。

## 后续验收

发布到 test 后重新提交 `science_guide`：

- 检查 `subtitle_timeline.json` 中 `styled_cards[*].text` 是否为简体。
- 检查 `styled_cards[*].translation` 是否有英文内容，`translated_count` 应大于 0。
- 人工抽帧确认中文字幕不再混繁体，英文翻译行出现。

## 相关文件

- `hyperframes-postprocess/index.js`
- `hyperframes-postprocess/templates/template4.html`
- `test/test_hyperframes_postprocess.py`
- `C:\Users\admin\Desktop\AIGCVideo_副本\src\steps\2-asr.js`
- `C:\Users\admin\Desktop\AIGCVideo_副本\src\steps\3.6-styled-subtitles.js`

## 图谱链接

- [[projects/joying-bot-server/00-项目概览|项目概览]]
- [[projects/joying-bot-server/changelog/00-changelog-index|更新日志索引]]
- [[projects/joying-bot-server/changelog/h20-hyperframes-diary-opening-bgm-adapter-fix-2026-06-18|h20-hyperframes-diary-opening-bgm-adapter-fix-2026-06-18]]
