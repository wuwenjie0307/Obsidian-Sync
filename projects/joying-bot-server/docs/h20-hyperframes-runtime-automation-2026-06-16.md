---
date: 2026-06-16
project: joying-bot-server
type: doc
tags: [h20, hyperframes, runtime, deployment, node]
aliases: [H20 HyperFrames Runtime 自动化, 网感视频 Node Runtime 部署规则]
---

# H20 HyperFrames Runtime 自动化

## 结论

> 2026-06-23 口径修正：测试环境已经可以直接读取 `/data/project/hyperframes-runtime` 共享运行时。`scripts/ensure_hyperframes_runtime.sh` 不再作为每次代码发版后的必跑步骤，只在新机器初始化、共享 runtime 损坏修复、Node/HyperFrames 版本升级时执行。日常发版复用共享 runtime，最多做只读路径/版本检查，渲染前仍由 Python preflight 兜底拦截环境问题。

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

## 2026-06-17 补充：本轮 runtime 自动化修复成因与边界

这一步不是为了在测试服“临时找一个 node 跑起来”，而是把 HyperFrames runtime 从机器手工状态收敛成部署合同。

修复内容：

- `hyperframes-postprocess/package.json` / `package-lock.json` 固定 `hyperframes@0.6.42`，默认不再依赖全局 `npx hyperframes`。
- Node 后处理默认使用 release 内本地 `node_modules/.bin/hyperframes`，保留 `HF_POSTPROCESS_RENDER_CMD` 作为人工覆盖口。
- Python 渲染前增加 `HYPERFRAMES_RUNTIME_NOT_READY` preflight，检查 Node、版本、本地 CLI、ffmpeg、Chromium Linux 依赖；失败时不进入渲染锁。
- `scripts/ensure_hyperframes_runtime.sh` 统一准备共享 runtime、执行 `npm ci`、校验 CLI 和 ffmpeg。
- 默认 Node/npm 版本固定为 Node `v22.22.2`、npm `10.9.7`；临时兼容 22.x/24.x 需要显式 `HYPERFRAMES_ALLOW_COMPATIBLE_NODE=1`。
- 脚本跳过 `onnxruntime-node` 在线 postinstall 下载，避免部署依赖公网下载。

问题成因：H20 服务进程的 PATH 和人工 SSH shell 不一定一致，全局 `npx` 又没有版本锁；因此“机器上似乎装了 Node”不能证明测试服务进程能稳定执行 HyperFrames 渲染。旧方案会把缺 Node/缺 CLI/缺 ffmpeg/缺 Chromium 系统库都表现成中途 CLI 失败，定位成本高，也不利于生产复现。

测试环境 Node 当前标准来源：优先 `/data/project/hyperframes-runtime/current/bin/node`；如果没有共享 runtime，则由离线 tar 包 `HYPERFRAMES_NODE_TARBALL` 通过 `scripts/ensure_hyperframes_runtime.sh` 解压准备。系统 PATH 里的 Node 只作为显式兼容模式下的临时兜底，不作为长期部署方案。

关联提交：`3a93ac98`、`aa367fd3`、`f25f150f`。后续测试服 bug 必须先修回 `feature/ai_v6.3.3_vibevideo`，再重新集成到 `test`。

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

## 2026-06-17 事故复盘：不要再重复踩的坑

这次测试服最终 `video_diary` 新任务已由用户确认成功，但成功前暴露了几类运行时问题。这里按“照着做就行”的方式记录，后续部署先看这一段。

### 一句话版本

网感视频不是纯 Python 功能。它最后会调用 Node.js 运行 `hyperframes-postprocess/index.js`，再由 HyperFrames 启动 Chrome/Chromium 做页面渲染，并用 ffmpeg 产出视频。因此一台机器必须同时准备好：

1. 固定版本 Node.js。
2. release 目录内的 `hyperframes-postprocess/node_modules`。
3. 本地 HyperFrames CLI：`hyperframes-postprocess/node_modules/.bin/hyperframes`。
4. ffmpeg。
5. Chrome/Chromium 在 Linux 上需要的系统动态库，例如 `libgbm.so.1`。

少任何一个，都不是“业务模板坏了”，而是运行时没有准备好。

### 本次实际出现过的问题

1. 缺 Node 或服务进程找不到 Node

早期错误表现为：

```text
HYPERFRAMES_CLI_FAILED: [Errno 2] No such file or directory: 'node'
```

原因：人工 SSH 进机器看到的 PATH，不等于 `8100/8017/18017` 服务进程的 PATH。服务进程可能找不到 `node`，所以不能靠“我在 shell 里敲 node 可以用”来判断。

正确做法：统一使用共享 runtime：

```bash
/data/project/hyperframes-runtime/current/bin/node
```

当前标准版本：

```text
Node.js v22.22.2
npm 10.9.7
```

2. 缺 release 内本地 HyperFrames CLI

错误表现：

```text
HYPERFRAMES_CLI_FAILED: HYPERFRAMES_RUNTIME_NOT_READY: local HyperFrames CLI missing: /data/project/test_ai_botserver.20260616213821/hyperframes-postprocess/node_modules/.bin/hyperframes
```

原因：共享 Node 准备好了，不代表当前 release 目录的 npm 依赖也准备好了。每次新 release 都是一个新的目录，例如：

```bash
/data/project/test_ai_botserver.20260616213821
```

服务进程 cwd 指向这个物理目录时，它会在这个目录下找：

```bash
hyperframes-postprocess/node_modules/.bin/hyperframes
```

如果部署后没有在当前 release 目录执行 `npm ci`，这个文件就不存在。任务会在渲染前被 preflight 拦住。

正确做法：每次 release 部署完成后、重启服务前，在当前 release 目录执行：

```bash
cd /data/project/test_ai_botserver
HYPERFRAMES_RUNTIME_HOME=/data/project/hyperframes-runtime bash scripts/ensure_hyperframes_runtime.sh
```

执行完必须看到：

```text
[hyperframes-runtime] node=v22.22.2 path=/data/project/hyperframes-runtime/current/bin/node
[hyperframes-runtime] npm=10.9.7 path=/data/project/hyperframes-runtime/current/bin/npm
[hyperframes-runtime] hyperframes=0.6.42 path=/data/project/test_ai_botserver/hyperframes-postprocess/node_modules/.bin/hyperframes
[hyperframes-runtime] runtime ready
```

只看到 Node ready 不够，必须看到 `hyperframes=0.6.42` 和 `runtime ready`。

3. Chrome/Chromium 缺 Linux 系统库

早期错误表现为 Chrome 启动失败，关键缺库是：

```text
libgbm.so.1: cannot open shared object file
```

原理：HyperFrames 渲染时会启动 Chrome/Chromium，把 HTML/CSS/视频模板渲染成画面，再生成视频。服务器没有桌面环境也可以 headless 渲染，但 Chrome 二进制仍依赖 Linux 图形相关动态库。`libgbm.so.1` 属于这类基础库。

正确做法：Ubuntu 安装系统包：

```bash
apt-get install -y libgbm1
```

验证：

```bash
ldconfig -p | grep 'libgbm.so.1'
```

现在代码和脚本已经加了检查：

- `scripts/ensure_hyperframes_runtime.sh` 会检查 `libgbm.so.1`。
- `router/service/video_server2/hyperframes_cli.py` 渲染前 preflight 会报 `HYPERFRAMES_RUNTIME_NOT_READY`，避免进入半路渲染后才失败。

4. 失败原因太长，导致失败状态落库失败

曾经出现过：真正的失败原因已经产生，但 `fail_reason` 太长，写回 `t_video_generate_task.fail_reason` 时 MySQL 报 `Data too long for column 'fail_reason'`，结果任务反而停在 `task_status=2`，看起来像“卡住”。

修复：`scheduler/collect_scheduler.py` 增加 `_video_task_fail_reason_for_storage`，落库前截断失败原因，保留前缀和 truncated 标记。这样以后即使失败原因很长，也应该能把任务置为失败并回调。

5. 我这次的误判点

- 一开始把“脚本能跑出 Node 版本”当成 runtime OK，这是不够的。必须确认当前 release 目录内的 `.bin/hyperframes` 存在。
- 一开始容易把 `/data/project/test_ai_botserver` 软链路径和真实 release 目录混在一起看。实际服务进程 cwd 是物理目录，例如 `/data/project/test_ai_botserver.20260616213821`，验证时必须看进程 cwd。
- 一开始看到 Chrome 缺 `libgbm.so.1`，容易只在机器上补包，但如果代码里不加 preflight，下一台机器还会重新踩坑。所以这次把检查写进了脚本和 Python preflight。
- 一开始 DB 里的任务 `task_status=2` 容易被理解成还在跑；实际有可能是失败落库失败、或失败前“处理中”回调已成功但最终状态没写上。以后必须结合 `logs/run.log`、`fail_reason`、`hf_result_path`、模型池锁一起看。

### 小学生版部署步骤

每次把网感视频代码部署到 H20 测试服或生产服，按这个顺序做：

1. 先确认代码已经发布到新 release 目录。

```bash
readlink -f /data/project/test_ai_botserver
```

2. 进入当前 release。

```bash
cd /data/project/test_ai_botserver
```

3. 准备 Node 和 HyperFrames 依赖。

```bash
HYPERFRAMES_RUNTIME_HOME=/data/project/hyperframes-runtime bash scripts/ensure_hyperframes_runtime.sh
```

4. 看输出，不要跳过。

必须看到：

```text
node=v22.22.2
npm=10.9.7
hyperframes=0.6.42
runtime ready
```

5. 再确认当前 release 内 CLI 文件真的存在。

```bash
test -x hyperframes-postprocess/node_modules/.bin/hyperframes && echo OK
```

6. 再重启服务。

```bash
supervisorctl restart ai_botserver
supervisorctl restart ai_botserver_sch
```

如果 `8100` 是单独 nohup 启动的，要按 H20 重启 skill 查 PID 后精确重启，不能宽泛 `pkill`。

7. 重启后确认三个端口 cwd 都指向当前 release。

```bash
for p in 8100 8017 18017; do
  pids=$(ss -ltnp 2>/dev/null | awk -v port=":$p" '$4 ~ port {print}' | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | sort -u)
  echo "PORT $p PIDS ${pids:-none}"
  for pid in $pids; do
    echo "PID $pid CWD $(readlink -f /proc/$pid/cwd 2>/dev/null)"
  done
done
```

8. 再提任务验收。

建议顺序：

- `video_diary`：验证网感视频日记链路。
- `science_guide`：验证另一个 HyperFrames 网感链路。
- `minimal`：验证旧链路不受影响。

### 以后看到这些报错怎么判断

| 报错关键词 | 说明 | 先做什么 |
|---|---|---|
| `No such file or directory: 'node'` | 服务进程找不到 Node | 查 `HYPERFRAMES_NODE_BINARY` 和 `/data/project/hyperframes-runtime/current/bin/node` |
| `local HyperFrames CLI missing` | 当前 release 没跑 npm ci 或依赖目录不完整 | 在当前 release 跑 `scripts/ensure_hyperframes_runtime.sh` |
| `libgbm.so.1` | Chrome Linux 系统库缺失 | 安装/确认 `libgbm1` |
| `ffmpeg missing` | ffmpeg 不在 PATH | 确认 `/usr/sbin/ffmpeg` 或配置 PATH |
| `Data too long for column 'fail_reason'` | 失败原因太长，状态落库失败 | 确认当前代码包含 fail_reason 截断修复 |
| `task_status=2` 长时间不变 | 不一定是真在跑 | 查日志、临时目录、模型池锁、最终回调 |

### 最终口径

Node.js 不应该每台机器手工临时装。当前项目的最优方案是：

- 机器级别只维护一个共享 Node runtime：`/data/project/hyperframes-runtime/current`。
- 项目级别用 `hyperframes-postprocess/package-lock.json` 固定 HyperFrames 依赖。
- 每次 release 后必须跑 `scripts/ensure_hyperframes_runtime.sh`。
- 服务启动前必须确认当前 release 内 `node_modules/.bin/hyperframes` 存在。
- 缺依赖要让 preflight 明确失败，不要进入半路渲染再猜。
## 2026-06-23 运维口径修正：日常发版复用共享 runtime

这次以用户确认的 H20 测试服现状为准：测试环境已经能直接读取共享运行时，不需要每次发版都重新执行 runtime 解包或依赖准备。

当前推荐口径：

- 共享运行时由运维统一维护：`/data/project/hyperframes-runtime`。
- 日常代码 release 复用已准备好的共享 Node 和 HyperFrames deps。
- `scripts/ensure_hyperframes_runtime.sh` 只用于三类场景：新机器初始化、共享 runtime 损坏修复、Node/HyperFrames 升级。
- 日常发版前如需确认，只做只读检查，不做安装/解包：

```bash
test -x /data/project/hyperframes-runtime/current/bin/node
test -x /data/project/hyperframes-runtime/deps/hyperframes-0.6.42/node_modules/.bin/hyperframes
/data/project/hyperframes-runtime/current/bin/node -v
/data/project/hyperframes-runtime/deps/hyperframes-0.6.42/node_modules/.bin/hyperframes --version
```

- 代码侧 `router/service/video_server2/hyperframes_cli.py` 的 preflight 继续保留，负责在渲染前明确报出 runtime 缺失、版本不对、ffmpeg/libgbm 等环境问题。
- 本文早期“每次 release 后必须执行 `ensure_hyperframes_runtime.sh`”的表述已废弃；后续给运维的说明应改成“统一准备并维护共享 runtime，代码发版不重复安装”。

## 图谱链接补充

- [[projects/joying-bot-server/changelog/h20-hyperframes-shared-runtime-deps-2026-06-17|h20-hyperframes-shared-runtime-deps-2026-06-17]]
