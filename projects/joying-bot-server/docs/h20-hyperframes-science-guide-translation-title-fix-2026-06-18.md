---
tags: [project, h20, hyperframes, template, fix-record]
---

# H20 HyperFrames 科普指南字幕翻译与标题自适应修复记录

日期：2026-06-18

## 背景

用户对比本地 `C:\Users\admin\Desktop\AIGCVideo_副本` golden 视频后指出：科普指南模板当前 H20 产物缺少中文字幕下方的英文翻译字幕，并且开头前 2 秒顶部标题字号过大，会超出标题框。

同时要求继续遵守：能复用原项目逻辑就复用，不要重新造一套近似逻辑；`minimal` 极简旧链路不能被网感链路改动影响。

## 排查结论

1. 原项目英文字幕来自 `src/steps/3.6-styled-subtitles.js` 的 `translateCards(cards)`：
   - 先生成 styled cards；
   - 再调用豆包 Ark 接口；
   - 把每张卡片中文短语翻译成 4 个词以内英文；
   - 写入 `card.translation`。
2. 原项目 `templates/universal.html` 只有在 `card.translation` 非空时才渲染英文行。
3. H20 当前 `hyperframes-postprocess/index.js` 已迁入 styled card 结构，但 `buildStyledCards(cues)` 直接把 `translation` 留空，没有迁入原项目的 LLM 翻译步骤，所以模板逻辑存在但数据为空。
4. 顶部 quote 标题溢出不是封面图问题，而是 opening title 的 HTML 层字号固定偏大；长标题来自 H20 结构化分析后更容易触发该问题。

## 本轮修复

1. 在 H20 `hyperframes-postprocess/index.js` 增加 `translateStyledCards`，复用原项目“styled card 后做批量英文翻译”的逻辑，但接口调用方式沿用 H20 现有 `doubao_headline.py` 的 Ark `chat/completions` 口径，不再新引入 `/responses`：
   - 返回 JSON 数组；
   - 顺序与输入 cards 对齐；
   - 每条英文尽量短；
   - 写回 `styled_cards[*].translation`。
2. Node 后处理入口会读取：
   - `DOUBAO_ARK_API_KEY`
   - `DOUBAO_ARK_MODEL`
   - `DOUBAO_ARK_BASE_URL`
   - 兼容 `HF_POSTPROCESS_LLM_API_KEY/HF_POSTPROCESS_LLM_MODEL/HF_POSTPROCESS_LLM_BASE_URL`
3. Node 后处理会补充读取 `hyperframes-postprocess/.env`、项目根 `.env`、以及 H20 服务启动时写入环境变量的 `APP_CONFIG_FILE` 指向的 bot 配置 JSON，避免 Python 能读到配置但 Node 后处理读不到。
4. `APP_CONFIG_FILE` 里当前只兼容明确的豆包/Ark 字段：`doubao_ark_api_key`、`doubao_api_key`、`doubao_ark_model`、`doubao_model`、`doubao_ark_base_url`。不要把 `proxy_api_key` 当豆包 key 使用；本地配置里的 `proxy_api_host` 是代理 IP 服务地址，混用会导致翻译接口鉴权失败且误导排查。
5. 翻译失败或未配置 key 时不阻断任务，保持原项目“翻译失败则无英文字幕继续渲染”的容错口径。
6. 在 `hyperframes-postprocess/templates/universal.html` 的 `buildOpeningCoverTop(styleKey === 'quote')` 中增加 `fitSingleLineTitle`，按标题视觉长度在 `108px -> 56px` 范围内收缩字号，避免顶部 quote 标题溢出。
7. `minimal` 不进入 HyperFrames postprocess，极简旧链路不受影响。

## 验证

1. `python -m unittest test.test_hyperframes_postprocess test.test_hyperframes_cli test.test_hyperframes_analysis test.test_hyperframes_upload_callback test.test_template_route -v` 通过，96 项。
2. `python -m unittest test.test_hyperframes_postprocess -v` 通过，16 项，包含 `APP_CONFIG_FILE` 读取 bot 配置中的豆包 key 的用例。
3. `python -m py_compile scheduler/collect_scheduler.py router/service/video_server2/hyperframes_analysis.py router/service/video_server2/hyperframes_cli.py` 通过。
4. `node --check hyperframes-postprocess\index.js` 通过。

## 后续 Test 验收重点

1. 测试服必须确认 Node 后处理运行环境实际能读到豆包 Ark key，否则任务会成功但没有英文翻译行。优先检查服务进程环境变量 `APP_CONFIG_FILE` 指向的 JSON 是否包含 `doubao_ark_api_key` 或 `doubao_api_key`。
2. 重新提交 `science_guide`，抽查首 2 秒顶部标题不再出框，并确认 styled card 下方出现英文短字幕。
3. 重新提交 `video_diary` 和 `minimal`，确认 diary 日期/标题逻辑不回退，minimal 旧链路不受影响。
