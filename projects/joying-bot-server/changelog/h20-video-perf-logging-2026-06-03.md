---
date: "2026-06-03"
tags: [changelog, h20, video-generation, performance, logging, voxcpm, latentsync]
---

# h20 视频生成结构化耗时日志

## 改动类型

- [x] 新功能
- [ ] Bug 修复
- [ ] 重构
- [ ] 配置变更

## 改动内容

本次在 h20 视频生成链路增加第一阶段结构化耗时日志，不新增 DB 表，不改 CRM 回调字段。

新增统一日志 helper：`router/service/video_server2/perf_log.py`，日志前缀固定为：

```text
[video_perf]
[video_perf_summary]
```

主要埋点：

- `scheduler/collect_scheduler.py`：记录 `queue_wait_ms`、`config_wait_ms`、`generate_total_ms`、`callback_processing_ms`、`callback_finish_ms`，并在任务结束或早退时输出 scheduler 级 summary。
- `router/service/video_server2/video_work.py`：用 `VideoPerfCollector` 拆分参考音频下载/上传/Whisper/转换、VoxCPM、LatentSync、转码、字幕、混剪、背景音乐、封面、最终上传、临时文件清理等阶段。
- `router/service/video_server2/voxcpm_tts.py`：记录 VoxCPM API 总耗时、首字节耗时、首字节后的流式下载/写文件耗时、HTTP 状态码和输出大小。
- `router/service/video_server2/latentsync_service.py`：记录 LatentSync API 总耗时、首字节耗时、首字节后的流式下载/写文件耗时、HTTP 状态码和输出大小。
- `router/service/video_server2/video_tool.py`：记录下载、CRM 登录、上传耗时、文件大小、上传返回 code 和平均速度。

测试补充：

- `test/test_video_perf_logging.py` 覆盖日志 helper、阶段异常 summary、下载 mock、上传 mock、VoxCPM streaming mock、LatentSync streaming mock，以及 scheduler 源码埋点完整性。
- 相关验证命令：`python -m unittest test.test_responses_stream_disconnect test.test_video_perf_logging`。
- 语法验证命令：`python -m py_compile router\service\video_server2\perf_log.py router\service\video_server2\video_tool.py router\service\video_server2\voxcpm_tts.py router\service\video_server2\latentsync_service.py router\service\video_server2\video_work.py scheduler\collect_scheduler.py agent\llm_models.py`。

## 影响范围

- 影响 h20 视频生成任务的日志输出和排查能力。
- 不改 `t_comfyui_config` 调度规则，一行仍代表一套 VoxCPM + LatentSync 服务组。
- 不改 CRM 外部接口和回调 payload。
- 不新增库表，不改变现有生成流程的业务语义。
- 封面阶段为了拆出 `cover_download`，会先下载封面图再传给 `add_cover_to_video`，该函数内部仍会对本地文件做临时 copy；这是第一阶段可接受的轻量开销，后续可再优化。

## 后续验证

上线测试服后需要跑 5 条真实任务：20 秒普通视频、20 秒带背景音乐、带封面、带混剪素材、100 秒以上长视频。

验证口径：

```bash
grep -F "[video_perf_summary]" <scheduler日志>
grep -F "[video_perf]" <scheduler日志>
```

目标是按单条任务明确慢点：排队、声音克隆、下载、转码、唇形同步、字幕/封面、上传、回调。

## 相关 Commit

- 未提交，本地工作区改动待提交。

## 2026-06-03 13:45 h20 部署验证与重启

推送 `001bdc47 feat: add video performance logging` 后检查 h20：

- `/data/project/test_ai_botserver` 已切到新部署目录：`/data/project/test_ai_botserver.20260603134321`。
- 新部署目录已包含 `router/service/video_server2/perf_log.py`。
- `scheduler/collect_scheduler.py` 已包含 `emit_video_perf_summary`、`generate_total`、`callback_finish` 埋点。
- `video_work.py` 已包含 `VideoPerfCollector`。
- `voxcpm_tts.py` 和 `latentsync_service.py` 已包含 `first_byte_ms` 埋点。

发现并处理的问题：

- `ai_botserver` 8017 已自动跑在新目录。
- 旧 `ai_botserver_sch` scheduler 仍跑在旧目录 `test_ai_botserver.20260602145953`，已通过 `supervisorctl stop/start ai_botserver_sch` 重启到新目录。
- 旧 8100 公网入口仍跑在旧目录 `test_ai_botserver.20260602145953`，已停止旧进程，并从 `/data/project/test_ai_botserver` 当前 symlink 重新 `nohup` 启动。

最终验证：

- 8017 cwd：`/data/project/test_ai_botserver.20260603134321`
- 8100 cwd：`/data/project/test_ai_botserver.20260603134321`
- scheduler cwd：`/data/project/test_ai_botserver.20260603134321`
- `http://127.0.0.1:8017/status/check` 返回 `{"status":"ok"}`
- `http://127.0.0.1:8100/status/check` 返回 `{"status":"ok"}`
- 模型端口 `8120`/`8121`/`8122`/`8123`/`8124`/`8125` `/health` 均返回 `{"status":"ok"}`

说明：当前已确认服务进程加载新代码；只有后续产生新视频任务后，日志中才会出现新的 `[video_perf]` / `[video_perf_summary]` 记录。

## 2026-06-03 14:36 第一条新埋点样本

### 监控动作

- 发现 `1064`/`1065`/`1066` 是重启前旧 scheduler 领取的任务，没有 `[video_perf]` 日志。
- 经确认后，将测试库中这 3 条任务从 `task_status=2` 重置回 `task_status=0`，并释放 `t_comfyui_config` 的 `id=1`/`id=2`/`id=10` 为 `is_active=1`。
- 新 scheduler 后续正常领取新任务并产出结构化耗时日志。

### 有效样本

任务：`task_id=1067`，`job_id=1076`，带背景音乐，最终成功。

总耗时：

```text
generate_total_ms = 796820 ms ≈ 13.28 分钟
queue_wait_ms = 6250 ms ≈ 6.25 秒
config_wait_ms = 36 ms
callback_processing_ms = 56 ms
callback_finish_ms = 58 ms
```

阶段 Top 耗时：

| 阶段 | 耗时 | 说明 |
|---|---:|---|
| `latentsync` | 731693 ms / 12.19 分钟 | 最大瓶颈，占生成总耗时约 91.8% |
| `voxcpm_clone` | 13681 ms / 13.7 秒 | 声音克隆本身不慢 |
| `source_video_download` | 8348 ms / 8.3 秒 | 源视频 87.4 MB，下载速度约 10.47 MB/s |
| `subtitle_ass_generate` | 7602 ms / 7.6 秒 | 字幕 ASS 生成 |
| `standardize_9x16_30fps` | 6680 ms / 6.7 秒 | 格式标准化 |
| `cover_concat` | 6125 ms / 6.1 秒 | 封面拼接 |
| `subtitle_burn` | 5900 ms / 5.9 秒 | 字幕烧录 |
| `background_music` | 4722 ms / 4.7 秒 | 背景音乐处理 |

模型 API 细节：

```text
voxcpm_api cost_ms=13681, first_byte_ms=11295, stream_download_ms=2386, output=5.08 MB
latentsync_api cost_ms=731692, first_byte_ms=731580, stream_download_ms=112, output=42.56 MB
```

结论：

- 当前样本的慢点不是排队、不是下载上传、不是声音克隆，而是 LatentSync 远端模型处理。
- `latentsync_api.first_byte_ms` 几乎等于总耗时，说明时间主要花在模型服务端推理/处理，客户端下载结果只用了约 112 ms。
- 下一步优化应优先查 LatentSync 容器内部：GPU 利用率、输入视频帧率/分辨率、是否每次重新加载模型、推理参数、是否存在 CPU fallback。

### 当前进度

计划中“第一阶段结构化日志上线并拿到真实样本”已完成 1 条有效样本，还需要继续覆盖：

- [x] 带背景音乐视频：`task_id=1067`
- [ ] 20 秒普通视频
- [ ] 带封面视频
- [ ] 带混剪素材视频
- [ ] 100 秒以上长视频
