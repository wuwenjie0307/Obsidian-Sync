---
date: "2026-06-01"
tags: [changelog, h20, video-generation, latentsync, ffmpeg]
---

# h20 视频画质保持参数调整

## 改动类型

- [x] Bug 修复
- [x] 配置变更
- [x] 测试
- [x] 部署验证

## 改动内容

- GitLab `test` 分支已合并并推送视频画质修复。
- LatentSync API 默认 `guidance_scale` 从旧值调整为 `1.8`。
- 视频进入 LatentSync 前恢复 HDR -> SDR 条件转换，避免 HDR 输入直接进入唇形同步造成色彩/曝光漂移。
- 关键 ffmpeg 二次编码默认改为更高质量的 `crf=18`：
  - HDR -> SDR 转换
  - 9:16 标准化
  - 横屏转竖屏
- 新增视频画质管线源码级回归测试，防止参数回退。
- h20 上 `ai_botserver_sch` 已重启到当前部署目录 `/data/project/test_ai_botserver.20260601202651`。

## 影响范围

- 影响 h20 测试服视频生成链路中的唇形同步前处理和后续标准化编码质量。
- 不影响 `master`，未推送生产分支。
- 不会消除 LatentSync 生成式重绘本身带来的全部人脸细节差异，但会降低 ffmpeg 后续多次重编码造成的额外画质损失。

## 相关 Commit

- `a0820871 fix: preserve h20 video quality defaults`
- `0d7e9021 merge h20 video quality preserve into test`
