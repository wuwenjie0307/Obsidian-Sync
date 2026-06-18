---
date: 2026-06-18
project: joying-bot-server
type: changelog
tags: [changelog, h20, hyperframes, cover, template-reuse]
aliases: [H20 HyperFrames 封面标题与抽帧源修复]
---

# H20 HyperFrames 封面标题与抽帧源修复

## 改动类型

Bug fix / 原项目逻辑对齐。

## 改动内容

- 修复网感视频封面标题被结构化分析中的无效标题污染的问题。
  - 现场证据：H20 最新成功产物的 `hf_cover` 已经进入视频首帧，但封面上缺少大标题；截图中只出现类似短横杠的小元素。
  - 代码证据：`hyperframes-postprocess/index.js` 原先使用 `manifest.cover_title || analysis.cover_title || script_text`，如果上游 analysis 给出 `"-"` 这类纯标点标题，就会进入封面脚本，导致封面大标题为空白感。
  - 修复：新增 meaningful title 过滤，只接受包含 Unicode 字母或数字的标题；优先使用 manifest/business title，再用 analysis title，最后才用脚本文案片段。
- 修复封面抽帧源与原项目不一致的问题。
  - 原项目 `AIGCVideo_副本/src/steps/6-cover.js` 的 `generateCover(videoPath, ...)` 是从原始输入视频抽封面帧，再叠加封面文字并 prepend 到最终视频。
  - H20 当前逻辑曾从渲染后的 `final.mp4` 抽 `cover_frame.png`，这会把已经处理过的开头再作为封面基底，偏离原项目。
  - 修复：H20 postprocess 生成 cover 时优先从 `manifest.lip_sync_video_path` 抽帧，只有缺失时才 fallback 到 `final.mp4`。

## 影响范围

- 仅影响 `science_guide` / `video_diary` 网感后处理封面标题和封面抽帧源。
- `minimal` 旧链路不进入 HyperFrames postprocess，本次不应受影响。
- 不改数据库字段，不改 CRM/CSM 回调口径，不改测试服专属逻辑。

## 验证结果

本地验证通过：

```powershell
python -m unittest test.test_hyperframes_cli test.test_hyperframes_postprocess test.test_hyperframes_analysis test.test_hyperframes_upload_callback test.test_template_route -v
# Ran 91 tests, OK

python -m py_compile router/service/video_server2/hyperframes_cli.py scheduler/collect_scheduler.py router/service/video_server2/hyperframes_analysis.py
# exit 0

node --check hyperframes-postprocess/index.js
# exit 0

git diff --check
# exit 0，仅有 Windows LF/CRLF 提示
```

新增回归测试：

- `analysis.cover_title="-"` 时回退到 `manifest.cover_title`，封面脚本入参不再使用 `-`。
- 启用封面抽帧时，ffmpeg 抽帧输入必须是 `manifest.lip_sync_video_path`，不是 `out/final.mp4`。

## 相关文件

- `hyperframes-postprocess/index.js`
- `test/test_hyperframes_postprocess.py`
- 原项目参考：`AIGCVideo_副本/src/steps/6-cover.js`
- 原项目参考：`AIGCVideo_副本/scripts/cover_gen.py`

## 相关记录

- [[projects/joying-bot-server/changelog/h20-hyperframes-test-merge-template3-sourcehan-2026-06-18|h20-hyperframes-test-merge-template3-sourcehan-2026-06-18]]
- [[projects/joying-bot-server/changelog/h20-hyperframes-local-source-han-font-fallback-2026-06-18|h20-hyperframes-local-source-han-font-fallback-2026-06-18]]
- [[projects/joying-bot-server/docs/h20-hyperframes-template3-quote-migration-2026-06-18|h20-hyperframes-template3-quote-migration-2026-06-18]]

## 图谱链接

- [[projects/joying-bot-server/00-项目概览|项目概览]]
- [[projects/joying-bot-server/changelog/00-changelog-index|更新日志索引]]
