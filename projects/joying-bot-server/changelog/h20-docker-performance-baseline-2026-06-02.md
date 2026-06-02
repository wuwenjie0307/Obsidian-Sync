---
date: "2026-06-02"
tags: [changelog, h20, docker, performance, latentsync, video-generation]
---

# h20 Docker 与裸机视频生成耗时对比 2026-06-02

## 背景

h20 测试服当前已经把 Bot 模型调用切到 Docker 旁路服务：

```text
VoxCPM Docker: http://127.0.0.1:8120
LatentSync Docker: http://127.0.0.1:8121
```

产品测试开始关注完整视频生成耗时，需要和之前 h20 裸机模型服务做对比。

## 当前对比结论

当前 Docker 链路能端到端跑通，但性能还没有优化到裸机水平。

粗略结论：

```text
Docker 链路：1 分钟左右视频完整生成约 35-40 分钟
裸机链路：1 分钟左右视频完整生成约 18-20 分钟
```

即当前 Docker 链路大约比之前裸机链路慢 1.7-2 倍。

## 已记录样本

| 链路 | 样本任务 | 视频时长 | 完整处理耗时 | 说明 |
|---|---:|---:|---:|---|
| 裸机 `8110/8101` | `task_id=996` | 约 69 秒 | 约 18-19 分钟 | 17:01 左右领取任务，17:20 完成 |
| 裸机 `8110/8101` | `task_id=998` | 约 68 秒 | 音频完成到最终成片约 17.5 分钟 | 阶段产物已记录 |
| Docker `8120/8121` | `task_id=1025` | 约 84 秒 | 约 39 分钟 | 12:27 开始处理，13:06 最终成功 |
| Docker `8120/8121` | `task_id=1024` | 未完整成功 | 超过旧 1800 秒超时 | 已将超时默认调整到 7200 秒 |
| 裸机早期直测 | 测试脚本 | 约 3.4 秒 | 67.5 秒 | 只测 VoxCPM + LatentSync，不含 CRM 完整链路 |
| Docker 直测 | 短视频样本 | 约 3.6 秒 | 135 秒 | 只测 LatentSync Docker |

注意：以上不是严格同素材 A/B，同步结论只能说明当前趋势。后续要做严谨性能对比，需要使用同一份视频、同一份音频、同一组参数分别跑裸机和 Docker。

## 主要慢点判断

1. LatentSync 是主要瓶颈，VoxCPM 一般在几十秒到 1 分钟左右。
2. Docker 运行环境和裸机不一致：

```text
裸机：Python 3.10.20 + Torch 2.5.1+cu121 + conda latentsync
Docker：Python 3.11.14 + Torch 2.9.1+cu128 + /opt/latentsync-venv
```

3. 当前 LatentSync 每次任务仍会启动推理子进程并加载模型，不是常驻预热模型服务。
4. 当前默认参数较重：`inference_steps=30`、`guidance_scale=1.8`。
5. 视频越长，LatentSync 推理、ffmpeg 合成、字幕/BGM/封面/上传都会变慢。
6. Docker 当前只是服务化验证形态，还没完成生产式模型池和性能调优。

## 下一步

优先执行：把 Docker 环境尽量对齐裸机环境。

目标：

```text
Python: 3.10.x
Torch: 2.5.1 + CUDA 12.1/12.x，优先对齐裸机 cu121
LatentSync: 继续使用 1.6 checkpoints
API 参数：继续保留 inference_steps=30、guidance_scale=1.8、7200 秒超时
```

后续再做：

1. 用同素材做 Docker 与裸机严格 A/B。
2. 给 LatentSync 增加阶段耗时日志。
3. 评估模型常驻，减少每次任务重新加载模型的开销。
4. 继续改造为按 `t_comfyui_config.config_value_audio/config_value` 调用模型池地址。
