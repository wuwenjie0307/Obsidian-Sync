---
date: "2026-06-17"
project: "joying-bot-server"
type: changelog
tags: [changelog, h20, hyperframes, runtime, test]
aliases: ["h20-hyperframes-shared-runtime-deps-2026-06-17"]
---

# h20-hyperframes-shared-runtime-deps-2026-06-17

## 图谱链接

- 项目: [[projects/joying-bot-server/00-项目概览|joying-bot-server]]
- 索引: [[projects/joying-bot-server/changelog/00-changelog-index|更新日志索引]]

## 改动类型

- [ ] 新功能
- [x] Bug 修复
- [x] 重构
- [x] 配置变更
- [x] 文档

## 改动内容

- 将 H20 HyperFrames 的 npm 依赖从 release-local `hyperframes-postprocess/node_modules` 调整为共享运行环境优先。
- 默认共享依赖路径为 `/data/project/hyperframes-runtime/deps/hyperframes-0.6.42/node_modules`。
- Python preflight 优先检查共享 HyperFrames CLI；release 本地 `node_modules` 只作为开发/兼容兜底。
- Node 后处理默认渲染优先使用共享 deps，避免每次 timestamp release 都要求重新铺 `node_modules`。
- `scripts/ensure_hyperframes_runtime.sh` 改为：
  - 已有共享 Node + 共享 HyperFrames deps 且版本正确时直接复用。
  - 首次初始化或升级时才从 runtime bundle 解出依赖到共享 deps。
  - 不再把 bundle 里的 `node_modules` 安装到当前 release 目录。
- 更新 `docs/h20-hyperframes-runtime.md`，明确当前 release 不再安装 release-local `node_modules`。

## 原因

- H20 测试服现有逻辑是代码 release 目录随时间戳变化，但 Python 依赖、ffmpeg 等运行环境长期复用。
- 之前 HyperFrames Node/npm 依赖绑在每个 release 目录下，导致新 release 目录没有 `node_modules/.bin/hyperframes` 时，任务运行到一半才失败。
- 用户确认这个模式不符合测试服现有依赖管理习惯，维护成本高，因此改为共享 Node/runtime deps，与现有 conda Python 环境管理方式保持一致。

## 影响范围

- 影响网感视频 HyperFrames 后处理链路的运行时依赖查找。
- 不改数据库字段。
- 不改 CRM/CSM 回调口径。
- 不影响 `minimal` 旧链路隔离规则。
- 测试服后续 release 只需要确认共享 runtime 可用，不应该每次手工安装 npm 依赖。

## 验证结果

本地功能分支验证：

- `python -m unittest test.test_hyperframes_cli test.test_hyperframes_postprocess test.test_hyperframes_analysis test.test_hyperframes_upload_callback test.test_template_route -v`：89 tests OK。
- `python -m py_compile router/service/video_server2/hyperframes_cli.py scheduler/collect_scheduler.py`：通过。
- `node --check hyperframes-postprocess/index.js`：通过。
- `bash -n scripts/ensure_hyperframes_runtime.sh`：通过。
- `bash -n scripts/build_hyperframes_runtime_bundle.sh`：通过。

目标侧 test 集成验证：

- 未直接把整条 `feature/ai_v6.3.3_vibevideo` 合入 `test`，因为 feature 相对 test 有大量历史差异，直接合并有污染风险。
- 在目标侧临时 worktree 基于 `origin/test` cherry-pick 最新共享 runtime 提交，无冲突。
- 目标侧同样跑过上述相关测试和语法检查，通过后推送 `origin/test`。

测试服验证：

- `origin/test` 更新到 `150a4191 fix: use shared hyperframes runtime deps`。
- H20 release 已部署到 `/data/project/test_ai_botserver.20260617223033`。
- release 中确认存在代码标记 `sharedHyperframesNodeModules`。
- `scripts/ensure_hyperframes_runtime.sh` 在测试服输出 `runtime ready`。
- 共享 HyperFrames CLI 路径确认：`/data/project/hyperframes-runtime/deps/hyperframes-0.6.42/node_modules/.bin/hyperframes`。
- 已精确重启 stale 的 `8100`，重启前 `8100` 仍在旧 release `20260617211633`，重启后 `8100/8017/18017` 全部运行在 `20260617223033`。
- 健康检查：`8100/status/check` 和 `8017/status/check` 均返回 `{"status":"ok"}`。

## 相关文件

- `router/service/video_server2/hyperframes_cli.py`
- `hyperframes-postprocess/index.js`
- `scripts/ensure_hyperframes_runtime.sh`
- `docs/h20-hyperframes-runtime.md`
- `test/test_hyperframes_cli.py`
- `test/test_hyperframes_postprocess.py`

## 相关记录

- [[projects/joying-bot-server/docs/h20-hyperframes-runtime-automation-2026-06-16|h20-hyperframes-runtime-automation-2026-06-16]]
- [[projects/joying-bot-server/docs/h20-hyperframes-runtime-bundle-drill-2026-06-17|h20-hyperframes-runtime-bundle-drill-2026-06-17]]
- [[projects/joying-bot-server/docs/h20-hyperframes-test-merge-rules-2026-06-17|h20-hyperframes-test-merge-rules-2026-06-17]]
- [[projects/joying-bot-server/changelog/h20-hyperframes-runtime-automation-fix-2026-06-17|h20-hyperframes-runtime-automation-fix-2026-06-17]]

## 相关 Commit

- 功能分支: `8a770f71 fix: use shared hyperframes runtime deps`
- test 侧集成: `150a4191 fix: use shared hyperframes runtime deps`
