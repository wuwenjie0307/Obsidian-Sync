---
date: 2026-06-11
project: joying-bot-server
type: doc
tags: [doc, h20, hyperframes, wanggan, local-validation]
aliases: ["H20 HyperFrames 本地唇形样本模板验证 2026-06-11"]
---

# H20 HyperFrames 本地唇形样本模板验证 2026-06-11

## 图谱链接

- 项目: [[projects/joying-bot-server/00-项目概览|joying-bot-server]]
- 索引: [[projects/joying-bot-server/docs/00-docs-index|参考文档索引]]
- 相关 PRD/决策: [[projects/joying-bot-server/docs/h20-hyperframes-prd-uncertainty-decisions-2026-06-08|h20-hyperframes-prd-uncertainty-decisions-2026-06-08]]

## 背景

2026-06-11，为了避免直接影响测试环境，先不合并到 `test`，也不重启 H20 服务、不改测试库字段。验证方式改为：从 H20 找一个已经唇形处理过的视频，拉到本地，作为网感视频 HyperFrames 后处理链路的输入，做本地端到端验证。

## 样本来源

- H20 现成唇形产物：`/tmp/lip_sync_result.mp4`
- 原始参数：`576x1280`、`25fps`、`3.44s`
- 为适配新链路输入，只在 H20 上用 `ffmpeg` 做标准化，不跑模型：`/tmp/lip_sync_result_916_30fps.mp4`
- 标准化参数：`720x1280`、`30fps`、`3.433333s`
- 本地输入文件：`C:\Users\admin\Desktop\joyingbot-new-h20-hyperframes-dev\samples\h20_lipsync_sample\user4_1781149380944_9832222ca5439eea.mp4`
- 本地元数据：`C:\Users\admin\Desktop\joyingbot-new-h20-hyperframes-dev\samples\h20_lipsync_sample\existing_lipsync_local_meta.json`

## 使用模板

本地样本使用的是网感视频 V1 的 `science_guide` 路由模板：

- `templates_style_id`: `1`
- `template_id`: `science_guide`
- HyperFrames 内部模板名：`template-7 + wanggan`
- `cover_style`: `wanggan`
- `subtitle_mode`: `paired-corners`

对应文件：

- manifest: `C:\Users\admin\Desktop\joyingbot-new-h20-hyperframes-dev\samples\h20_lipsync_sample\hyperframes_probe\manifest_real.json`
- timeline: `C:\Users\admin\Desktop\joyingbot-new-h20-hyperframes-dev\samples\h20_lipsync_sample\hyperframes_probe\out_real\subtitle_timeline.json`

## 本地渲染结果

- 输出视频：`C:\Users\admin\Desktop\joyingbot-new-h20-hyperframes-dev\samples\h20_lipsync_sample\hyperframes_probe\out_real\final.mp4`
- 输出参数：`1080x1920`、`30fps`、`3.433333s`
- `result_real.json`: `success: true`
- 最近一次渲染耗时：约 `20245ms`
- 封面：`C:\Users\admin\Desktop\joyingbot-new-h20-hyperframes-dev\samples\h20_lipsync_sample\hyperframes_probe\out_real\cover.png`
- 字幕 timeline：`C:\Users\admin\Desktop\joyingbot-new-h20-hyperframes-dev\samples\h20_lipsync_sample\hyperframes_probe\out_real\subtitle_timeline.json`

## 小字问题与修复

现象：成片中间出现了“开场卖点 / 强调决策点”等小字。

根因：`hyperframes-postprocess/index.js` 的 `actionHtml()` 把结构化分析里的 `actions[].reason` 直接渲染进了 `.action-cue` DOM。`reason` 本来只是镜头动作解释，用于说明为什么某段触发 `push_in` 或 `zoom_in`，属于内部元数据，不应该进入成片。

修复：

- `action-cue` 不再写入 `reason` 文本。
- `action-cue` 改为不可见，只保留 `data-action-type`、`data-segment-index`、`data-start`、`data-duration` 等动画驱动字段。
- 脚本侧只传递 action 的 `segment_index/type/start/end`，不再把 `reason` 写进成片 HTML。
- 新增防回归测试，确保 `opening hook / key rule` 这类内部 reason 不进入 HTML。

相关代码：

- `C:\Users\admin\Desktop\joyingbot-new-h20-hyperframes-dev\hyperframes-postprocess\index.js`
- `C:\Users\admin\Desktop\joyingbot-new-h20-hyperframes-dev\test\test_hyperframes_postprocess.py`

## 验证结果

已完成本地验证：

- `python -m unittest test.test_hyperframes_postprocess`: `4 tests OK`
- `composition/index.html` 中未检出：`开场卖点`、`强调决策点`、`opening hook`、`key rule`
- `result_real.json`: `success: true`
- ffprobe 输出视频参数：`h264`、`1080x1920`、`30/1`、`3.433333s`
- 抽帧检查 `0.6s` 和 `1.5s`，原中间小字已消失，只剩正式标题与 Whisper 字幕。

## 环境注意

本地 HyperFrames 真实渲染曾遇到 Windows 环境问题：HyperFrames `0.6.42` 在预检时使用 `where ffmpeg`，当前 Codex/PowerShell 环境里存在 `PATH/Path` 重复以及不可访问的 WinGet FFmpeg 路径，导致误判 `FFmpeg not found`。

本次验证只在 `samples/h20_lipsync_sample/hyperframes_probe/` 下使用临时 renderer wrapper 和本地 FFmpeg runtime 规避环境问题；这不是正式后端代码路径，不应作为线上部署方案提交，除非后续专门产品化 Windows 本地验证流程。

## 当前状态

- 未合并到 `test`。
- 未重启 H20 服务。
- 未修改测试数据库字段。
- `samples/` 和 `tools/h20_lipsync_sample.py` 当前只作为本地验证材料，不建议随正式功能提交，除非后续明确要沉淀为工具。
