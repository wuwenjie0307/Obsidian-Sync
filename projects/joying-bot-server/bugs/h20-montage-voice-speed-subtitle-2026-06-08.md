---
date: "2026-06-08"
status: open
severity: medium
tags: [bug, h20, video-generation, montage, subtitle, voice-clone]
---

# H20 混剪视频 3 倍速导致字幕体感跟不上

## 问题描述

产品反馈：新增音色克隆支持倍速后，普通视频在高倍速下字幕表现尚可，但一旦使用混剪，倍速过大时会出现“字幕跟不上说话速度”的体感问题。

样例视频：

`https://videos-test.joyingai.cn/video/crm/20260608/user4_1780913803580_cd97a6a907897907.mp4`

本次排查目标是确认测试服是否能看到该混剪视频任务、任务入参是多少，以及需要调整哪一层逻辑。

## 任务证据

测试库：`zhugedata_test`

`t_video_generate_task` 对应任务：

| 字段 | 值 |
|---|---|
| 本地任务 id | `1350` |
| `job_id` | `1156` |
| `task_id` | `1138` |
| `company_id / user_id` | `1 / 4` |
| `task_status / progress / callback_status` | `3 / 100 / 1` |
| `generate_source` | `2` |
| `video_category` | `0` |
| `voice_emotion` | `8` |
| `voice_speed` | `3.0` |
| `voice_volume` | `77` |
| `video_user_subtitle` 长度 | 约 `311` 字符 |
| `ai_rewritten_text` | `null` |
| 背景音乐 | 空 |
| 最终视频 | `https://videos-test.joyingai.cn/video/crm/20260608/user4_1780913803580_cd97a6a907897907.mp4` |

关键生成资源：

| 字段 | 值 |
|---|---|
| 参考音频 `voice_file_url` | `https://files.joyingai.cn/crm/20260605/user4_1780623654442_4faed475d8a851b1.mp3` |
| 形象视频 `imagery_video` | `https://files.joyingai.cn/crm/20260605/user4_1780637795609_4832260309e54bcb.mp4` |
| 封面图 `cover_image_url` | `https://videos-test.joyingai.cn/video/crm/20260608/user4_1780913632302_a2cb64299dd7d70f.png` |

`t_video_material_template` 对应混剪素材：

| 字段 | 值 |
|---|---|
| 素材本地 id | `697` |
| `material_id` | `628` |
| `material_type` | `1`，视频素材 |
| `material_duration` | `13` 秒 |
| `material_subtitle` 长度 | 约 `165` 字符 |
| `material_source_url` | `https://files.joyingai.cn/crm/20260608/user4_1780913606999_27616b0ab4a41de2.mp4` |
| `is_mix_material` | `1` |
| `is_lip_sync` | `0` |
| `sort_order` | `1` |

## 复现步骤

1. 创建视频生成任务，并选择混剪视频素材。
2. 设置音色克隆参数，尤其是较高 `voice_speed`，样例为 `3.0`。
3. 等待 H20 测试服生成视频完成。
4. 查看最终混剪视频，主观感受为字幕无法跟上高速口播。

## 期望行为

混剪视频在支持音色倍速的同时，字幕可读性、混剪覆盖窗口和口播速度应保持可接受的平衡。普通视频和混剪视频不应因为同一个高倍速参数产生明显不同的观看体验。

## 实际行为

样例任务中 `voice_speed=3.0`，混剪素材为 13 秒视频，但素材绑定文案约 165 字。高倍速压缩语音时长后，字幕时间窗和混剪覆盖时间窗都被压缩，视觉上出现字幕追不上说话速度的问题。

## 原因

这次不是“混剪素材没同步”的问题。素材已经存在于 `t_video_material_template`，且 `is_mix_material=1`。

直接原因是混剪场景允许了过高语速：

- `voice_speed=3.0` 原样进入 H20 视频生成链路。
- 字幕 ASS 是根据高倍速合成后的音频生成的，时间戳本身大概率是跟音频对齐的。
- 混剪素材的覆盖区间也是通过同一套字级时间戳从素材绑定文案中定位。
- 当 165 字素材文案被压缩到很短时间窗时，字幕虽然“同步”，但可读性不足，用户体感就是字幕跟不上。

普通视频没有混剪素材覆盖和素材绑定长文案这层视觉负担，因此同样的高倍速问题不明显。

## 解决方案

建议先做参数策略收口，而不是强行移动字幕时间轴：

1. 前端/CRM：当任务选择了混剪素材时，不提供 `3.0` 倍速选项，或提交前降级到 `2.0` / `1.5`。
2. 后端兜底：scheduler 在发现 `Montage_dict` 或 `Photo_dict` 非空时，对 `voice_speed` 做上限保护。
3. 推荐初始策略：混剪场景 `voice_speed > 2.0` 时降到 `2.0`；如果产品要求更稳，直接降到 `1.5`。
4. 增加 warning 日志：记录原始倍速、实际使用倍速、素材数量、素材文案长度和素材时长。
5. 不建议简单延长字幕显示时间；这会让字幕和真实语音发生真正的不同步。

## 优化点

- 按文案密度动态判断：例如 `material_subtitle_chars / material_duration` 超过阈值时自动限制倍速。
- 混剪任务增加生成前校验：长文案 + 短素材 + 高倍速时返回明确提示。
- 回归测试覆盖：混剪 + `voice_speed=3.0` 会被降速；普通视频 + `voice_speed=3.0` 不受影响。
- 日志中增加 `has_montage`、`voice_speed_original`、`voice_speed_effective`，便于后续直接定位。

## 环境信息

- 项目：`joying-bot-server` / `joyingbot-new`
- 本地工作区：`C:\Users\admin\Desktop\joyingbot-new`
- 测试库：`zhugedata_test`
- 表：`t_video_generate_task`、`t_video_material_template`
- 日期：2026-06-08
- 说明：本次 H20 SSH key 登录返回 `Permission denied (publickey,password)`，未使用密码登录；任务证据来自测试库只读查询。

## 相关文件

- `C:\Users\admin\Desktop\joyingbot-new\scheduler\collect_scheduler.py`
- `C:\Users\admin\Desktop\joyingbot-new\router\service\video_server2\video_work.py`
- `C:\Users\admin\Desktop\joyingbot-new\router\service\video_server2\video_select_overlay.py`
- `C:\Users\admin\Desktop\joyingbot-new\router\service\video_server2\voice_params.py`
- `C:\Users\admin\Desktop\joyingbot-new\router\service\video_server\voxcpm_api.py`
