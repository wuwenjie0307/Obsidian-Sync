---
date: "2026-06-05"
status: fixed
severity: medium
tags: [bug, h20, crm, video, voice-clone]
---

# H20 8100 CRM 视频任务语音表现参数未传入

## 问题描述

CRM 测试 H5 的“个人形象 - 语音表现”里有 `voice_emotion`、`voice_speed`、`voice_volume` 三个音色克隆参数，但创建实际视频任务后，H20 侧任务仍使用默认值。

## 复现步骤

1. 在 CRM H5 个人形象里设置语音表现参数。
2. 从视频生成页创建新视频任务。
3. 查看 CRM 任务列表或 H20 `t_video_generate_task` 中的新任务参数。

## 期望行为

创建视频任务时，语音表现参数应随任务传入后端，并进入 H20 实际视频任务。

## 实际行为

实际视频任务中仍是默认值：`voice_emotion=1`、`voice_speed=1`、`voice_volume=50`。

## 原因

H20 后端最新代码已支持解析并写入三参数，`router/crm_server.py` 中会调用 `parse_voice_clone_params(task)` 并写入 `record.voice_emotion`、`record.voice_speed`、`record.voice_volume`。

根因在 CRM H5 创建视频任务请求：个人形象页保存/试听已带三参数，但视频生成页调用 `/crm/agent/pc/video/generateJobUserCreate` 时，payload 只带了 `voice_file_url`、`personal_intro`，缺少 `voice_emotion`、`voice_speed`、`voice_volume`。上游没传，H20 只能使用默认值。

## 处理结果

- 已重启 H20 `8100`。
- 重启前 `8100` 运行目录：`/data/project/test_ai_botserver.20260604185023`。
- 重启后 `8100` 运行目录：`/data/project/test_ai_botserver.20260604205503`。
- 进程命令：`app_server_api.py --env=dev --jobStatus=false --port=8100`。
- 验证 `/status/check` 返回 `200 {"status":"ok"}`。
- 验证 `/crm/generate_video_task` 空 body 返回 `400 job_id 不能为空`。
- 验证旧实时接口 `/crm/submit_heygem_whisper_video_task` 返回 `410`。

## 解决方案

前端在 `/crm/agent/pc/video/generateJobUserCreate` 请求体中补传：

```js
voice_emotion: Number(profile?.voice_emotion ?? 1),
voice_speed: Number(profile?.voice_speed ?? 1),
voice_volume: Number(profile?.voice_volume ?? 50),
```

值从 `userProfileInfo` 或当前个人形象 profile 对象里取，和 `voice_file_url`、`personal_intro` 同源。

## 前端反馈话术

H20 8100 已重启到最新代码，后端已支持 `voice_emotion`、`voice_speed`、`voice_volume` 三个语音表现参数。现在问题在前端创建视频任务时没传这三个字段：个人形象页保存/试听有传，但 `generateJobUserCreate` 的 payload 里缺这三项，导致后端只能用默认值 `1/1/50`。请在 `/crm/agent/pc/video/generateJobUserCreate` 请求体里补上传参，值从 `userProfileInfo` / 当前个人形象 profile 中取。

## 环境信息

- 环境：H20 测试服 `hgx19`
- 端口：`8100`
- 分支：`merge-check/ai_v6.3.1_video-to-test`
- 本地仓库：`C:\Users\admin\Desktop\joyingbot-new-h20-model-pool-productionize`

## 相关文件 / 接口

- H20：`/data/project/test_ai_botserver/router/crm_server.py`
- CRM 创建任务接口：`/crm/agent/pc/video/generateJobUserCreate`
- H20 生成接口：`/crm/generate_video_task`
- CRM H5 路径：`/h5/#/video/generated`

## 2026-06-05 二次核查：generateTaskList 参数已在 H20 实际任务中生效

### 口径修正

前面判断前端 `/crm/agent/pc/video/generateJobUserCreate` 少传参数不准确。张建国确认后，正确流程是：H20 不关心创建视频任务写接口，只消费 CRM 的 `/csm/agent/pc/video/generateTaskList` 任务列表；创建任务时 CRM 会默认从个人形象取参数。

本次修复点是 H20 同步任务列表时，要把 `generateTaskList` 返回的 `voice_emotion`、`voice_speed`、`voice_volume` 落到 `t_video_generate_task`，后续生成时从本地任务表带给 VoxCPM。

### 代码与分支状态

- 个人分支：`merge-check/ai_v6.3.1_video-to-test`
- 修复提交：`83d22986 fix: sync crm task voice params`
- 已合并到远端 `test`
- `origin/test` 最新确认提交：`d0919006`
- 涉及文件：
  - `router/crm_server.py`
  - `scheduler/collect_scheduler.py`

### H20 运行状态

已登录 H20 `hgx19` 核查并处理：

- 发现 `8100` API 一开始还在旧目录 `/data/project/test_ai_botserver.20260604205503`。
- 已重启 `8100` 到最新目录。
- 当前三个进程都跑在同一个最新目录：`/data/project/test_ai_botserver.20260605105110`
  - `8100`：`app_server_api.py --env=dev --jobStatus=false --port=8100`
  - `8017`：`app_server_api.py --env=dev --jobStatus=false --port=8017`
  - `18017`：`app_server_sch.py --env=dev --jobStatus=true --port=18017`
- `8100 /status/check` 返回 `{"status":"ok"}`
- `8017 /status/check` 返回 `{"status":"ok"}`

线上代码检查通过：

- `router/crm_server.py`：存在 `parse_voice_clone_params(task)` 和 `record.voice_emotion = voice_params["voice_emotion"]`
- `scheduler/collect_scheduler.py`：存在同步落库逻辑，并且生成时传：
  - `voice_emotion=task_record.voice_emotion or 1`
  - `voice_speed=float(task_record.voice_speed or 1.0)`
  - `voice_volume=int(task_record.voice_volume if task_record.voice_volume is not None else 50)`
- `router/service/video_server2/voxcpm_tts.py`：VoxCPM 请求体包含：
  - `voice_emotion`
  - `voice_speed`
  - `voice_volume`

### 实际任务核查

查询 `zhugedata_test.t_video_generate_task`，已看到非默认参数进入实际任务：

| task_id | 状态 | voice_emotion | voice_speed | voice_volume | 最终视频 |
|---|---:|---:|---:|---:|---|
| 1095 | 已完成 | 3 | 1.5 | 63 | https://videos-test.joyingai.cn/video/crm/20260605/user4_1780626225315_2c12e4e35f2396cb.mp4 |
| 1096 | 已完成 | 4 | 1.0 | 48 | https://videos-test.joyingai.cn/video/crm/20260605/user4_1780626769680_72b6aa5c04e4b204.mp4 |
| 1097 | 已完成 | 2 | 1.0 | 48 | https://videos-test.joyingai.cn/video/crm/20260605/user4_1780626786740_bd0212ba46928b88.mp4 |
| 1098 | 已完成 | 6 | 1.0 | 48 | https://videos-test.joyingai.cn/video/crm/20260605/user4_1780626906600_c07b8f1f1c46fb71.mp4 |
| 1099 | 部分完成 | 1 | 1.0 | 48 | 暂无 |

原始参考音频，以上任务共用：

`https://files.joyingai.cn/crm/20260605/user4_1780623654442_4faed475d8a851b1.mp3`

共同个人介绍：

`关注我，带你寻找更优质的上海房产`

共同字幕主体：

`第一，帮你主动做个人获客：你可以搭建自己专属的私域云门店推广获客，发房源、更楼盘、推资讯、答问题全都能搞定，还能直接给房源拍短视频、录口播解说，靠专业内容攒粉塑IP，客源自动找上门。 第二，匹配客源精准又省心：平台会分析千万购房用户的找房偏好，给你精准推送意向潜客，抢客还有人工双重兜底，购房者的需求、预算一目了然，你完全可以按需挑选，不瞎浪费时间。 第三，找房源全量还极速：每天处理28亿次数据，全渠道的二手房能一键搜全，全网新房实时更新还能直接认领，不管是业主直放房源，还是跨公司的竞品房源，都能轻松拿到，效率直接拉满。`

### 产物说明

- 表里保留了最终视频 URL 和原始参考音频 URL。
- 克隆后的中间音频文件 URL 没有单独落库，日志里也没有找到可直接复用的独立音频 URL。
- 因此试听对比建议直接听最终视频；如果后续需要单独试听克隆音频，建议在 VoxCPM 调用完成后把中间音频 URL 或本地路径记录到任务表/日志。

### 当前结论

问题在代码和 H20 运行态上已处理：`generateTaskList` 返回的三个语音表现参数已经能进入 H20 本地任务表，并且当前运行代码会在生成时传给 VoxCPM。已有完成任务中可以看到非默认参数和最终视频产物。
