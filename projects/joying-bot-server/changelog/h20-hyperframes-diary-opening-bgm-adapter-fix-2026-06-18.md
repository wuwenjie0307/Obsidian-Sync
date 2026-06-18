---
date: "2026-06-18"
project: joying-bot-server
type: changelog
tags: [h20, hyperframes, video-diary, bgm, adapter, original-project-reuse]
aliases: [H20 HyperFrames 日记开场与 BGM adapter 修复]
---

# H20 HyperFrames 日记开场与 BGM adapter 修复

## 改动类型

- Bug fix / adapter 补齐。
- 不改数据库字段，不改 CRM/CSM 回调口径。
- 不修改 `minimal` 旧链路；只影响 `science_guide` / `video_diary` 网感 HyperFrames 分支。

## 问题背景

用户对比本地 `AIGCVideo_副本` 产物与 H20 测试服产物后指出两个问题：

1. `video_diary` 开头前两秒右上角日期为空，日期下方标题错误显示模板默认 `Day36`，而原项目目标效果应显示日期，并在下方显示复用封面标题/业务标题。
2. 生成后的视频没有使用 H5 上传/选择的 BGM；旧极简链路能使用 BGM，但网感链路没有声音背景。

## 原因

### 日记开场日期/标题

对照原项目：

- `AIGCVideo_副本/src/pipeline.js` 有 `resolveCoverDate()`，默认使用上海日期 `YYYY/MM/DD`，并把 `coverDate`、`coverTitle` 传入 render。
- `AIGCVideo_副本/templates/template4.html` 的 diary opening 使用 `coverDate` 作为右上角日期，使用 `coverTitle` 作为日期下方标题。
- `AIGCVideo_副本/scripts/cover_gen.py` 中 `Day 36` 是封面 day label 概念，不应该替代视频开场标题。

H20 adapter 漏点：

- `hyperframes-postprocess/index.js` 没有在 diary 缺省时生成 `coverDate`。
- `openingTitle` 之前错误地取 `coverDay || "Day 36"`，导致视频开场标题被封面 day label 覆盖。

### BGM

依据 apidoc 与代码：

- CRM 单条创建接口 `701 /crm/agent/pc/video/generateJobUserCreate` 请求体包含 `hot_video_audio_url`，这是 H5 上传/选择 BGM 后进入 H20 的字段。
- H20 同步逻辑会把 Task/Job 返回的 `hot_video_audio_url` 落到 `t_video_generate_task.hot_video_audio_url`。
- 旧极简链路 `video_work_Heygem_Whisper` 会用 `background_music_url=task_record.hot_video_audio_url` 下载并混音。
- HyperFrames Node 后处理已经支持 `manifest.bgm_path`，并且混音算法与原项目 `src/steps/7-bgm.js` 的核心策略一致：循环 BGM、淡入淡出、人声 sidechain ducking。

实际断点在 H20 网感分叉：scheduler 进入 `render_hyperframes_video` 前没有把 `task_record.hot_video_audio_url` 下载成本地文件，也没有把下载后的路径作为 `bgm_path` 写入 manifest，因此 Node 后处理认为没有 BGM，直接跳过混音。

## 改动内容

- `hyperframes-postprocess/index.js`
  - 增加 `resolveCoverDate(candidate)`，复用原项目口径：显式值优先，其次 `COVER_DATE`，否则上海日期 `YYYY/MM/DD`。
  - `video_diary` 的 `cover_date` 默认生成。
  - `opening_title` 改为 `coverTitle`，不再用 `coverDay` / `Day 36`。

- `scheduler/collect_scheduler.py`
  - 在网感分叉 `_prepare_hyperframes_video_task` 内读取 `task_record.hot_video_audio_url`。
  - 有值时复用 H20 旧链路下载工具 `_download_if_needed()` 下载成本地 BGM 文件。
  - 下载失败时返回 `BGM_DOWNLOAD_FAILED`，不静默降级为无 BGM。
  - 下载成功后把本地路径作为 `bgm_path` 传给 `render_hyperframes_video`，由 HyperFrames Node 后处理执行 BGM 混音。

- 测试更新
  - 覆盖 diary 开场标题不再使用 `Day 36`。
  - 覆盖 diary 缺省日期时生成 `YYYY/MM/DD`。
  - 覆盖 scheduler 会把显式 `hot_video_audio_url` 转成 HyperFrames `bgm_path`。
  - 保持 `minimal` 旧链路隔离，不把 `video_work_Heygem_Whisper` 或旧 BGM 后处理混入网感准备函数。

## 影响范围

- 影响：`templates_style_id=1 science_guide`、`templates_style_id=2 video_diary`。
- 不影响：`templates_style_id=3 minimal` 旧极简链路。
- `hot_video_audio_url` 为空：网感链路不加 BGM，符合既定规则。
- `hot_video_audio_url` 有值但下载失败：任务失败，失败码前缀 `BGM_DOWNLOAD_FAILED`。
- BGM 混音失败：仍由 Node 后处理返回 `H20_POSTPROCESS_BGM_*` / `HYPERFRAMES_RENDER_FAILED`，不静默吞掉。

## 验证结果

本地已通过：

```powershell
python -m unittest test.test_hyperframes_cli test.test_hyperframes_postprocess test.test_template_route -v
python -m py_compile scheduler/collect_scheduler.py router/service/video_server2/hyperframes_cli.py
node --check hyperframes-postprocess\index.js
```

结果：相关 66 个单测 OK，Python 编译 OK，Node 语法检查 OK。

## 相关文件

- `scheduler/collect_scheduler.py`
- `hyperframes-postprocess/index.js`
- `test/test_hyperframes_cli.py`
- `test/test_hyperframes_postprocess.py`
- `test/test_template_route.py`
- 原项目参考：`AIGCVideo_副本/src/pipeline.js`
- 原项目参考：`AIGCVideo_副本/templates/template4.html`
- 原项目参考：`AIGCVideo_副本/src/steps/7-bgm.js`

## 相关记录

- [[projects/joying-bot-server/docs/h20-hyperframes-prd-uncertainty-decisions-2026-06-08|H20 HyperFrames PRD 不确定项与最终决策]]
- [[projects/joying-bot-server/docs/h20-recent-video-task-output-params-2026-06-05|H20 最近视频任务参数与 BGM 记录]]
- [[projects/joying-bot-server/changelog/h20-hyperframes-cover-title-frame-source-fix-2026-06-18|H20 HyperFrames 封面标题与抽帧修复]]

## 图谱链接

- [[projects/joying-bot-server/00-项目概览|项目概览]]
- [[projects/joying-bot-server/changelog/00-changelog-index|更新日志索引]]
