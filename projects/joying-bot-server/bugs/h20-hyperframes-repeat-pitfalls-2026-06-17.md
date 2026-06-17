---
date: "2026-06-17"
project: "joying-bot-server"
type: bug
status: fixed
severity: high
tags: [bug, h20, hyperframes, runtime, llm, repeat-pitfall]
aliases: ["H20 HyperFrames 重复踩坑复盘"]
---

# H20 HyperFrames 重复踩坑复盘 2026-06-17

## 图谱链接

- 项目: [[projects/joying-bot-server/00-项目概览|joying-bot-server]]
- 索引: [[projects/joying-bot-server/bugs/00-bugs-index|Bug 记录索引]]
- 运行文档: [[projects/joying-bot-server/docs/h20-hyperframes-runtime-automation-2026-06-16|H20 HyperFrames Runtime 自动化]]
- 运行包演练: [[projects/joying-bot-server/docs/h20-hyperframes-runtime-bundle-drill-2026-06-17|H20 HyperFrames Runtime Bundle 演练]]

## 问题描述

2026-06-17 测试服验证网感视频时，连续出现两个本应按已有记录快速定位的问题：

1. `HYPERFRAMES_RUNTIME_NOT_READY: local HyperFrames CLI missing`
2. `STRUCTURED_ANALYSIS_FAILED: invalid LLM analysis JSON: response is not a JSON object`

这两类问题都不是第一次出现。处理时一开始没有严格按 Obsidian 已记录的排障步骤执行，导致重复消耗时间，也让用户明确指出“昨天已经修过/记录过”。

## 复现步骤

1. 将网感视频代码合入 `test` 并部署到 H20 新 release：`/data/project/test_ai_botserver.20260617165824`。
2. 提交 `video_diary` 任务。
3. 任务 `1473` 失败：当前 release 缺 `hyperframes-postprocess/node_modules/.bin/hyperframes`。
4. 手动补齐 runtime 后再次提交任务。
5. 任务 `1474`、`1475` 失败：结构化分析阶段 LLM 返回被解析为非 JSON object，且失败时未保留 raw LLM 响应。

## 期望行为

- 每次新 release 部署后，必须先按当前 release 目录执行 runtime 检查，确认本地 HyperFrames CLI 存在后再提交任务。
- 遇到 `STRUCTURED_ANALYSIS_FAILED` 时，先查 Obsidian 和现场产物，不要只凭昨天的 `fallback_flags=false` 记忆判断。
- 结构化分析失败必须保留 `analysis_input.json` 和 `llm_analysis_raw.txt`，让下一次能看到原始 LLM 返回。

## 实际行为

- 一开始只确认了共享 Node runtime 存在，但没有第一时间确认当前物理 release 目录下的 `.bin/hyperframes`。
- 忽略了 Obsidian 中已经写明的规则：服务进程 CWD 对应的物理 release 目录必须有本地 CLI。
- 对结构化分析错误，一开始把它和昨天的 `fallback_flags=false` 混在一起；实际本次错误发生在更外层：LLM 响应整体不是 object。
- 失败目录 `tmp/h20_hyperframes/1258`、`1259` 只有 `whisper_timeline.json`，没有 LLM raw 证据。

## 原因

### 坑 1：新 release 不继承旧 release 的 node_modules

昨晚跑通的是旧 release：

```text
/data/project/test_ai_botserver.20260616213821
```

今天测试服进程跑的是新 release：

```text
/data/project/test_ai_botserver.20260617165824
```

`node_modules` 不在 Git 中，也不会天然从旧 release 带到新 release。新 release 里即使有 `package.json` / `package-lock.json`，如果没有执行 runtime 准备，也会缺：

```text
hyperframes-postprocess/node_modules/.bin/hyperframes
```

### 坑 2：结构化分析错误不能只记 fallback_flags

昨天修过的是：

```text
fallback_flags=false/null -> {}
```

本次失败是：

```text
invalid LLM analysis JSON: response is not a JSON object
```

这是外层 payload 类型问题，可能是 LLM 返回单对象数组、JSON 字符串包 JSON、空值或其他非 object。不能只看到 `STRUCTURED_ANALYSIS_FAILED` 就以为是同一个 `fallback_flags` 问题。

### 坑 3：失败时没有 raw 证据

旧代码只有成功后才写 `hyperframes_analysis.json`。如果 parse 阶段失败，就不会落任何分析阶段调试文件，现场只能看到泛化错误，无法判断 LLM 原始响应到底是什么。

## 解决方案

### 已执行的现场修复

在当前 H20 release：

```text
/data/project/test_ai_botserver.20260617165824
```

补齐了本地 HyperFrames CLI，验证结果：

```text
CLI_OK
hyperframes --version -> 0.6.42
```

### 已提交的代码修复

功能分支：`feature/ai_v6.3.3_vibevideo`

提交：

```text
7bf90b4c fix: stabilize hyperframes llm analysis parsing
```

修复内容：

- `parse_llm_analysis_json` 允许单对象数组 `[ {...} ]` 归一化为 object。
- 允许 JSON 字符串包 JSON 时二次解析。
- 多对象数组仍拒绝，避免吞脏结构。
- `build_hyperframes_analysis` 在调用 LLM 后立即写：
  - `analysis_input.json`
  - `llm_analysis_raw.txt`
- 保留已有 `fallback_flags=false/null -> {}` 行为。

测试集成分支：

```text
integrate/ai_v6.3.3_vibevideo_analysis_fix
```

已从最新 `origin/test` cherry-pick 该修复，未整条合并 feature 历史。

## 优化点

以后遇到这两类错误，必须按下面顺序做，不允许跳步：

1. 先查 Obsidian：搜错误关键字、任务 id、`hyperframes-runtime`、`STRUCTURED_ANALYSIS_FAILED`。
2. 查 live 进程 CWD：`8100/8017/18017` 必须指向当前 release。
3. 对当前物理 release 执行：

```bash
test -x hyperframes-postprocess/node_modules/.bin/hyperframes && hyperframes-postprocess/node_modules/.bin/hyperframes --version
```

4. 如果报 `local HyperFrames CLI missing`，不要讨论业务逻辑，先在当前 release 目录跑 runtime 准备。
5. 如果报 `STRUCTURED_ANALYSIS_FAILED`，先查任务目录：

```text
tmp/h20_hyperframes/{task_id}/analysis_input.json
tmp/h20_hyperframes/{task_id}/llm_analysis_raw.txt
tmp/h20_hyperframes/{task_id}/whisper_timeline.json
```

6. 不要只看最终 `fail_reason`；同时看 `logs/run.log`、DB artifact 字段、任务目录文件。
7. 测试服发现 bug，必须先修回 `feature/ai_v6.3.3_vibevideo`，再 cherry-pick/集成到 `test`。

## 验证结果

本地功能分支和 test 集成分支均已通过：

```text
python -m unittest test.test_hyperframes_analysis test.test_hyperframes_cli test.test_hyperframes_postprocess -v
54 tests OK

python -m py_compile router/service/video_server2/hyperframes_analysis.py router/service/video_server2/hyperframes_cli.py scheduler/collect_scheduler.py
OK
```

## 相关文件

- `router/service/video_server2/hyperframes_analysis.py`
- `test/test_hyperframes_analysis.py`
- `scripts/ensure_hyperframes_runtime.sh`
- `hyperframes-postprocess/package.json`
- `hyperframes-postprocess/package-lock.json`

## 相关记录

- [[projects/joying-bot-server/docs/h20-hyperframes-runtime-automation-2026-06-16|H20 HyperFrames Runtime 自动化]]
- [[projects/joying-bot-server/docs/h20-hyperframes-runtime-bundle-drill-2026-06-17|H20 HyperFrames Runtime Bundle 演练]]
- [[projects/joying-bot-server/docs/h20-hyperframes-test-merge-rules-2026-06-17|H20 HyperFrames test 合并规则]]
