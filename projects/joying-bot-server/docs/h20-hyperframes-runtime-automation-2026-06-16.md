---
date: 2026-06-16
project: joying-bot-server
type: doc
tags: [h20, hyperframes, runtime, deployment, node]
aliases: [H20 HyperFrames Runtime 自动化, 网感视频 Node Runtime 部署规则]
---

# H20 HyperFrames Runtime 自动化

## 结论

网感视频 HyperFrames 链路不应依赖每台机器手工安装或手工寻找 `node/npx`。当前项目采用共享 Node runtime + release 内 npm lock 依赖 + 部署脚本校验的方式：

- 共享 runtime 默认目录：`/data/project/hyperframes-runtime`
- release 内依赖目录：`hyperframes-postprocess`
- 每次 release 部署后执行：`bash scripts/ensure_hyperframes_runtime.sh`
- Python 渲染前 preflight 失败时明确报：`HYPERFRAMES_RUNTIME_NOT_READY`

## 运行时规则

- `hyperframes-postprocess/package.json` 固定 `hyperframes@0.6.42`。
- 不提交 `node_modules`。
- 不依赖全局 `npx hyperframes`。
- Node 默认接受 `22.x` 或 `24.x`，拒绝低版本和奇数 Current 版本。
- Python 默认优先级：
  1. `HYPERFRAMES_NODE_BINARY`
  2. `HYPERFRAMES_RUNTIME_HOME/current/bin/node`
  3. PATH 中的 `node`
- Node 后处理默认使用本地 `hyperframes-postprocess/node_modules/.bin/hyperframes`，保留 `HF_POSTPROCESS_RENDER_CMD` 覆盖口。
- 子进程 PATH 自动补入 Node runtime bin、本地 `.bin`、`/usr/local/bin`、`/usr/bin`、`/usr/sbin`、`/bin`。

## 部署变量

- `HYPERFRAMES_RUNTIME_HOME=/data/project/hyperframes-runtime`
- `HYPERFRAMES_NODE_TARBALL=/path/to/node-v22-or-v24-linux-x64.tar.xz`
- `HYPERFRAMES_NODE_BINARY=/abs/path/node`
- `HYPERFRAMES_POSTPROCESS_DIR=/data/project/test_ai_botserver/hyperframes-postprocess`
- `HF_POSTPROCESS_RENDER_CMD`：仅用于人工覆盖默认 renderer 命令。

## 实现记录

- 新增 `scripts/ensure_hyperframes_runtime.sh`，用于共享 runtime/离线 tar 包/系统 Node 检查，以及执行 `npm ci --omit=dev --no-audit --no-fund`。
- 新增项目文档 `docs/h20-hyperframes-runtime.md`。
- 修改 `router/service/video_server2/hyperframes_cli.py`，在渲染锁前做 runtime preflight。
- 修改 `hyperframes-postprocess/index.js`，默认调用本地 HyperFrames CLI，不再调用全局 `npx hyperframes`。

## 验证

- `python -m unittest test.test_hyperframes_cli test.test_hyperframes_postprocess test.test_hyperframes_analysis test.test_hyperframes_upload_callback test.test_template_route -v`：69 项通过。
- `python -m py_compile router/service/video_server2/hyperframes_cli.py scheduler/collect_scheduler.py`：通过。
- `node --check hyperframes-postprocess\index.js`：通过。
- `C:\Program Files\Git\bin\bash.exe -n scripts/ensure_hyperframes_runtime.sh`：通过。

## 图谱链接

- [[projects/joying-bot-server/00-项目概览|项目概览]]
- [[projects/joying-bot-server/docs/00-docs-index|参考文档索引]]
- [[projects/joying-bot-server/docs/h20-hyperframes-db-field-change-rules-2026-06-16|H20 HyperFrames 字段变更规则]]
- [[projects/joying-bot-server/docs/h20-hyperframes-prd-uncertainty-decisions-2026-06-08|H20 HyperFrames PRD 不确定项与决策记录]]
