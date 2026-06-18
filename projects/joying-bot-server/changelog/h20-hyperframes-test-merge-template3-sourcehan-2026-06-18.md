---
date: "2026-06-18"
project: "joying-bot-server"
type: changelog
tags: [h20, hyperframes, vibevideo, test-merge, deployment]
aliases: ["H20 HyperFrames template3 quote 与 SourceHan 字体合入 test"]
---

# H20 HyperFrames template3 quote 与 SourceHan 字体合入 test 2026-06-18

## 图谱链接

- 项目: [[projects/joying-bot-server/00-项目概览|joying-bot-server]]
- 索引: [[projects/joying-bot-server/changelog/00-changelog-index|变更记录索引]]

## 改动类型

Test branch integration。

## 改动内容

按安全集成规则，没有将整个 `feature/ai_v6.3.3_vibevideo` 直接 merge 到 `test`，而是从最新 `origin/test` 建立 test-side 集成分支：

- `merge-check/ai_v6.3.3_vibevideo-template3-sourcehan-to-test`

并 cherry-pick 两个必要提交：

- `3b92da19 fix: route science guide to template3 quote`
- `453175ef fix: bundle source han cjk fallback for hyperframes`

随后 fast-forward 更新远端 `test`：

- `origin/test` 从 `9f2f3ebd` 更新到 `453175ef`

## 影响范围

本次合入只涉及：

- `hyperframes-postprocess/index.js`
- `hyperframes-postprocess/templates/universal.html`
- `hyperframes-postprocess/assets/fonts/source-han-sans-sc/SourceHanSansSC-Regular-2.otf`
- `test/test_hyperframes_postprocess.py`

关键行为：

- `science_guide` 改为对齐 golden 的 `template=3 + cover=quote`，使用 `universal.html`。
- `video_diary` 保持 `template=4 + cover=diary`。
- HyperFrames 后处理随代码发布完整中文兜底字体 `Source Han Sans SC Local`，避免测试服缺系统 CJK 字体导致中文字幕方框。
- `minimal` 极简旧链路不进入 HyperFrames postprocess，不受本次合入影响。
- 不改数据库字段，不改 CRM/CSM 回调口径。

## 验证结果

合入 `test` 前，在 test-side 集成分支重新验证通过：

```text
python -m unittest test.test_hyperframes_postprocess test.test_hyperframes_cli test.test_hyperframes_analysis test.test_hyperframes_upload_callback test.test_template_route -v
89 tests OK

python -m py_compile router/service/video_server2/hyperframes_cli.py scheduler/collect_scheduler.py router/service/video_server2/hyperframes_analysis.py
OK

node --check hyperframes-postprocess/index.js
OK
```

远端确认：

```text
origin/test HEAD = 453175ef fix: bundle source han cjk fallback for hyperframes
```

## 后续动作

- 测试服自动拉取后，需要确认实际 release 目录包含 `universal.html` 与 `SourceHanSansSC-Regular-2.otf`。
- 按 H20 重启流程重启 `8100/8017/18017`。
- 提交 `science_guide`、`video_diary`、`minimal` 各一条验收：
  - `science_guide` 应走 `template3 + quote`。
  - `video_diary` 字体不应再出现中文方框。
  - `minimal` 旧链路不受影响。

## 相关记录

- [[projects/joying-bot-server/docs/h20-hyperframes-template3-quote-migration-2026-06-18|H20 网感视频 template3 quote 迁移决策 2026-06-18]]
- [[projects/joying-bot-server/changelog/h20-hyperframes-local-source-han-font-fallback-2026-06-18|H20 HyperFrames 本地 SourceHanSans 中文兜底字体 2026-06-18]]
