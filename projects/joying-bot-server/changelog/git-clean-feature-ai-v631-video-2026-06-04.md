---
date: "2026-06-04"
tags: [changelog, git, branch, master, test, h20]
---

# Git 干净分支整理：feature/ai_v6.3.1_video

## 改动类型

- [ ] 新功能
- [ ] Bug 修复
- [x] 重构
- [x] 配置变更

## 背景

同事建议将近期 h20 / VoxCPM / 完整视频链路相关提交，从最新 `master` 重新拉出一条干净个人分支，再按 commit 时间从旧到新 cherry-pick 过去，避免直接从 `test` 或旧个人分支把其他人的未上线提交带入 `master`。

本次按该流程执行，未直接推送或合并到 `test` / `master`。

## 执行结果

- 基准分支：`origin/master`
- 基准提交：`5d57cbb5 update(config)`
- 新个人分支：`feature/ai_v6.3.1_video`
- 远端分支：`origin/feature/ai_v6.3.1_video`
- 最终 HEAD：`e61af89e fix: use cursor pagination for crm video lists`
- 新分支相对 `origin/master`：`51` 个提交
- 推送状态：已推送到 GitLab
- MR 创建链接：`http://git.joyingai.cn/services/crm.ai.joyingbot/-/merge_requests/new?merge_request%5Bsource_branch%5D=feature%2Fai_v6.3.1_video`

## cherry-pick 范围

从旧分支 `lucky-test/voxcpm-default-speed-prompt` 中，筛选 `伍文杰 <wuwenjie@joyingai.cn>` 相对 `origin/master` 多出的非 merge 提交，按旧到新 cherry-pick 到新分支。

本次跳过两个不适合搬入新分支的提交：

- `28c21844 chore: trigger merge request for feature/ai_v1_api_merge`
  - 原因：空提交 / MR 触发用途，没有实际代码改动。
- `4826469e fix: omit default VoxCPM speed prompt`
  - 原因：与已搬入的 `1f030117 fix: omit default VoxCPM speed prompt` 是同一修复的 clean 分支重复提交，避免重复冲突。

## 冲突处理记录

- `app_config/config.py`
  - 冲突原因：旧提交只新增少量 h20 配置 key，`master` 已有更多配置 key。
  - 处理：保留 `master` 侧完整配置列表，同时保留 h20 / VoxCPM / LatentSync 相关 key。

- `config/config-dev.json`
  - 冲突原因：旧提交新增 h20 / VoxCPM / LatentSync 服务地址，`master` 侧已有诸葛、短链、聊天服务等配置。
  - 处理：合并两侧非敏感结构，不记录具体敏感配置值；JSON 解析校验通过。

- `router/service/video_server2/video_work.py`
  - 冲突原因：文件末尾 `__main__` 本地样例块追加位置冲突。
  - 处理：保留旧提交样例块，删除冲突标记。

- `scheduler/collect_scheduler.py`
  - 冲突 1：`conf` import 与性能日志 helper 冲突。
    - 处理：两边都保留。
  - 冲突 2：性能日志包裹与恢复 Heygem 视频池逻辑冲突。
    - 处理：保留 `generate_total` 性能日志；同时恢复 Heygem 视频池行为，不实际传 `latentsync_api_base`，只保留 LatentSync 切换注释。

- `test/test_voxcpm_voice_style_prompt.py`
  - 冲突原因：旧测试输入括号内仍带 `自然语速`，新版策略不再默认拼接自然语速。
  - 处理：采用不带 `自然语速` 的新版测试输入。

## 验证结果

关键文件编译检查通过：

```text
python -m py_compile router/crm_server.py scheduler/collect_scheduler.py router/service/video_server/voxcpm_api.py router/service/video_server2/voxcpm_tts.py router/service/video_server2/video_work.py router/service/voice_audition_pool_service.py router/service/video_server2/voice_params.py
```

相关单测通过：

```text
python -m unittest test.test_voxcpm_voice_style_prompt test.test_scheduled_video_voice_params test.test_voice_clone_upload test.test_voice_audition_pool_service test.test_crm_video_cursor_pagination test.test_video_quality_pipeline test.test_video_perf_logging test.test_audio_conversion_ffmpeg_binary test.test_latentsync_timeout test.test_production_baseline_alignment
Ran 81 tests in 0.702s
OK
```

## 当前工作区备注

推送后，本地已跟踪文件无未提交改动。仍存在未跟踪项，未纳入本次分支：

```text
artifacts/
open-source-skills/
tmp_h20_8100_debug.py
```

## 后续流程建议

1. 先将 `feature/ai_v6.3.1_video` 合入 `test` 提测。
2. 测试通过后，用同一分支向 `master` 提 MR。
3. 若 GitLab 提示与 `master` 冲突，在个人分支本地 merge 最新 `origin/master` 解决冲突后再 push。
4. 不直接从 `test` 合并到 `master`，避免带入其他人未上线提交。

## 相关 Commit

- `5d57cbb5`：本次新分支基准 `origin/master`
- `e61af89e`：本次新分支最终 HEAD
- `feature/ai_v6.3.1_video`：已推送个人功能分支
