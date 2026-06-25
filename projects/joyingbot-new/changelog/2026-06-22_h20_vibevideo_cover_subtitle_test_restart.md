---
date: "2026-06-22"
project: "joyingbot-new"
type: changelog
tags: [changelog, h20, hyperframes, vibevideo, deployment, restart]
aliases: ["H20 网感封面字幕修复合入 test 与重启"]
---

# H20 网感封面字幕修复合入 test 与重启

## 图谱链接

- 项目: [[projects/joyingbot-new/00-项目概览|joyingbot-new]]
- 索引: [[projects/joyingbot-new/changelog/00-changelog-index|更新日志索引]]

## 改动类型

- [ ] 新功能
- [x] Bug 修复
- [ ] 重构
- [x] 配置/部署变更
- [ ] 文档

## 改动内容

- 修复网感封面标题文案过长时字号不随内容收缩的问题，避免封面文字越界。
- 去掉网感封面默认署名 `@狗头军师 - Jay`，避免所有用户封面都带固定作者名。
- 按产品截图红线要求统一两个网感视频模板的视频内字幕规格：
  - `template4.html` / `video_diary` 主字幕字号统一到 `58px`，强调字不再额外放大。
  - `template7.html` / `science_guide` 主字幕和核心字幕统一到 `58px`。
  - `universal.html` styled 字幕卡片位置统一抬到中下安全带，`bottom` 使用 `560px / 500px / 530px`，字号使用 `58px / 56px / 52px`。
  - `hyperframes-postprocess/index.js` fallback 路径同步字幕字号和位置，去掉 diary 的低位覆盖。
- 功能分支已合入远端 `test`，随后重启 H20 测试服务。

## 影响范围

- 影响 H20 网感视频 HyperFrames 后处理链路：`science_guide`、`video_diary` 的封面生成和视频内字幕展示。
- 不改旧 `minimal` 路线。
- 不改 CRM/CSM 回调 payload。
- H20 重启涉及测试环境服务端口：`8100`、`8017`、`18017`。

## 验证结果

### 本地提交与合并

- 功能分支: `feature/ai_v6.3.3_vibevideo_master_ready`
- 修复提交: `d2e2d1b5 fix: polish viral cover and subtitle rendering`
- 合入 test 的 merge commit: `e0564dfa Merge branch 'feature/ai_v6.3.3_vibevideo_master_ready' into test`
- 推送范围: `2a91f324..e0564dfa HEAD -> test`
- 无污染冲突检查：

```text
git merge-tree origin/test origin/feature/ai_v6.3.3_vibevideo_master_ready
8a4b5d1e831d74eabf115846a91452fc0441c80c
```

`merge-tree` 未输出冲突文件；合并方向为 `feature/ai_v6.3.3_vibevideo_master_ready -> test`，没有把 `test` 合回功能分支。

### 合入 test 前验证

```text
python -m unittest test.test_hyperframes_postprocess
Ran 29 tests in 29.033s
OK

python -m unittest test.test_cover_template_style
Ran 6 tests in 0.589s
OK

python -m py_compile hyperframes-postprocess/scripts/cover_gen.py
exit 0

node --check hyperframes-postprocess/index.js
exit 0
```

### H20 重启验证

- H20 主机: `hgx19`
- 当前 release 目录: `/data/project/test_ai_botserver.20260622202834`
- `/data/project/test_ai_botserver` 是 release symlink，不是 Git worktree；通过文件 marker 确认可运行目录已包含本次修复：
  - `hyperframes-postprocess/templates/template4.html:714 bottom: 560px`
  - `hyperframes-postprocess/templates/template7.html:841 bottom: 560px`
  - `hyperframes-postprocess/templates/universal.html:822 bottom: 560px`
  - `hyperframes-postprocess/templates/template4.html:699 font-size: 58px`
  - `hyperframes-postprocess/templates/template7.html:827 font-size: 58px`
  - `hyperframes-postprocess/templates/universal.html:846 font-size: 58px`
  - `hyperframes-postprocess/index.js:1569 font-size: 58px`
  - `hyperframes-postprocess/scripts/cover_gen.py` 中 `COVER_HANDLE` 默认读取为空字符串

重启后进程状态：

```text
ai_botserver      RUNNING pid 3274221, uptime 0:02:05
ai_botserver_sch  RUNNING pid 3274225, uptime 0:02:04

PORT 8100 PID 3274251 CWD /data/project/test_ai_botserver.20260622202834
CMD /data/server/anaconda3/envs/botserver/bin/python app_server_api.py --env=dev --jobStatus=false --port=8100

PORT 8017 PID 3274221 CWD /data/project/test_ai_botserver.20260622202834
CMD /data/server/anaconda3/envs/botserver/bin/python app_server_api.py --env=dev --jobStatus=false --port=8017

PORT 18017 PID 3274225 CWD /data/project/test_ai_botserver.20260622202834
CMD /data/server/anaconda3/envs/botserver/bin/python app_server_sch.py --env=dev --jobStatus=true --port=18017
```

健康检查：

```text
http://127.0.0.1:8100/status/check -> {"status":"ok"}
http://127.0.0.1:8017/status/check -> {"status":"ok"}
```

测试库摘要：

```text
DB_CONNECTED database=zhugedata_test
TASK_STATUS_COUNTS
[{"task_status": 2, "count": 2}, {"task_status": 3, "count": 741}, {"task_status": 4, "count": 412}]

ACTIVE_TASKS
[{"id": 1559, "job_id": 1398, "task_id": 1343, "task_status": 2, "progress": 0, "callback_status": 1, "fail_reason": "", "created_time": "2026-06-22 12:37:47", "updated_time": "2026-06-22 12:38:08"}, {"id": 1558, "job_id": 1397, "task_id": 1342, "task_status": 2, "progress": 0, "callback_status": 1, "fail_reason": "", "created_time": "2026-06-22 12:28:50", "updated_time": "2026-06-22 12:29:35"}]

MODEL_POOL_COUNTS
[{"config_key": "comfyui_url", "is_active": 0, "count": 12}, {"config_key": "comfyui_url", "is_active": 1, "count": 2}, {"config_key": "comfyui_url", "is_active": 2, "count": 2}, {"config_key": "voice_audition_url", "is_active": 0, "count": 1}, {"config_key": "voice_audition_url", "is_active": 1, "count": 3}]
```

说明：重启后仍有 2 个 `task_status=2` 的视频任务和 2 个 `comfyui_url is_active=2` 的模型池占用，需结合任务 `1342/1343` 后续日志判断是否正常推进或需要单独处理。

## 相关文件

- `hyperframes-postprocess/scripts/cover_gen.py`
- `hyperframes-postprocess/templates/template4.html`
- `hyperframes-postprocess/templates/template7.html`
- `hyperframes-postprocess/templates/universal.html`
- `hyperframes-postprocess/index.js`
- `test/test_cover_template_style.py`
- `test/test_hyperframes_postprocess.py`

## 相关记录

- 用户反馈：网感封面默认署名不应固定为 `@狗头军师`。
- 用户反馈：两个网感视频字幕应按截图红线统一变小并上移。
- H20 测试环境重启命令路径通过 jump host 登录执行，未在笔记中记录任何密码或数据库凭据。

## 相关 Commit

- `d2e2d1b5 fix: polish viral cover and subtitle rendering`
- `e0564dfa Merge branch 'feature/ai_v6.3.3_vibevideo_master_ready' into test`
