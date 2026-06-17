---
date: 2026-06-17
project: joying-bot-server
type: changelog
tags: [changelog, h20, hyperframes, runtime, pillow]
aliases: [h20-hyperframes-cover-python-pillow-fix-2026-06-17]
---

# H20 HyperFrames cover Python / Pillow 修复

## 改动类型

- Bugfix / runtime contract hardening。
- 不改数据库字段，不改 CRM/CSM 回调口径，不改模板路由。

## 背景

测试库 `t_video_generate_task` 中 id=1476 的网感视频任务失败：

```text
HYPERFRAMES_RENDER_FAILED: H20_POSTPROCESS_FAILED: Command failed: "python3" ".../hyperframes-postprocess/scripts/cover_gen.py" ...
ModuleNotFoundError: No module named 'PIL'
```

该任务已经走过 Node/HyperFrames CLI、结构化分析和视频渲染，失败点落在 `cover_gen.py` 封面生成阶段。

## 原因

`hyperframes-postprocess/index.js` 的封面生成默认使用 `HF_POSTPROCESS_PYTHON || PYTHON || python3`。H20 后端 Python wrapper 没有显式把当前服务 Python 传给 Node 后处理，导致测试服运行时可能解析到一个没有 Pillow 的 `python3`。`cover_gen.py` 依赖 `PIL`，所以封面阶段失败。

这不是数据库字段问题，也不是模板逻辑问题；这是 Python 解释器选择不确定造成的 runtime 契约问题。

## 改动内容

- `router/service/video_server2/hyperframes_cli.py`
  - 新增 cover Python 默认选择：优先 `HF_POSTPROCESS_PYTHON`，其次 `PYTHON`，最后 `sys.executable`。
  - 调用 Node 后处理时显式传入 `HF_POSTPROCESS_PYTHON`，默认指向当前 H20 服务 Python。
  - runtime preflight 新增 Pillow 检查：渲染锁之前执行 `import PIL`，失败时抛 `HYPERFRAMES_RUNTIME_NOT_READY: cover python missing Pillow/PIL`。
- `test/test_hyperframes_cli.py`
  - 新增缺 Pillow 的 preflight 单测。
  - 断言渲染调用会把 `HF_POSTPROCESS_PYTHON` 传给 Node 子进程。

## 提交与集成

- 功能分支 `feature/ai_v6.3.3_vibevideo`：`3b5e3753 fix: use service python for hyperframes cover`
- test 集成提交：`46780d79 fix: use service python for hyperframes cover`
- 推送到远端 `test` 后，测试服 release 更新到：`/data/project/test_ai_botserver.20260617183203`

## 验证结果

本地验证：

```text
python -m unittest test.test_hyperframes_cli test.test_hyperframes_postprocess test.test_hyperframes_analysis test.test_hyperframes_upload_callback test.test_template_route -v
Ran 84 tests OK

python -m py_compile router/service/video_server2/hyperframes_cli.py scheduler/collect_scheduler.py router/service/video_server2/hyperframes_analysis.py
OK

node --check hyperframes-postprocess/index.js
OK
```

测试服验证：

- release marker 已存在：`HF_POSTPROCESS_PYTHON` 和 `cover python missing Pillow/PIL`。
- 执行 `scripts/ensure_hyperframes_runtime.sh`，输出 `runtime ready`。
- 当前 release 的 HyperFrames CLI：`hyperframes=0.6.42`。
- 重启后端口 cwd：
  - `8100 -> /data/project/test_ai_botserver.20260617183203`
  - `8017 -> /data/project/test_ai_botserver.20260617183203`
  - `18017 -> /data/project/test_ai_botserver.20260617183203`
- 健康检查：
  - `8100 /status/check -> {"status":"ok"}`
  - `8017 /status/check -> {"status":"ok"}`

## 影响范围

- 影响 `science_guide` / `video_diary` 网感链路的封面生成阶段。
- `minimal` 旧链路不进入 HyperFrames postprocess，不受影响。
- 已失败的 id=1476 不会自动恢复，需要重新提交一条任务验证新代码。

## 后续注意

- 测试服后续如果再次出现环境类问题，先确认 wrapper 是否显式传递运行时依赖路径，避免依赖 supervisor 的 PATH。
- 测试服发现的新 bug 必须先修回 `feature/ai_v6.3.3_vibevideo`，再从 test 侧集成验证。
- 不要只在 `test` 集成分支临时修复。

## 图谱链接

- [[projects/joying-bot-server/00-项目概览|项目概览]]
- [[projects/joying-bot-server/changelog/00-changelog-index|更新日志索引]]
- [[projects/joying-bot-server/changelog/h20-hyperframes-runtime-automation-fix-2026-06-17|h20-hyperframes-runtime-automation-fix-2026-06-17]]
