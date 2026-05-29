---
date: "2026-05-29"
tags: [changelog, h20, cover, video-generation]
---

# h20 测试服封面首帧逻辑同步核查

## 改动类型

- [ ] 新功能
- [ ] Bug 修复
- [ ] 重构
- [x] 配置/状态核查

## 核查方式

按用户要求，在不影响 h20 测试服运行的前提下，只读查看 `/data/projects/joyingbot-new/`：

- 使用 `ps` 查看当前 Bot/VoxCPM/LatentSync 进程。
- 使用 `grep` 只读查找封面生成和视频生成调用链。
- 未重启服务、未改文件、未写配置。

## 结论

h20 当前代码已经与生产服封面首帧逻辑一致，不需要额外同步代码：

1. `router/crm_server.py` 存在 `/generate_cover` 接口，`frame_index` 默认 `0`，即第一帧。
2. `router/crm_server.py` 的异步处理逻辑在 `cover_image_url` 缺失且 `imagery_video` 存在时调用：
   `extract_frame(imagery_video_url, record.cover_title, frame_index=0, ...)`
3. `scheduler/collect_scheduler.py` 中也有同样的补封面逻辑：缺 `cover_image_url` 时从 `imagery_video` 抽第 0 帧生成并写回。
4. 生成视频时，`scheduler/collect_scheduler.py` 将 `task_record.cover_image_url` 作为：
   `First_frame_judge_url=task_record.cover_image_url`
5. `router/service/video_server2/video_work.py` 要求 `First_frame_judge_url` 必填，并在封面合成阶段调用：
   `add_cover_to_video(video_path=video_path, image_path=First_frame_judge_url, task_id=task_id)`

## 当前 h20 服务状态

只读检查时 h20 上相关进程存在：

- Bot：`app_server_api.py --env dev --jobStatus false --port 8100`
- VoxCPM：`voxcpm_api.py --port 8110`
- LatentSync：`latentsync_api.py --port 8101`

## 注意

测试服联调时仍需保证：

- `first_frame_judge_url` 传图片 URL。
- 如果只有视频 URL，应先走首帧封面生成流程得到 `cover_image_url`，再提交视频生成。
