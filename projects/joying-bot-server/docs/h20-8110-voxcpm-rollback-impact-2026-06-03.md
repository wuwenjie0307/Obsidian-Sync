---
date: "2026-06-03"
tags: [h20, voxcpm, docker, model-pool, ops, rollback]
---

# h20 8110 VoxCPM 裸机服务停用影响判断

## 背景

2026-06-03 在 h20 机器的 GPU 进程列表中看到一条旧裸机 VoxCPM 服务：

```text
/data/server/anaconda3/bin/python /data/projects/joyingbot-new/router/service/video_server/voxcpm_api.py --port 8110
```

该进程位于 GPU0，显存占用约 22GB。当前问题是：测试服里停掉这条 `8110` 服务，是否会影响测试服正常运行。

## 当前判断

如果只看 h20 测试服视频生成主链路，`8110` 当前不应再是必需服务。

当前主链路已经切到 Docker 多实例 + DB 资源池调度：

```text
CRM -> /crm/generate_video_task
-> Bot 入库 t_video_generate_task
-> ai_botserver_sch 扫描任务
-> 领取 zhugedata_test.t_comfyui_config 中 is_active=1 的服务组
-> config_value_audio 调 VoxCPM
-> config_value 调 LatentSync
-> 任务完成或失败后释放 is_active 回 1
```

当前已记录的 Docker 模型服务组：

| 服务组 | VoxCPM | LatentSync | DB config_id |
|---|---|---|---|
| 第 1 组 | `http://127.0.0.1:8120` | `http://127.0.0.1:8121` | `id=1` |
| 第 2 组 | `http://127.0.0.1:8122` | `http://127.0.0.1:8123` | `id=2` |
| 第 3 组 | `http://127.0.0.1:8124` | `http://127.0.0.1:8125` | `id=10` |

因此，只要测试库 `t_comfyui_config.config_value_audio` 没有再指向 `http://127.0.0.1:8110`，视频生成主链路停掉 `8110` 后不应受影响。

## 风险点

### 1. 声音试听接口可能仍依赖 8110

`/crm/voice_clone_audition` 不走 `t_comfyui_config` 模型池，它在 `router/crm_server.py` 中读取全局配置：

```text
h20_api_base = conf().get('h20_api_base', '') or H20_API_BASE
h20_url = f'{h20_api_base}/v1/clone-voice'
```

本地仓库 `config/config-dev.json` 当前仍是：

```json
"h20_api_base": "http://127.0.0.1:8110",
"voxcpm_api_base": "http://127.0.0.1:8110"
```

如果 h20 当前真实运行配置也仍指向 `8110`，停掉该服务会影响 `/crm/voice_clone_audition`，表现为试听接口返回语音合成服务不可用或连接失败。

### 2. 8110 是旧裸机回滚目标

6 月 2 日模型池交接记录中明确提到：旧裸机 `8110/8101` 短期保留作为回滚。停掉 `8110` 不等于影响主链路，但会减少快速回滚能力。

### 3. 只停父进程可能不会释放全部显存

截图里 GPU0 还有多个 multiprocessing 子进程。停掉 `voxcpm_api.py --port 8110` 后，需要重新看 `nvidia-smi`，确认相关子进程也退出，否则显存可能不会完全释放。

## 停服务前确认项

### 1. Docker 模型池健康检查

```bash
curl -s http://127.0.0.1:8120/health
curl -s http://127.0.0.1:8121/health
curl -s http://127.0.0.1:8122/health
curl -s http://127.0.0.1:8123/health
curl -s http://127.0.0.1:8124/health
curl -s http://127.0.0.1:8125/health
```

预期均返回：

```json
{"status":"ok"}
```

### 2. 测试库资源池确认没有 8110

```sql
SELECT id, config_value_audio, config_value, is_active
FROM zhugedata_test.t_comfyui_config
WHERE config_key = 'comfyui_url';
```

确认：

```text
config_value_audio 不包含 http://127.0.0.1:8110
config_value 不包含 http://127.0.0.1:8101，除非仍有意保留旧 LatentSync 组
```

### 3. Bot 全局配置确认

```bash
grep -n '"h20_api_base"\|"voxcpm_api_base"' /data/project/test_ai_botserver/config/config-dev.json
```

如果仍是 `8110`，则：

- 不停 `8110`；或
- 先把 `h20_api_base` 改到一个健康的 Docker VoxCPM，例如 `http://127.0.0.1:8120`，再重启 Bot；或
- 明确接受停掉后试听接口暂时不可用。

### 4. 日志确认实际调用端口

scheduler 日志应看到类似：

```text
voxcpm_api_base=http://127.0.0.1:8120
voxcpm_api_base=http://127.0.0.1:8122
voxcpm_api_base=http://127.0.0.1:8124
```

不要再出现主链路调用：

```text
http://127.0.0.1:8110/v1/clone-voice
```

## 操作结论

可以这样对外表述：

```text
红线那条 8110 是旧裸机 VoxCPM 服务。现在视频生成主链路已经走 Docker 模型池 8120/8122/8124，对应 LatentSync 8121/8123/8125，所以在 DB 资源池不再指向 8110 的前提下，停 8110 不影响视频生成主流程。

但它可能仍被声音试听接口 h20_api_base 使用，也作为旧裸机回滚入口。停之前要确认 h20_api_base 和 t_comfyui_config 都没有指向 8110；否则会影响试听或回滚能力。
```

## 相关代码与配置

- `scheduler/collect_scheduler.py`
  - `config_value_audio` -> VoxCPM API base
  - `config_value` -> LatentSync API base
- `router/service/video_server2/voxcpm_tts.py`
  - 优先使用调度层传入的 `api_base`
  - 未传入时 fallback 到全局 `voxcpm_api_base`
- `router/crm_server.py`
  - `/crm/voice_clone_audition` 使用全局 `h20_api_base`
- `config/config-dev.json`
  - 本地仍保留 `h20_api_base` / `voxcpm_api_base` 指向 `8110`

## 相关记录

- [[projects/joying-bot-server/docs/h20-model-pool-ops-handoff-2026-06-02|h20-model-pool-ops-handoff-2026-06-02]]
- [[projects/joying-bot-server/changelog/h20-model-config-pool-routing-2026-06-02|h20-model-config-pool-routing-2026-06-02]]
- [[projects/joying-bot-server/changelog/h20-test-current-status-2026-06-03|h20-test-current-status-2026-06-03]]
