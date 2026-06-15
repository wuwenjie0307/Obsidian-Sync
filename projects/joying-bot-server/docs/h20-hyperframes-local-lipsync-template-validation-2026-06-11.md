---
date: 2026-06-11
updated: 2026-06-15
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
- 最近一次渲染耗时：约 `17777ms`（2026-06-15 记录时 `result_real.json`）
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

## 2026-06-15 开场中心标题与字幕错开修正

用户最新确认的视觉要求：封面标题（例如“南京低总价好房”）需要在视频一开始出现在画面中心，但不能被处理成视频上方标题，也不能和第一句字幕重叠；标题应短暂承担开场封面作用，随后退出，字幕再进入。

本次修正后的模板行为：

- `opening-cover-title` 使用全屏开场层，`.opening-cover-top { inset: 0; }`，`wanggan` 单行标题居中显示。
- 开场标题从 `0s` 开始，按 `openingVisibleDuration(duration)` 计算短暂显示时长。
- 字幕渲染 cue 通过 `cueForRender(cue, subtitleStartDelay)` 延后首屏展示，避免覆盖开场中心标题。
- 原始 `subtitle_timeline.json` 的 Whisper timing 不被改写；只调整成片 HTML 里的渲染 cue 开始时间。
- 对当前 `3.433333s` 本地样本，生成 HTML 中开场标题 `data-duration="0.612"`，第一句字幕 `data-start="0.6316"`。
- 废弃旧的 `DURATION - 0.6` 长驻/后退场逻辑，避免封面标题长期留在画面中心。

验证证据：

- 自动测试：`python -m unittest test.test_hyperframes_postprocess`，结果 `Ran 4 tests ... OK`。
- 真实渲染：`result_real.json` 为 `success: true`，最近一次 `render_ms: 17777`。
- 抽帧检查：`0.3s` 标题在中心且没有字幕；`0.8s` 标题已退出、第一句字幕出现；`1.5s` 只保留正常字幕，无中心封面标题残留。
- 抽帧文件：
  - `C:\Users\admin\Desktop\joyingbot-new-h20-hyperframes-dev\samples\h20_lipsync_sample\hyperframes_probe\out_real\frame_0_3_center_opening.png`
  - `C:\Users\admin\Desktop\joyingbot-new-h20-hyperframes-dev\samples\h20_lipsync_sample\hyperframes_probe\out_real\frame_0_8_after_opening.png`
  - `C:\Users\admin\Desktop\joyingbot-new-h20-hyperframes-dev\samples\h20_lipsync_sample\hyperframes_probe\out_real\frame_1_5_after_opening.png`

正式代码/测试位置：

- `C:\Users\admin\Desktop\joyingbot-new-h20-hyperframes-dev\hyperframes-postprocess\index.js`
- `C:\Users\admin\Desktop\joyingbot-new-h20-hyperframes-dev\test\test_hyperframes_postprocess.py`

注意：本次仍未合并到 `test`，未重启 H20 服务，未修改测试数据库字段。`samples/` 和临时 renderer wrapper 只用于本地验证，不应默认随正式功能提交。
## 环境注意

本地 HyperFrames 真实渲染曾遇到 Windows 环境问题：HyperFrames `0.6.42` 在预检时使用 `where ffmpeg`，当前 Codex/PowerShell 环境里存在 `PATH/Path` 重复以及不可访问的 WinGet FFmpeg 路径，导致误判 `FFmpeg not found`。

本次验证只在 `samples/h20_lipsync_sample/hyperframes_probe/` 下使用临时 renderer wrapper 和本地 FFmpeg runtime 规避环境问题；这不是正式后端代码路径，不应作为线上部署方案提交，除非后续专门产品化 Windows 本地验证流程。

## 当前状态

- 未合并到 `test`。
- 未重启 H20 服务。
- 未修改测试数据库字段。
- `samples/` 和 `tools/h20_lipsync_sample.py` 当前只作为本地验证材料，不建议随正式功能提交，除非后续明确要沉淀为工具。

## 2026-06-15 干净 31 秒样本与双层字幕结论

本次继续排查用户反馈的两个现象：

- 双层字幕：旧样本来自 `t_video_generate_task.id=1442 / task_id=1226 / job_id=1260` 的 `generate_video_url`，该 URL 是旧链路最终成片，底部已经烧录旧字幕；再进入 HyperFrames 后会叠加左上新字幕，因此出现双层字幕。
- 第一帧标题偏上：根因是 `hyperframes-postprocess/index.js` 中 `.opening-wanggan-title` 默认 `top: 16%`，长标题拆两行时没有走 `.is-single-line` 的居中规则。已改为默认 `top: 50%; transform: translateY(-50%);`，并新增长标题回归测试。

为验证输入源问题，2026-06-15 通过 H20 只读探测 `/tmp` 候选视频，找到干净样本：

- H20 原始候选：`/tmp/tmpc3z9ua5v.mp4`
- 本地原始样本：`C:\Users\admin\Desktop\joyingbot-new-h20-hyperframes-dev\samples\h20_lipsync_sample\clean_31s\tmpc3z9ua5v_clean_31s.mp4`
- 本地标准化输入：`C:\Users\admin\Desktop\joyingbot-new-h20-hyperframes-dev\samples\h20_lipsync_sample\clean_31s\tmpc3z9ua5v_clean_31s_916_30fps.mp4`
- HyperFrames manifest：`C:\Users\admin\Desktop\joyingbot-new-h20-hyperframes-dev\samples\h20_lipsync_sample\clean_31s\manifest_clean31_real.json`
- 渲染输出：`C:\Users\admin\Desktop\joyingbot-new-h20-hyperframes-dev\samples\h20_lipsync_sample\clean_31s\out_real\final.mp4`
- 带音频验收输出：`C:\Users\admin\Desktop\joyingbot-new-h20-hyperframes-dev\samples\h20_lipsync_sample\clean_31s\out_real\final_with_audio.mp4`

验证结果：

- `python -m unittest test.test_hyperframes_postprocess`：`Ran 5 tests ... OK`。
- 干净样本渲染成功：`result_clean31_real.json` 中 `success: true`，`render_ms: 98002`。
- `final_with_audio.mp4` 输出参数：`1080x1920`、`30fps`、约 `30.06s`，包含 `h264` 视频流和 `aac 48000Hz stereo` 音频流。
- 抽帧 `frame_0_3_clean31.png`：开场标题位于画面中心，不再偏到上方。
- 抽帧 `frame_1_0_clean31.png`：只剩一层左上 HyperFrames 字幕，底部无旧字幕，证明双层字幕来自旧链路最终成片输入，不是 HyperFrames 模板重复画字幕。
- HTML 检查：没有 `top: 16%`，没有 `开场卖点` / `中间决策点` / `opening hook` / `key rule` 等可见动作说明文本，`action-cue` 不再可见渲染 reason 文案。

注意事项：

- 本次仍未合并到 `test`，未重启 H20，未修改测试数据库字段。
- `samples/` 与 `tools/h20_lipsync_sample.py` 仍是本地验证材料，默认不随正式代码提交。
- 这次使用的 31 秒干净样本来自 H20 `/tmp` 临时文件，并非 task 1226 的同一个女主播最终成片；它用于验证“干净唇形输入进入 HyperFrames 后不会双层字幕”。后续正式链路应在 `router/service/video_server2/video_work.py` 的 `return_standardized_result=True` 分叉点取 `HeygemStandardizedVideoResult`，也就是标准化唇形视频、字幕前产物。
