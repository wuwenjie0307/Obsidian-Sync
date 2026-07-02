---
date: "2026-07-02"
project: "joying-bot-server"
type: doc
tags: [doc, h20, vibevideo, hyperframes, subtitles, rollout]
aliases: ["H20 网感字幕分词开关", "HF_SUBTITLE_SEGMENTATION_MODE"]
---

# H20 网感字幕分词开关与测试服启用记录

## 图谱链接

- 项目: [[projects/joying-bot-server/00-项目概览|joying-bot-server]]
- 索引: [[projects/joying-bot-server/docs/00-docs-index|Docs 索引]]

## 背景

网感视频字幕断句之前多次调整，涉及口播字幕观感、数字单位保护、英文/API/Agent 这类词组保护，以及避免把词拆成单字。为了避免新分词逻辑污染原有完整链路，本次增加一个可回滚开关：默认继续走旧逻辑，测试服通过环境变量单独启用新逻辑。

## 当前代码状态

- 功能分支: `feature/voice-reference-audio-guard`
- 功能提交: `5b248102 feat: gate subtitle director segmentation`
- 合入 test 的临时合并提交: `20a8e234 merge feature/voice-reference-audio-guard into test`
- 涉及文件:
  - `hyperframes-postprocess/index.js`
  - `hyperframes-postprocess/reference_styled_subtitles.js`
  - `test/test_hyperframes_postprocess.py`

## 开关方式

优先级:

1. manifest/template config 中的 `hf_subtitle_segmentation_mode`
2. 环境变量 `HF_SUBTITLE_SEGMENTATION_MODE`
3. 默认值 `legacy`

可选值:

- `legacy`: 旧字幕分词逻辑，默认模式。
- `director`: 新字幕分词逻辑，用于测试新断句效果。

测试服当前已设置:

```text
HF_SUBTITLE_SEGMENTATION_MODE=director
```

回滚方式:

```text
HF_SUBTITLE_SEGMENTATION_MODE=legacy
```

或者删除该环境变量后重启 `ai_botserver_sch`，会回到默认旧逻辑。

## 影响范围

本次只改变“字幕如何切成每段显示”的逻辑。

不会改变:

- TTS 文案生成与音色克隆。
- ASR/错别字纠正。
- 口播 cue 的基础时间轴生成。
- 混剪素材匹配与覆盖逻辑。
- 字幕翻译逻辑。
- 封面生成逻辑。

会改变:

- 字幕分段边界。
- 长句如何拆成多个字幕 cue。
- 数字单位、英文词、Agent/API 这类 ASCII/业务词组附近的断句偏好。

注意: `director` 模式是测试变量。如果产品觉得新断句效果不稳定，可以直接回到 `legacy`，旧链路没有被删除。

## H20 测试服启用记录

- 当前 H20 release: `/data/project/test_ai_botserver.20260702174357`
- scheduler supervisor 配置: `/etc/supervisor.d/ai_botserver_sch.conf`
- 配置备份: `/etc/supervisor.d/ai_botserver_sch.conf.bak.20260702175117`
- 重启服务: `ai_botserver_sch`
- 重启后进程 cwd: `/data/project/test_ai_botserver.20260702174357`
- 已验证进程环境变量包含 `HF_SUBTITLE_SEGMENTATION_MODE=director`

测试服当时相关 HyperFrames 配置:

```text
HF_RENDER_BACKEND=docker
HF_DOCKER_IMAGE=h20-hyperframes-renderer:0.6.42-node22.22.2
HF_DOCKER_BINARY=/cm/local/apps/docker/current/bin/docker
HF_DOCKER_MOUNTS=/data:/data,/tmp:/tmp
HF_DOCKER_SHM_SIZE=2g
HF_RENDER_LOCK_TIMEOUT_SECONDS=60
HF_MAX_CONCURRENCY=7
```

敏感信息如密码、webhook、secret 不记录在 Obsidian。

## 验证记录

功能分支验证:

- `python -m unittest test.test_hyperframes_postprocess` 通过，59 tests OK。
- `node --check hyperframes-postprocess/index.js` 通过。
- `node --check hyperframes-postprocess/reference_styled_subtitles.js` 通过。
- `git diff --check` 通过。

合 test 前验证:

- 使用临时 test 合并工作区做无污染合并。
- 未把 test 合回功能分支。
- `origin/test` 是临时合并 HEAD 的祖先。
- `origin/feature/voice-reference-audio-guard` 已包含在临时合并 HEAD 中。

H20 设置环境变量前:

- 测试库无 `task_status IN (1,2)` 的处理中任务。

## 风险与排查口径

- 如果后续只发现字幕断句观感变化，优先检查 `subtitle_segmentation_mode` 是否为 `director`。
- 如果出现混剪素材不对齐、素材丢失、字幕错别字、TTS 读错符号，这些不是本开关直接负责的链路，应另查对应模块。
- 如果需要完全回退字幕断句变量，先把测试服改回 `legacy`，不需要回滚代码。

## 相关记录

- [[projects/joying-bot-server/docs/h20-model-timeout-isolation-retry-behavior-2026-07-02|H20 模型超时隔离与重试行为]]
- [[projects/joying-bot-server/docs/h20-video-task-stage-duration-fields-2026-07-01|H20 视频任务阶段耗时字段]]
