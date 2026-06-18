---
date: "2026-06-18"
project: "joying-bot-server"
type: doc
tags: [h20, hyperframes, vibevideo, template, migration]
aliases: ["H20 网感视频 template3 quote 迁移决策"]
---

# H20 网感视频 template3 quote 迁移决策 2026-06-18

## 图谱链接

- 项目: [[projects/joying-bot-server/00-项目概览|joying-bot-server]]
- 索引: [[projects/joying-bot-server/docs/00-docs-index|参考文档索引]]

## 背景

用户和同事提供了原项目 `AIGCVideo_副本` 的本地 golden 运行参数：

- 视频日记：`npm start -- --template=4 --cover=diary`
- 科普指南：`npm start -- --template=3 --cover=quote`

这说明此前 H20 将 `science_guide` 映射为 `template-7 + wanggan` 的结论已经被实际 golden 参数推翻。后续不能继续按 `template7/wanggan` 作为科普指南默认风格。

## 根因判断

H20 当前后处理曾只迁移 `template4.html` 与 `template7.html`，缺少原项目 `template-3` 使用的 `templates/universal.html` 路线。

原项目 `template-3` 的关键合同是：

- `subtitleMode: styled`
- `coverStyle: quote`
- 默认渲染模板为 `universal.html`
- HTML 注入 `STYLED_CARDS_JSON`、`SUBTITLES_JSON`、`EFFECT_CONFIG_JSON`、`SCENE_SEGMENTS_JSON`、`STYLE_JSON`
- 模板中存在 `styled-card-layer`、`focus-layer`、`gsap.min.js`、关键词/覆层/镜头推拉逻辑

因此科普指南之前“不像原项目”的主要原因不是单纯字体大小，而是路线层面缺失 `template3/universal/styledCards/quote`。

## 本轮代码修复

功能分支 `feature/ai_v6.3.3_vibevideo` 已做本地改造：

- `science_guide` 改为 `template-3 + quote`：
  - `render_template=universal.html`
  - `subtitle_mode=styled`
  - `cover_style=quote`
  - `render_quality=standard`
- 迁入原项目 `templates/universal.html` 到 H20 `hyperframes-postprocess/templates/universal.html`。
- `universal.html` 的 `--cjk-font` 改为使用 H20 注入的本地 CJK 字体栈，避免测试服中文字体方框回退。
- H20 adapter 新增 `styled_cards` 生成，并注入 `STYLED_CARDS_JSON`。
- `effect_config.explanation_overlays` 不再恒为空，至少根据现有 cues 生成保守的 `stat-card` 或 `quote-callout`，让 universal 模板具备触发镜头推拉/观点覆层的基础数据。
- `video_diary` 继续保持 `template4 + diary`。
- `minimal` 仍拒绝进入 HyperFrames postprocess，旧链路隔离不变。

## 验证结果

本地已通过：

```text
python -m unittest test.test_hyperframes_cli test.test_hyperframes_postprocess test.test_hyperframes_analysis test.test_hyperframes_upload_callback test.test_template_route -v
89 tests OK

python -m py_compile router/service/video_server2/hyperframes_cli.py scheduler/collect_scheduler.py router/service/video_server2/hyperframes_analysis.py
OK

node --check hyperframes-postprocess/index.js
OK
```

## 后续规则

- 科普指南后续优先按 `template=3 cover=quote` 对齐 golden。
- 视频日记按 `template=4 cover=diary` 对齐 golden。
- 不再把 `template7 + wanggan` 当作科普指南默认验收目标，除非产品重新确认需要该风格。
- 测试服发现 bug 必须先修回 `feature/ai_v6.3.3_vibevideo`，再干净集成到 `test`。
- 上测试服前必须按共享 runtime 记录检查 Node、HyperFrames CLI、PIL、rembg、ffmpeg，避免重复 2026-06-17 的环境坑。
