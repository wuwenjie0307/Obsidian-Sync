---
date: "2026-06-05"
tags: [h20, video-generation, task-check, bgm, voice-params]
---

# h20-recent-video-task-output-params-2026-06-05

## 查询背景

用户反馈 H20 测试服生成视频后 BGM 声音小。为排查最近任务是否传入了异常参数，查询 H20 测试服 `zhugedata_test.t_video_generate_task` 最近 8 条记录。

查询方式：

```sql
SELECT id, job_id, job_name, template_name, task_id, real_name, user_id, bot_id,
       task_status, progress, callback_status, fail_reason, generate_video_url,
       video_source_url, hot_video_audio_url, voice_file_url,
       voice_emotion, voice_speed, voice_volume,
       imagery_video, cover_image_url, cover_title,
       personal_intro, video_user_subtitle, video_user_desc,
       ai_rewritten_text, ai_rewritten_desc,
       created_time, updated_time, task_created_at, task_updated_at, finish_time
FROM t_video_generate_task
ORDER BY id DESC
LIMIT 8;
```

状态含义：

- `task_status=3`: 完成
- `task_status=4`: 失败
- `task_status=2`: 部分完成 / 处理中态

## 最近任务概览

| id | job_id | task_id | CRM 创建时间 | 状态 | 最终产出物 | BGM | voice 参数 | 素材/封面 |
|---|---:|---:|---|---|---|---|---|---|
| `1317` | `1114` | `1105` | 2026-06-05 17:43:44 | `2`, progress `0` | 未生成，`generate_video_url` 为空 | `调频/舒缓-城南花已开-new.mp3` | emotion `6`, speed `1.0`, volume `46` | 素材视频 `user4_1780637795609_4832260309e54bcb.mp4`; 封面标题：新手养狗别瞎踩坑！一年踩百坑掏心窝真话 |
| `1316` | `1113` | `1104` | 2026-06-05 17:37:15 | `3`, progress `100` | `https://videos-test.joyingai.cn/video/crm/20260605/user4_1780652413859_1223df6984e9f1a2.mp4` | `知识科普/舒缓-Sunrise.mp3` | emotion `6`, speed `1.0`, volume `46` | 素材视频 `user4_1780637795609_4832260309e54bcb.mp4`; 封面标题：狗子成精刷爆全网！这操作比人都聪明 |
| `1315` | `1112` | `1103` | 2026-06-05 16:43:21 | `3`, progress `100` | `https://videos-test.joyingai.cn/video/crm/20260605/user4_1780649191727_9d9f54350980b53f.mp4` | `知识科普/舒缓-Sunrise.mp3` | emotion `6`, speed `1.0`, volume `46` | 素材视频 `user4_1780637795609_4832260309e54bcb.mp4`; 封面标题：五一售楼处挤爆了！北京楼市真的回暖了 |
| `1314` | `1111` | `1102` | 2026-06-05 13:37:12 | `3`, progress `null` | `https://videos-test.joyingai.cn/video/crm/20260605/user4_1780637974437_b00f2c961420796a.mp4` | 无 BGM，`hot_video_audio_url` 为空 | emotion `1`, speed `1.0`, volume `50` | 素材视频 `user4_1780637795609_4832260309e54bcb.mp4`; 封面标题：房产中介日赚过万！这套获客法太好用 |
| `1313` | `1110` | `1101` | 2026-06-05 13:01:04 | `3`, progress `100` | `https://videos-test.joyingai.cn/video/crm/20260605/user4_1780635889150_68d8a0e42171d4be.mp4` | `调频/舒缓-Sunrise-new.mp3` | emotion `1`, speed `1.0`, volume `48` | 素材视频 `user4_1780623592227_1755053c4eb3edf0.mp4`; 封面标题：北京售楼处挤爆了！五一抢房都是真的 |
| `1312` | `1109` | `1100` | 2026-06-05 12:00:26 | `3`, progress `100` | `https://videos-test.joyingai.cn/video/crm/20260605/user4_1780632187743_0d06624659bc5d14.mp4` | `调频/舒缓-Sunrise-new.mp3` | emotion `1`, speed `1.0`, volume `48` | 素材视频 `user4_1780626793347_af9f11e734482cae.mp4`; 封面标题：房产中介躺赚获客！精准客源自动找上门 |
| `1311` | `1108` | `1099` | 2026-06-05 10:34:16 | `4`, failed | 未生成 | `调频/舒缓-城南花已开-new.mp3` | emotion `1`, speed `1.0`, volume `48` | 失败原因：上线前清理：历史卡住任务未生成视频，释放模型池资源 |
| `1310` | `1107` | `1098` | 2026-06-05 10:32:05 | `3`, progress `100` | `https://videos-test.joyingai.cn/video/crm/20260605/user4_1780626906600_c07b8f1f1c46fb71.mp4` | `调频/舒缓-城南花已开-new.mp3` | emotion `6`, speed `1.0`, volume `48` | 素材视频 `user4_1780623592227_1755053c4eb3edf0.mp4`; 封面标题：房产中介省出80%时间！客源自动找上门不用抢 |

## 参数观察

- 最近成功任务的 `voice_volume` 主要为 `46 / 48 / 50`，不是异常低值。
- 最近带 BGM 的任务主要使用：
  - `知识科普/舒缓-Sunrise.mp3`
  - `调频/舒缓-Sunrise-new.mp3`
  - `调频/舒缓-城南花已开-new.mp3`
- 最近任务的 `voice_file_url` 基本一致：`https://files.joyingai.cn/crm/20260605/user4_1780623654442_4faed475d8a851b1.mp3`
- `personal_intro` 基本一致：`关注我，带你寻找更优质的上海房产`

## 结论

从任务表看，BGM 声音小不像是前端传入了异常小的 `voice_volume`；`voice_volume` 控制的是声音克隆输出音量，不是 BGM 混音音量。更可疑的是 H20 后处理里的 BGM 自动混音策略，即 `router/service/video_server2/bge_add_video.py` 中 loudnorm 后又乘很小自动系数的问题。

相关修复记录：

- [[projects/joying-bot-server/bugs/h20-8100-runtime-stale-release-2026-06-05|h20-8100-runtime-stale-release-2026-06-05]]
- [[projects/joying-bot-server/changelog/h20-8100-runtime-refresh-2026-06-05|h20-8100-runtime-refresh-2026-06-05]]
