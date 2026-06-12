---
date: "2026-06-12"
project: joyingbot-new
type: changelog
tags: [changelog, video, montage, ffmpeg, test-server, 3090]
aliases: ["视频方向元数据清理修复"]
---

# 视频方向元数据清理修复

## 图谱链接

- 项目: [[projects/joyingbot-new/00-项目概览|joyingbot-new]]
- 索引: [[projects/joyingbot-new/changelog/00-changelog-index|更新日志索引]]
- 运行手册: [[projects/joyingbot-new/docs/2026-06-12_3090_test_server_runbook|3090 测试服运行手册]]

## 改动类型

- [x] Bug 修复
- [ ] 新功能
- [ ] 重构
- [ ] 配置变更
- [ ] 文档

## 改动内容

修复混剪素材方向归一化后仍残留 `rotate=90` metadata 导致任务失败的问题。

现场失败任务：

```text
job_id=1227
task_id=1200
错误: orientation bake output still has rotation metadata
path=/tmp/tmp_ia7axxt_oriented.mp4
size=1080x1920
rotate=90
```

修复逻辑：

- `normalize_video_orientation()` 仍先用 `transpose=1/2` 烘焙像素方向。
- 新增 `_ensure_orientation_bake_output()`：如果输出像素已经是竖屏，但 ffprobe 仍读到 `rotate != 0`，则调用 `_clear_rotation_metadata()` remux 一次。
- remux 命令使用 `-map_metadata -1 -metadata:s:v:0 rotate=0 -c copy`，避免重新编码。
- remux 后继续走 `_validate_orientation_bake_output()`，如果仍有旋转元数据或像素方向不对，继续抛错。

## 影响范围

- 影响文件：`router/service/video_server2/video_time_align.py`
- 回归测试：`test/test_video_time_align_orientation.py`
- 影响链路：3090 测试服 scheduler 处理混剪视频/图片素材时的方向归一化。
- 不涉及 VoxCPM 音色容器；部署后只需要重启 `ai_botserver_sch` 让 scheduler 加载新代码。

## 验证结果

本地验证：

```bash
python -m unittest test.test_llm_json_cleanup test.test_video_time_align_orientation test.test_voxcpm_voice_style_prompt
```

结果：

```text
Ran 35 tests in 0.059s
OK (skipped=2)
```

合并验证：

```text
个人分支 feature/ai_v6.3.1_video 已合入最新 origin/test，无冲突。
test 分支已推送到 GitLab。
远端 feature/ai_v6.3.1_video 与 test 均指向 2019a93c4445b8195a3c2cf327367b7859604542。
```

## 相关文件

- `router/service/video_server2/video_time_align.py`
- `test/test_video_time_align_orientation.py`

## 相关记录

- [[projects/joyingbot-new/docs/2026-06-12_3090_test_server_runbook|3090 测试服运行手册]]

## 相关 Commit

- `284527b1 fix: clear baked video rotation metadata`
- 远端合并后提交位置：`2019a93c4445b8195a3c2cf327367b7859604542`
