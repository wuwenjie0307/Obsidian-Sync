---
date: "2026-06-18"
project: "joying-bot-server"
type: changelog
tags: [h20, hyperframes, vibevideo, font, postprocess]
aliases: ["H20 HyperFrames 本地 SourceHanSans 中文兜底字体"]
---

# H20 HyperFrames 本地 SourceHanSans 中文兜底字体 2026-06-18

## 图谱链接

- 项目: [[projects/joying-bot-server/00-项目概览|joying-bot-server]]
- 索引: [[projects/joying-bot-server/changelog/00-changelog-index|变更记录索引]]

## 改动类型

Bug fix / runtime visual stability。

## 改动内容

测试服生成的视频在第一轮字体修复后仍出现部分中文显示为方框或短横。排查结论是：`Smiley Sans Local` 与 `Ma Shan Zheng Local` 已经随 composition 复制并加载，但它们属于风格字体，不适合作为完整中文兜底字库；测试服 Linux 环境又没有可用的系统 CJK 字体，因此未覆盖的中文字形仍会渲染异常。

本轮修复在 H20 后处理目录新增随代码发布的完整中文兜底字体：

- `hyperframes-postprocess/assets/fonts/source-han-sans-sc/SourceHanSansSC-Regular-2.otf`

并调整 `hyperframes-postprocess/index.js`：

- `FONT_ASSETS` 增加 `Source Han Sans SC Local`，生成 composition 时复制到 `fonts/source-han-sans-sc/`。
- `@font-face` 支持每个字体单独声明 `format/weight/style`，`Smiley Sans Local` 保持 `900 oblique`。
- `--cjk-font` 改为优先使用 `Source Han Sans SC Local`，再接 `Smiley Sans Local`、`Ma Shan Zheng Local` 和系统字体。
- `science_guide` 与 `video_diary` 的 `titleFont/subtitleFont` 也改为优先使用 `Source Han Sans SC Local`，避免模板中 `var(--font)` 的正文层继续落到测试服不存在的系统字体。

## 影响范围

- 影响范围仅限 HyperFrames 网感后处理 composition 字体注入与资产复制。
- `science_guide` 仍保持 `template3 + quote`。
- `video_diary` 仍保持 `template4 + diary`。
- `minimal` 极简旧链路不进入 HyperFrames postprocess，不受本次字体修复影响。
- 不改数据库字段，不改 CRM/CSM 回调口径，不依赖测试服手工安装系统字体。

## 验证结果

本地已通过：

```text
python -m unittest test.test_hyperframes_postprocess test.test_hyperframes_cli test.test_hyperframes_analysis test.test_hyperframes_upload_callback test.test_template_route -v
89 tests OK

python -m py_compile router/service/video_server2/hyperframes_cli.py scheduler/collect_scheduler.py router/service/video_server2/hyperframes_analysis.py
OK

node --check hyperframes-postprocess/index.js
OK
```

新增/更新测试覆盖：

- `science_guide` composition HTML 必须引用 `SourceHanSansSC-Regular-2.otf`。
- `science_guide` composition 目录必须真实复制 `fonts/source-han-sans-sc/SourceHanSansSC-Regular-2.otf`。
- `video_diary` composition HTML 必须引用 `SourceHanSansSC-Regular-2.otf`。
- `--cjk-font` 与 `--font` 必须优先使用 `Source Han Sans SC Local`。
- 继续保留 `Smiley Sans Local`、`Ma Shan Zheng Local` 的字体声明与风格权重。

## 相关文件

- `hyperframes-postprocess/index.js`
- `hyperframes-postprocess/assets/fonts/source-han-sans-sc/SourceHanSansSC-Regular-2.otf`
- `test/test_hyperframes_postprocess.py`

## 相关记录

- [[projects/joying-bot-server/docs/h20-hyperframes-template3-quote-migration-2026-06-18|H20 网感视频 template3 quote 迁移决策 2026-06-18]]
- [[projects/joying-bot-server/bugs/h20-hyperframes-repeat-pitfalls-2026-06-17|H20 HyperFrames 反复踩坑记录 2026-06-17]]
