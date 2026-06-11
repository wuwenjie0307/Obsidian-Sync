---
date: "2026-06-10"
project: joyingbot-new
type: doc
tags: [doc, ops, h20-test, video-tmp, voxcpm]
aliases: ["H20 video_tmp 多服务共用实查"]
---

# H20 video_tmp 多服务共用实查

## 图谱链接

- 项目: [[projects/joyingbot-new/00-项目概览|joyingbot-new]]
- 索引: [[projects/joyingbot-new/docs/00-docs-index|参考文档索引]]

## 背景

运维询问 compose 中 `/data/video_tmp:/data/video_tmp` 这个临时目录在启动多应用时是否会产生文件冲突。

## 结论

H20 实查结果：正常不会冲突。H20 当前多个模型服务已经共用 `TMPDIR=/data/video_tmp`，临时文件使用随机名，不是固定文件名。

对外简短口径：

> 看了 H20，现在多个服务就是共用 `/data/video_tmp`，临时文件是随机名，正常不会冲突。为了隔离更稳，多应用也可以各自挂不同子目录。

## 关键内容

- 实查主机：`hgx19`
- 当前 release：`/data/project/test_ai_botserver.20260610165052`
- VoxCPM 端口：`8120`、`8122`、`8124`、`8126`、`8128`、`8129`、`8130`、`8131`
- LatentSync 端口：`8121`、`8123`、`8125`、`8127`
- 上述服务进程环境均包含：`TMPDIR=/data/video_tmp`
- VoxCPM 服务代码使用：`tempfile.NamedTemporaryFile(delete=False, suffix=suffix)`，并在 finally 中 `os.unlink(ref_path)` 删除自己创建的临时文件。
- 调用端保存 VoxCPM 输出时使用：`voxcpm_clone_{uuid}.wav`，带随机 `uuid`。
- H20 上 `/data/video_tmp` 实际文件示例：`tmp75yigwki.mp4`、`tmpkrvr9dhs.wav`、`tmpm823wpup.mp4`，均为随机临时文件名。

## 相关文件

- `router/service/video_server/voxcpm_api.py`
- `router/service/video_server2/voxcpm_tts.py`
- `router/service/video_server2/video_tool.py`

## 相关记录

- [[projects/joyingbot-new/changelog/2026-06-10_voxcpm_huggingface_cache_migration|VoxCPM HuggingFace 缓存迁移口径]]
