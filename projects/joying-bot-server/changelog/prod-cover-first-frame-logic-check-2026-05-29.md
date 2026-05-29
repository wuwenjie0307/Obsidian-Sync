---
date: "2026-05-29"
tags: [changelog, production, cover, video-generation]
---

# 生产服封面首帧逻辑只读核查

## 改动类型

- [ ] 新功能
- [ ] Bug 修复
- [ ] 重构
- [x] 配置/状态核查

## 核查方式

在不影响生产服正常运行的前提下，只读查看 `222.71.55.27` 上 `/data/project/prod_ai_autodone/` 的代码：

- 使用 `ps` 查看生产进程。
- 使用 `grep`/`sed` 只读查看封面生成、视频生成调用链。
- 未重启、未写文件、未改配置、未操作 supervisor。

生产实例当前路径：`/data/project/prod_ai_autodone -> /data/project/prod_ai_autodone.20260521184129`
生产主进程：`app_autodone_cn.py --env cn_prod`，运行用户 `joying`。

## 结论

生产服当前就是“视频首帧生成封面图，再把封面图作为最终视频片头”的逻辑：

1. `router/crm_server.py` 的 `/generate_cover` 接口默认 `frame_index=0`，即视频第一帧。
2. `router/crm_server.py` 和 `scheduler/collect_scheduler.py` 在同步任务后，如果 `cover_image_url` 为空且 `imagery_video` 有值，会调用：
   `extract_frame(imagery_video_url, record.cover_title, frame_index=0, ...)`
3. 成功后写回 `record.cover_image_url`。
4. 生成视频时，`scheduler/collect_scheduler.py` 把 `task_record.cover_image_url` 传给：
   `video_work_Heygem_Whisper(..., First_frame_judge_url=task_record.cover_image_url)`
5. `router/service/video_server2/video_work.py` 要求 `First_frame_judge_url` 必填，并在封面合成阶段调用：
   `add_cover_to_video(video_path=video_path, image_path=First_frame_judge_url, task_id=task_id)`

## 对 h20 测试服的影响

h20 测试服应该保持与生产一致：

- 如果 CRM 已经有 `cover_image_url`，视频生成直接把它作为 `first_frame_judge_url`。
- 如果缺失，应先通过现有首帧封面流程从 `imagery_video` 取第 0 帧生成封面图片，再传给 `first_frame_judge_url`。
- `first_frame_judge_url` 必须是图片 URL，不能是视频 URL。
