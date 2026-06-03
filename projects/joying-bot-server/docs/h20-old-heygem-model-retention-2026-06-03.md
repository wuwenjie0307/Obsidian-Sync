---
date: "2026-06-03"
tags: [h20, heygem, duix, latentsync, model-switch, video-generation, runbook]
---

# h20 旧 Heygem/duix 模型保留与当前 LatentSync 切换状态

## 背景

用户反馈：LatentSync 在手部遮挡/手在面部前晃动较多的场景下，抗干扰能力不如旧 Heygem/duix 模型，容易出现画面失真。因此需要确认：

- 旧模型是否还在。
- 旧模型调用逻辑是否还在。
- 当前 h20 测试服是否已经把旧逻辑删除或只是暂时注释。
- 后续是否能切回旧模型。

## 2026-06-03 h20 现场检查结论

结论：旧 Heygem/duix 模型没有被删，旧调用代码也还在；但当前 h20 测试服主调度链路已经切到 LatentSync，不会主动走旧 Heygem/duix。

## 当前主调度链路

当前 scheduler 使用的是：

```text
scheduler/collect_scheduler.py
-> from router.service.video_server2.video_work import video_work_Heygem_Whisper
-> router/service/video_server2/video_work.py
-> LatentSyncService(...)
```

h20 现场代码确认：

```text
scheduler/collect_scheduler.py:3444
from router.service.video_server2.video_work import video_work_Heygem_Whisper
```

当前 `video_server2/video_work.py` 中的切换点：

```python
# 旧方案：duix.avatar Docker / Heygem
# video_service = VideoGenService(video_domain=Original_video_url, task_id=task_id)

# 新方案：LatentSync，当前启用
video_service = LatentSyncService(api_base=latentsync_api_base or "", task_id=task_id)
```

也就是说，旧 `VideoGenService` 逻辑是被注释了，不是删了。

## 旧代码是否还在

旧视频生成服务封装仍存在：

```text
router/service/video_server2/video_gen_service.py
router/service/video_server/video_gen_service.py
```

旧接口调用方式仍是：

```text
/easy/submit
/easy/query
```

旧版 `router/service/video_server/video_work.py` 中仍然直接使用 `VideoGenService`：

```python
video_service = VideoGenService(video_domain=Original_video_url, task_id=task_id)
# video_service = LatentSyncService(task_id=task_id)
```

这说明老代码链路保留着，只是当前 scheduler 不导入这套旧 `video_server` 主流程。

## h20 现场服务状态

h20 当前相关配置：

```text
video_domain=http://a800:6002
latentsync_api_base=http://127.0.0.1:8101
voxcpm_api_base=http://127.0.0.1:8110
```

服务区分：

| 地址/端口 | 含义 |
|---|---|
| `http://a800:6002` | 旧 Heygem/duix easy 接口 |
| `127.0.0.1:8101` | 裸机 LatentSync API，不是旧 Heygem |
| `127.0.0.1:8110` | 裸机 VoxCPM API |
| `127.0.0.1:8120-8127` | Docker VoxCPM/LatentSync 4 组模型池 |

现场检查结果：

```text
a800 -> 222.71.55.27
a800:6002 TCP 通
http://a800:6002/easy/query?code=__codex_probe__
返回：code=10004, msg=任务不存在, success=true
```

该结果说明旧 Heygem/duix easy 服务接口还活着，只是测试 probe code 不存在。

h20 本机健康检查：

```text
8101 -> {"status":"ok"}
8110 -> {"status":"ok"}
8120 -> {"status":"ok"}
8121 -> {"status":"ok"}
8122 -> {"status":"ok"}
8123 -> {"status":"ok"}
8124 -> {"status":"ok"}
8125 -> {"status":"ok"}
8126 -> {"status":"ok"}
8127 -> {"status":"ok"}
```

## 为什么不能只改 DB 切回旧模型

当前 scheduler 读取 `t_comfyui_config` 后：

```text
config_value_audio -> VoxCPM API base
config_value       -> LatentSync API base
```

当前 `LatentSyncService` 会把 `config_value` 拼成：

```text
{config_value}/v1/lip-sync
```

但旧 Heygem/duix 服务需要调用的是：

```text
http://a800:6002/easy/submit
http://a800:6002/easy/query
```

所以如果直接把 `t_comfyui_config.config_value` 改成：

```text
http://a800:6002
```

当前代码会错误请求：

```text
http://a800:6002/v1/lip-sync
```

这不是旧模型的接口，因此不能通过单纯替换 DB 地址完成切回。

## 当前风险判断

- 旧模型没有删除。
- 旧接口 `a800:6002` 仍可访问。
- 旧 `VideoGenService` 调用封装仍在代码里。
- 当前主调度链路已经切到 LatentSync。
- 当前数据库模型池 `t_comfyui_config` 只适配 VoxCPM + LatentSync 服务组，不适配 Heygem/duix 的 `/easy/*` 接口。

## 建议切换方案

如果后续要保留 LatentSync 和 Heygem/duix 双模型切换，不建议靠注释代码或直接改 DB 地址，建议加显式模型类型开关，例如：

```text
lip_sync_engine = latentsync / heygem
```

调用规则：

```text
lip_sync_engine=latentsync
-> LatentSyncService
-> /v1/lip-sync

lip_sync_engine=heygem
-> VideoGenService
-> /easy/submit + /easy/query
```

短期可做方案：

1. 在配置或 DB 中增加模型类型字段，或者临时用环境变量控制。
2. `video_work_Heygem_Whisper` 中保留两个 service：
   - `LatentSyncService`
   - `VideoGenService`
3. 根据开关决定使用哪个唇形模型。
4. 不删除旧 Heygem/duix 代码和服务。
5. 对“手遮脸/手在脸前晃动”场景优先切 Heygem/duix 做回归对比。

## 对外口径

可以这样说：

```text
旧 Heygem/duix 没删，服务也还在，a800:6002 的 easy 接口还能通；只是当前 h20 主调度链路已经切到 LatentSync。现在不能单纯改 DB 地址切回旧模型，因为 LatentSync 走 /v1/lip-sync，旧 Heygem 走 /easy/submit 和 /easy/query。后续如果要支持按场景切换，需要加一个明确的 lip_sync_engine 开关，让代码在 LatentSyncService 和 VideoGenService 之间选择。
```
