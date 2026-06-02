---
date: "2026-06-02"
tags: [changelog, h20, stage-output, voice-clone, latentsync, crm, video-generation]
---

# h20 视频生成阶段产物样例 task_id=998

## 背景

产品希望对比视频生成不同阶段的效果，尤其是：

- 音色克隆后的音频。
- 声音克隆 + 唇形同步完成后的视频。
- 最终成片。

本次从 h20 测试服已完成任务中提取阶段产物，未改代码，未重跑任务。

## 任务信息

```text
job_id=1007
task_id=998
任务完成时间：2026-06-01 18:58:28
最终视频时长：约 68 秒
```

## 原始输入

原始视频：

```text
https://files.joyingai.cn/crm/20260601/user4_1780302748155_727ccecc9a2d5725.mp4
```

原始音频：

```text
https://files.joyingai.cn/crm/20260601/user4_1780307339255_ccaaef4825238fb9.mp3
```

封面图：

```text
https://videos-test.joyingai.cn/video/crm/20260601/user4_1780310489036_2b5960259178989d.png
```

BGM：

```text
https://videos.joyingai.cn/video/crm/bgm/调频/舒缓-Sunrise-new.mp3
```

## 阶段产物

### 1. 音色克隆输出音频

日志说明：`音频克隆完成，音频链接为`。

```text
https://videos-test.joyingai.cn/video/crm/20260601/user4_1780310520578_43c7e135f9995a58.wav
```

验证结果：

```text
HTTP 200
WAV / mono / 48000 Hz
时长：68.000s
大小：约 6.3 MB
```

### 2. 声音克隆 + 唇形同步完成后的视频

这是 LatentSync 输出后，又做了尺寸/帧率标准化的视频；还没有进入字幕、BGM、封面阶段。

日志说明：`尺寸-帧率转换完成`，路径：`/tmp/latentsync_998_1780311479_916_30fps.mp4`。

```text
https://videos-test.joyingai.cn/video/crm/20260601/user4_1780311545683_768b2b9dcfee3dea.mp4
```

验证结果：

```text
HTTP 200
MP4
时长：68.067s
大小：约 15 MB
```

### 3. 字幕后的视频

日志说明：`混剪视频整体字幕添加完成`。

```text
https://videos-test.joyingai.cn/video/crm/20260601/user4_1780311558535_408ed88c82310616.mp4
```

验证结果：

```text
HTTP 200
MP4
时长：68.067s
大小：约 15 MB
```

### 4. BGM 后的视频

日志说明：`背景音乐添加完成`。

```text
https://videos-test.joyingai.cn/video/crm/20260601/user4_1780311562499_9eeeffc350646a51.mp4
```

验证结果：

```text
HTTP 200
MP4
时长：68.032s
大小：约 15 MB
```

### 5. 最终视频

日志说明：`任务执行完成，最终视频链接为`。

```text
https://videos-test.joyingai.cn/video/crm/20260601/user4_1780311568944_d73f6d0ec5a9a379.mp4
```

验证结果：

```text
HTTP 200
MP4
时长：68.566s
大小：约 15 MB
```

## 备注

当前代码会把临时文件加入 `tempfile` 列表，任务结束后删除本地临时文件。因此后续想稳定拿阶段产物，建议继续依赖 `get_url(...)` 上传后的 URL，或者临时加测试开关保留/记录阶段产物。

如果产品后续每次测试都需要这些阶段产物，建议加一个仅测试环境启用的配置，例如：

```json
{
  "debug_stage_outputs": true
}
```

开启后把下面字段写入日志或单独表：

```text
voice_clone_audio_url
lip_sync_video_url
subtitle_video_url
bgm_video_url
final_video_url
```
