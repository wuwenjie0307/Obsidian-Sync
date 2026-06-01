---
date: "2026-06-01"
tags: [changelog, h20, video-generation, crm]
---

# h20 视频生成主链路验证通过

## 改动类型

- [x] bug fix
- [x] config change
- [x] deployment verification

## 改动内容

- h20 字幕 Whisper 链路对齐生产底座，Bot 通过独立 8188 Whisper 服务进行转写。
- h20 8188 Whisper 服务切到 GPU 可用的 `joyingbot` 环境。
- 修复并验证调度锁释放逻辑，旧卡住任务已落失败态。
- `job_id=947/task_id=938` 验证通过完整视频生成链路：声音克隆、唇形同步、字幕、BGM、封面、上传、CRM 回调。

## 影响范围

- h20 测试服视频生成链路。
- 不涉及生产服写操作。
- 不涉及 Git 提交或推送。

## 验证结果

- Bot 健康检查：`8017`、`8100` 返回 `{"status":"ok"}`。
- VoxCPM：`8110/health` 返回 `{"status":"ok"}`。
- LatentSync：`8101/health` 返回 `{"status":"ok"}`。
- Whisper：`8188` 监听正常，日志显示 `绑定设备: cuda:0`。
- 最终视频：`https://videos-test.joyingai.cn/video/crm/20260601/user4_1780285072136_5a3d99f701e49b4d.mp4`

## 遗留问题

- LatentSync 单任务耗时较长，主要慢在子进程启动、模型加载、视频预处理/后处理和输出合成。
- h20 多个模型进程集中在 GPU0，建议后续按服务拆 GPU。
- 测试库历史待处理任务较多，可能影响产品新任务排队。
- 发布服务 `127.0.0.1:8015` 未连通，发布阶段失败；视频生成和 CRM 结果回调已成功。

## GitLab 同步

- 2026-06-01 已将本次 h20 视频生成链路修复提交并推送到 GitLab `test` 分支。
- 提交：`25536f9b fix: align h20 video generation with production baseline`
- 本次未推送 `master`。

## LatentSync 产品试测参数

- 2026-06-01 已确认 h20 当前 LatentSync 1.6 底层不支持 `lips_expression` 参数，只支持 `inference_steps` 和 `guidance_scale`。
- 为配合产品试测“嘴型强度”效果，h20 测试服 LatentSync API 默认值已调整为：
  - `inference_steps=30`
  - `guidance_scale=2.0`
- h20 当前运行目录 `/data/projects/joyingbot-new` 和 Jenkins 部署目录 `/data/project/test_ai_botserver` 的 `router/service/video_server/latentsync_api.py` 均已同步。
- LatentSync API `8101/health` 已验证返回 `{"status":"ok"}`。
- GitLab `test` 分支已同步提交：`a49c0afe fix: tune latentsync trial defaults`。
