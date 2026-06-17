---
date: 2026-06-17
project: joying-bot-server
type: changelog
tags: [h20, hyperframes, runtime, deployment, node, test-release]
aliases: [H20 HyperFrames Runtime 自动化修复, 网感视频 Node Runtime 收敛]
---

# H20 HyperFrames Runtime 自动化修复（2026-06-17）

## 改动类型

运行时依赖收敛 / 部署脚本 / 渲染前置检查 / 测试环境验收准备。

## 改动内容

- 在 `hyperframes-postprocess/` 增加正式 `package.json` 和 `package-lock.json`，把 `hyperframes` 固定为 `0.6.42`，避免继续依赖全局 `npx hyperframes`。
- `hyperframes-postprocess/index.js` 默认改为调用 release 内本地 CLI：`hyperframes-postprocess/node_modules/.bin/hyperframes render ...`，仍保留 `HF_POSTPROCESS_RENDER_CMD` 作为人工覆盖口。
- Node 后处理子进程 PATH 自动补入当前 Node bin、本地 `node_modules/.bin`、`/usr/local/bin`、`/usr/bin`、`/usr/sbin`、`/bin`，降低 supervisor 环境变量不完整导致的失败概率。
- `router/service/video_server2/hyperframes_cli.py` 增加 `HYPERFRAMES_RUNTIME_NOT_READY` preflight，渲染锁前检查 Node、Node 版本、`index.js`、本地 HyperFrames CLI、ffmpeg、Linux Chromium 依赖。
- 新增 `scripts/ensure_hyperframes_runtime.sh`，用于 release 部署后准备或校验共享 Node runtime，并执行 `npm ci --omit=dev --no-audit --no-fund`。
- Node/npm 版本从“接受 22.x/24.x”进一步收紧为默认固定：Node `v22.22.2`、npm `10.9.7`；如需临时兼容 22.x/24.x，必须显式设置 `HYPERFRAMES_ALLOW_COMPATIBLE_NODE=1`。
- 对 `onnxruntime-node` 的在线 postinstall 下载做部署规避：脚本设置 `ONNXRUNTIME_NODE_INSTALL=skip` 与 `npm_config_onnxruntime_node_install=skip`，使用 lock 中已有的 Linux x64 native 包，避免测试服/生产机公网依赖导致 `npm ci` 不稳定。
- `scheduler/collect_scheduler.py` 保留现有 `task_status` 回调口径，只把 `generate_video_duration` 在最终 callback payload 前归一为非负 int 秒。
- 增加单测覆盖 runtime preflight、缺 Node/缺本地 CLI/低版本 Node、preflight 失败不抢渲染锁、callback duration int 化等行为。

## 为什么会出现这个问题

原链路把 HyperFrames 渲染当成“机器上能找到 node/npx/hyperframes 就行”的外部环境能力，问题在测试服暴露出来：

- H20 服务不是在普通交互 shell 里运行，而是由 supervisor/nohup 等服务进程启动；服务进程的 PATH 往往比人工 SSH 进去看到的 PATH 更短。
- 即使人工 shell 能执行 `node` 或 `npx`，也不能证明 `8100/8017/18017` 这些线上进程能找到同一个命令。
- 全局 `npx hyperframes` 没有版本锁，机器之间、release 之间可能解析到不同版本，测试通过不代表后续部署可复现。
- 如果缺 Node、缺 npm 依赖、缺 ffmpeg 或缺 Chromium 系统库，旧代码可能已经进入渲染锁和中途渲染流程后才失败，错误会变成普通 CLI 失败，不利于判断是环境未准备好还是业务渲染失败。
- 依赖安装如果依赖在线 postinstall 下载，会把“机器是否能联网、能否访问 npm/CDN”混进业务发布流程，测试服和生产服都不适合靠这种偶然条件。

这次修复的核心不是“在某台机器手工装一个 Node”，而是把 runtime 变成 release 部署合同：代码、lock、preflight、部署脚本共同定义需要什么环境，缺什么就明确失败。

## 测试环境 Node 现在应该怎么来

当前标准口径：

- 优先使用共享 runtime：`/data/project/hyperframes-runtime/current/bin/node`。
- 如果机器还没有共享 runtime，由运维或部署流程准备离线 tar 包，并设置 `HYPERFRAMES_NODE_TARBALL=/path/to/node-v22.22.2-linux-x64.tar.xz`，再执行 `bash scripts/ensure_hyperframes_runtime.sh`。
- 脚本会把 tar 包解压到 `/data/project/hyperframes-runtime/`，更新 `current` 软链，并校验 Node/npm/ffmpeg/HyperFrames CLI。
- 只有在兼容模式下，才允许临时使用系统 PATH 里的 Node；这不是推荐长期方案。
- 不提交 `node_modules`，每次 release 进入 `/data/project/test_ai_botserver` 后跑 `npm ci` 复现依赖。

## 相关提交

当前功能分支 `feature/ai_v6.3.3_vibevideo` 已包含：

- `3a93ac98 chore: automate hyperframes runtime setup`
- `aa367fd3 fix: pin hyperframes runtime versions`
- `f25f150f fix: harden hyperframes failure handling`

规则：测试服如果发现新 bug，必须先修回 `feature/ai_v6.3.3_vibevideo`，再重新集成到 `test`；不要只修 `test`，避免功能分支以后合 master 时丢掉测试服修复。

## 验证结果

本轮代码侧已记录的验证：

```text
python -m unittest test.test_hyperframes_cli test.test_hyperframes_postprocess test.test_hyperframes_analysis test.test_hyperframes_upload_callback test.test_template_route -v
python -m py_compile router/service/video_server2/hyperframes_cli.py scheduler/collect_scheduler.py
node --check hyperframes-postprocess\index.js
C:\Program Files\Git\bin\bash.exe -n scripts/ensure_hyperframes_runtime.sh
```

后续测试服验收仍需在 H20 release 目录执行：

```bash
bash scripts/ensure_hyperframes_runtime.sh
```

然后重启 `8100/8017/18017`，再跑 `video_diary`、`science_guide`、`minimal` 三条任务确认新旧链路都正常。

## 影响范围

- 影响网感视频 `science_guide` / `video_diary` 的 HyperFrames 后处理 runtime 准备流程。
- `minimal` 仍走旧链路，不应调用 HyperFrames postprocess。
- 不涉及数据库字段变更。
- 不改变 CSM/CRM callback 的 `task_status` 口径。

## 相关文件

- `hyperframes-postprocess/package.json`
- `hyperframes-postprocess/package-lock.json`
- `hyperframes-postprocess/index.js`
- `router/service/video_server2/hyperframes_cli.py`
- `scheduler/collect_scheduler.py`
- `scripts/ensure_hyperframes_runtime.sh`
- `docs/h20-hyperframes-runtime.md`
- `test/test_hyperframes_cli.py`
- `test/test_hyperframes_postprocess.py`
- `test/test_hyperframes_upload_callback.py`

## 相关记录

- [[projects/joying-bot-server/docs/h20-hyperframes-runtime-automation-2026-06-16|H20 HyperFrames Runtime 自动化]]
- [[projects/joying-bot-server/changelog/h20-hyperframes-test-release-runtime-2026-06-16|H20 HyperFrames test 发布与运行时验证]]
- [[projects/joying-bot-server/docs/h20-hyperframes-db-field-change-rules-2026-06-16|H20 HyperFrames 字段变更规则]]

## 图谱链接

- [[projects/joying-bot-server/00-项目概览|项目概览]]
- [[projects/joying-bot-server/changelog/00-changelog-index|更新日志索引]]
- [[projects/joying-bot-server/docs/00-docs-index|参考文档索引]]

## H20 现场只读核验（2026-06-17）

已按登录 skill 经跳板进入 H20 做只读核验，未记录密码。

现场状态：

- 当前测试 release：`/data/project/test_ai_botserver -> /data/project/test_ai_botserver.20260616213821`。
- 共享 runtime：`/data/project/hyperframes-runtime/current -> /data/project/hyperframes-runtime/node-v22.22.2-linux-x64`。
- 共享 Node：`/data/project/hyperframes-runtime/current/bin/node`，版本 `v22.22.2`。
- 共享 npm：`/data/project/hyperframes-runtime/current/bin/npm`，版本 `10.9.7`。
- 系统服务进程 PATH 里没有直接解析到 `node/npm`，这验证了本轮不能依赖系统 PATH 的判断。
- ffmpeg：`/usr/sbin/ffmpeg`，版本 `7.0.2-static`。
- release 内后处理目录存在：`/data/project/test_ai_botserver/hyperframes-postprocess`。
- release 内本地 HyperFrames CLI 存在：`/data/project/test_ai_botserver/hyperframes-postprocess/node_modules/.bin/hyperframes`，版本 `0.6.42`。
- `8100` / `8017` / `18017` 当前 cwd 均为 `/data/project/test_ai_botserver.20260616213821`。

结论：当前测试环境的 Node 不是通过系统 PATH 全局安装提供，而是通过 `/data/project/hyperframes-runtime/current` 共享 runtime 提供；部署脚本补 PATH 后可解析到 Node、npm 和 release 内 HyperFrames CLI。

## 测试成功后的补充复盘

2026-06-17 用户确认最新 `video_diary` 任务已经成功。成功前出现过的关键运行时错误已经整理到参考文档：

- [[projects/joying-bot-server/docs/h20-hyperframes-runtime-automation-2026-06-16#2026-06-17 事故复盘：不要再重复踩的坑|2026-06-17 事故复盘：不要再重复踩的坑]]

后续部署不要只记“Node 装好了”。必须按顺序确认：

1. 当前 release 目录是服务进程实际 cwd。
2. 共享 Node runtime 固定为 `v22.22.2`，npm 固定为 `10.9.7`。
3. 当前 release 内执行过 `scripts/ensure_hyperframes_runtime.sh`。
4. 当前 release 内存在 `hyperframes-postprocess/node_modules/.bin/hyperframes`，版本 `0.6.42`。
5. Linux Chrome 依赖包含 `libgbm.so.1`。
6. ffmpeg 可从服务进程 PATH 找到，测试服当前为 `/usr/sbin/ffmpeg`。
7. 再重启 `8100/8017/18017`，并确认端口进程 cwd 都指向当前 release。

这次我自己的误判也要保留：只看 `node -v` 或脚本在软链目录输出 ready 不够，必须检查“服务进程 cwd 对应的物理 release 目录”里本地 CLI 是否存在。否则会出现共享 Node 是好的，但当前 release 的 `node_modules/.bin/hyperframes` 缺失，任务报：

```text
HYPERFRAMES_CLI_FAILED: HYPERFRAMES_RUNTIME_NOT_READY: local HyperFrames CLI missing
```
