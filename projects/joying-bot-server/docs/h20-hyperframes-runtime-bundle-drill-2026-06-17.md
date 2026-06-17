---
date: 2026-06-17
project: joying-bot-server
type: doc
tags: [h20, hyperframes, runtime, deployment, drill, vibevideo]
aliases: [H20 HyperFrames 固定运行包测试服隔离演练, 网感视频运行包演练]
---

# H20 HyperFrames 固定运行包测试服隔离演练记录

## 背景

本记录用于固化 H20 网感视频 HyperFrames 固定运行包方案的测试服隔离演练结果。

演练目的不是修复测试服故障，而是模拟正式服首次部署时可能出现的干净环境：没有系统 `node`、没有系统 `npm`、没有 `hyperframes-postprocess/node_modules`，只依赖代码中的脚本和固定运行包完成 runtime 准备。

## 演练结论

结论：固定运行包方案在 H20 测试服隔离目录完整跑通。

已验证：

- 研发/发布侧可以构建固定运行包。
- 运维/部署侧可以用固定运行包执行 `ensure_hyperframes_runtime.sh`。
- `ensure_hyperframes_runtime.sh` 首次执行成功。
- `ensure_hyperframes_runtime.sh` 二次执行成功，具备幂等性。
- 不需要系统全局 `node`、`npm`、`hyperframes`。
- 不需要在部署机临时执行默认 `npm ci`。

## 演练环境

- 时间：2026-06-17
- 机器：H20 测试服 `hgx19`
- live 软链：`/data/project/test_ai_botserver`
- live 实际目录：`/data/project/test_ai_botserver.20260617115413`
- 演练根目录：`/data/project/hyperframes-runtime-drill`

## 代码与脚本状态

`test` 分支已集成运行包脚本提交：

```text
e71b8d6d chore: package hyperframes runtime bundle flow
```

测试服 live 目录确认已有新版脚本：

```text
/data/project/test_ai_botserver/scripts/build_hyperframes_runtime_bundle.sh
/data/project/test_ai_botserver/scripts/ensure_hyperframes_runtime.sh
```

脚本版本特征：

```text
HYPERFRAMES_RUNTIME_BUNDLE
HYPERFRAMES_ALLOW_NPM_CI_FALLBACK
Node v22.22.2
HyperFrames 0.6.42
runtime ready
```

## 演练目录

构建侧目录：

```text
/data/project/hyperframes-runtime-drill/test_ai_botserver_clean
```

部署侧目录：

```text
/data/project/hyperframes-runtime-drill/test_ai_botserver_deploy
```

部署侧 runtime home：

```text
/data/project/hyperframes-runtime-drill/deploy-runtime-home
```

构建侧 runtime home：

```text
/data/project/hyperframes-runtime-drill/runtime-home
```

固定运行包输出目录：

```text
/data/project/hyperframes-runtime-drill/packages
```

## 前置检查结果

测试服已有 Node tar 包：

```text
/data/project/hyperframes-runtime/downloads/node-v22.22.2-linux-x64.tar.xz
```

测试服已有共享 Node runtime：

```text
/data/project/hyperframes-runtime/current -> /data/project/hyperframes-runtime/node-v22.22.2-linux-x64
/data/project/hyperframes-runtime/current/bin/node -v -> v22.22.2
```

测试服 shell 中没有系统全局 Node/npm：

```text
command -v node -> empty
command -v npm -> empty
```

演练目录初始状态符合正式服首次部署模拟：

```text
/data/project/hyperframes-runtime-drill/test_ai_botserver_clean/hyperframes-postprocess/node_modules 不存在
```

## 构建固定运行包

构建命令口径：

```bash
DRILL_ROOT=/data/project/hyperframes-runtime-drill
DRILL_DIR=$DRILL_ROOT/test_ai_botserver_clean
DRILL_RUNTIME_HOME=$DRILL_ROOT/runtime-home
NODE_TARBALL=/data/project/hyperframes-runtime/downloads/node-v22.22.2-linux-x64.tar.xz

cd "$DRILL_DIR"

HYPERFRAMES_RUNTIME_HOME="$DRILL_RUNTIME_HOME" \
HYPERFRAMES_NODE_TARBALL="$NODE_TARBALL" \
HYPERFRAMES_RUNTIME_BUNDLE_OUTPUT_DIR="$DRILL_ROOT/packages" \
bash scripts/build_hyperframes_runtime_bundle.sh
```

构建结果：

```text
[hyperframes-runtime-bundle] installed Node runtime from HYPERFRAMES_NODE_TARBALL: /data/project/hyperframes-runtime-drill/runtime-home/node-v22.22.2-linux-x64
npm warn deprecated node-domexception@1.0.0: Use your platform's native DOMException instead
added 170 packages in 3s
[hyperframes-runtime-bundle] hyperframes=0.6.42 path=/data/project/hyperframes-runtime-drill/test_ai_botserver_clean/hyperframes-postprocess/node_modules/.bin/hyperframes
[hyperframes-runtime-bundle] node=v22.22.2 path=/data/project/hyperframes-runtime-drill/runtime-home/current/bin/node
[hyperframes-runtime-bundle] npm=10.9.7 path=/data/project/hyperframes-runtime-drill/runtime-home/current/bin/npm
[hyperframes-runtime-bundle] bundle=/data/project/hyperframes-runtime-drill/packages/h20-hyperframes-runtime-node-v22.22.2-hf-0.6.42-linux-x64.tar.gz
[hyperframes-runtime-bundle] runtime bundle ready
```

固定运行包：

```text
/data/project/hyperframes-runtime-drill/packages/h20-hyperframes-runtime-node-v22.22.2-hf-0.6.42-linux-x64.tar.gz
```

包大小：

```text
124M
```

包内结构前缀确认：

```text
runtime/
runtime/node
runtime/node_modules/
```

## 使用固定运行包部署

部署侧命令口径：

```bash
DRILL_ROOT=/data/project/hyperframes-runtime-drill
SOURCE_DIR=$DRILL_ROOT/test_ai_botserver_clean
DEPLOY_DIR=$DRILL_ROOT/test_ai_botserver_deploy
DEPLOY_RUNTIME_HOME=$DRILL_ROOT/deploy-runtime-home
RUNTIME_BUNDLE=$DRILL_ROOT/packages/h20-hyperframes-runtime-node-v22.22.2-hf-0.6.42-linux-x64.tar.gz

cp -aL "$SOURCE_DIR" "$DEPLOY_DIR"
rm -rf "$DEPLOY_DIR/hyperframes-postprocess/node_modules"
rm -rf "$DEPLOY_RUNTIME_HOME"

cd "$DEPLOY_DIR"

HYPERFRAMES_RUNTIME_HOME="$DEPLOY_RUNTIME_HOME" \
HYPERFRAMES_RUNTIME_BUNDLE="$RUNTIME_BUNDLE" \
bash scripts/ensure_hyperframes_runtime.sh
```

首次部署结果：

```text
[hyperframes-runtime] installed Node runtime from bundle: /data/project/hyperframes-runtime-drill/deploy-runtime-home/node-v22.22.2-linux-x64
[hyperframes-runtime] installed node_modules from runtime bundle into /data/project/hyperframes-runtime-drill/test_ai_botserver_deploy/hyperframes-postprocess/node_modules
[hyperframes-runtime] runtime bundle installed: /data/project/hyperframes-runtime-drill/packages/h20-hyperframes-runtime-node-v22.22.2-hf-0.6.42-linux-x64.tar.gz
[hyperframes-runtime] node=v22.22.2 path=/data/project/hyperframes-runtime-drill/deploy-runtime-home/current/bin/node
[hyperframes-runtime] npm=10.9.7 path=/data/project/hyperframes-runtime-drill/deploy-runtime-home/current/bin/npm
[hyperframes-runtime] ffmpeg=/usr/sbin/ffmpeg
[hyperframes-runtime] hyperframes=0.6.42 path=/data/project/hyperframes-runtime-drill/test_ai_botserver_deploy/hyperframes-postprocess/node_modules/.bin/hyperframes
[hyperframes-runtime] runtime ready
```

## 二次执行幂等性验证

设置 runtime PATH 后手工确认：

```bash
export PATH="$DEPLOY_RUNTIME_HOME/current/bin:$DEPLOY_DIR/hyperframes-postprocess/node_modules/.bin:/usr/local/bin:/usr/bin:/usr/sbin:/bin:$PATH"
```

手工版本检查结果：

```text
command -v node -> /data/project/hyperframes-runtime-drill/deploy-runtime-home/current/bin/node
node -v -> v22.22.2
command -v npm -> /data/project/hyperframes-runtime-drill/deploy-runtime-home/current/bin/npm
npm -v -> 10.9.7
command -v hyperframes -> /data/project/hyperframes-runtime-drill/test_ai_botserver_deploy/hyperframes-postprocess/node_modules/.bin/hyperframes
hyperframes --version -> 0.6.42
```

二次执行 `ensure_hyperframes_runtime.sh` 结果：

```text
[hyperframes-runtime] reusing existing Node runtime: /data/project/hyperframes-runtime-drill/deploy-runtime-home/node-v22.22.2-linux-x64
[hyperframes-runtime] installed node_modules from runtime bundle into /data/project/hyperframes-runtime-drill/test_ai_botserver_deploy/hyperframes-postprocess/node_modules
[hyperframes-runtime] runtime bundle installed: /data/project/hyperframes-runtime-drill/packages/h20-hyperframes-runtime-node-v22.22.2-hf-0.6.42-linux-x64.tar.gz
[hyperframes-runtime] node=v22.22.2 path=/data/project/hyperframes-runtime-drill/deploy-runtime-home/current/bin/node
[hyperframes-runtime] npm=10.9.7 path=/data/project/hyperframes-runtime-drill/deploy-runtime-home/current/bin/npm
[hyperframes-runtime] ffmpeg=/usr/sbin/ffmpeg
[hyperframes-runtime] hyperframes=0.6.42 path=/data/project/hyperframes-runtime-drill/test_ai_botserver_deploy/hyperframes-postprocess/node_modules/.bin/hyperframes
[hyperframes-runtime] runtime ready
```

## 重要发现

手工直接执行 `npm` 或 `hyperframes` 时，如果当前 shell 的 `PATH` 没有包含 runtime bin，会出现：

```text
/usr/bin/env: 'node': No such file or directory
```

原因：`npm` 和 `hyperframes` 这类脚本内部通常使用：

```bash
#!/usr/bin/env node
```

它们会从 `PATH` 中查找 `node`。

这不是部署脚本失败。`ensure_hyperframes_runtime.sh` 自身会自动设置：

```text
Node runtime bin
hyperframes-postprocess/node_modules/.bin
/usr/local/bin
/usr/bin
/usr/sbin
/bin
```

因此运维正常只需执行 `ensure_hyperframes_runtime.sh`，不需要手工配置 PATH。只有人工调试 `npm` 或 `hyperframes` 时才需要先 export PATH。

## 运维交付口径

正式部署建议：

1. 研发/发布侧在 Linux x64 环境构建一次固定运行包。
2. 固定运行包不要提交 GitLab。
3. 运维把包放到：

```text
/data/project/hyperframes-runtime/packages/h20-hyperframes-runtime-node-v22.22.2-hf-0.6.42-linux-x64.tar.gz
```

4. 运维在当前 release 目录执行：

```bash
cd /data/project/test_ai_botserver

HYPERFRAMES_RUNTIME_BUNDLE=/data/project/hyperframes-runtime/packages/h20-hyperframes-runtime-node-v22.22.2-hf-0.6.42-linux-x64.tar.gz \
  bash scripts/ensure_hyperframes_runtime.sh
```

5. 看到以下输出才重启服务：

```text
node=v22.22.2
npm=10.9.7
hyperframes=0.6.42
runtime ready
```

## 不变边界

本次演练只验证 HyperFrames runtime 部署方案，不改变：

- 数据库字段。
- CRM/CSM 回调口径。
- 模板业务逻辑。
- `minimal` 旧链路。
- 运行包不提交 GitLab 的规则。

## 图谱链接

- [[projects/joying-bot-server/00-项目概览|项目概览]]
- [[projects/joying-bot-server/docs/00-docs-index|参考文档索引]]
- [[projects/joying-bot-server/docs/h20-hyperframes-runtime-automation-2026-06-16|h20-hyperframes-runtime-automation-2026-06-16]]
- [[projects/joying-bot-server/docs/h20-hyperframes-test-merge-rules-2026-06-17|h20-hyperframes-test-merge-rules-2026-06-17]]
