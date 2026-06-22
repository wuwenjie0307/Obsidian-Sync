---
date: "2026-06-22"
project: "joying-bot-server"
type: doc
tags: [doc, git, release, h20, hyperframes, master-merge]
aliases: ["H20 master release merge risk 2026-06-22", "v6.3.3 vibevideo 与 v6.3.1 video_new 合 master 风险"]
---

# H20 master 发布合并风险排查 2026-06-22

## 图谱链接

- 项目: [[projects/joying-bot-server/00-项目概览|joying-bot-server]]
- 索引: [[projects/joying-bot-server/docs/00-docs-index|参考文档索引]]

## 背景

当前团队流程是：功能分支先合入 `test` 测试服，测试通过后再把对应功能分支合到 `master` 正式服。不能直接 `test -> master`，因为 `test` 可能已经包含其它尚未准备上线的测试功能。

本次排查目标是客观评估以下分支合入 `master` 的风险：

- `feature/ai_v6.3.3_vibevideo`
- `feature/ai_v6.3.1_video`
- `feature/ai_v6.3.1_video_new`

## 排查时远端引用快照

排查时间：2026-06-22，北京时间。

```text
origin/master                         3d20eb7e
origin/test                           b6d8b282
origin/feature/ai_v6.3.3_vibevideo    48f4a782
origin/feature/ai_v6.3.1_video        e12999ae
origin/feature/ai_v6.3.1_video_new    23e6e4c1
```

其中 `origin/test` 的 `b6d8b282` 已包含本次视频方向 Display Matrix 修复从 `feature/ai_v6.3.1_video_new` 合入 test 的结果。

## 核心结论

### 1. 不建议直接用老分支 `feature/ai_v6.3.1_video` 合 master

`feature/ai_v6.3.1_video` 单独合 `master` 时，`merge-tree` 没有文本冲突，但风险很高，因为它相对 `master` 包含非常多历史和其它测试分支内容：

```text
master...feature/ai_v6.3.1_video = 3 / 891
branch_only_vs_master = 891
master_only_vs_branch = 3
```

直接 diff 规模：

```text
95 files changed, 13483 insertions(+), 789 deletions(-)
```

实际 `merge-tree origin/master origin/feature/ai_v6.3.1_video` 结果规模：

```text
94 files changed, 13416 insertions(+), 681 deletions(-)
```

该分支历史里可以看到大量非单一功能合并记录，例如：

```text
Merge branch 'wecom_message' into test
Merge branch 'phone_activate_bug' into test
Merge remote-tracking branch 'origin/test' into feature/ai_v6.3.1_video
Merge branch 'feature-rt-v6.3.1-chat' into test
```

判断：这个分支不像干净的单功能分支，更像夹带了测试服历史的宽分支。直接合 `master` 虽然不一定冲突，但会违背“避免 test 未验证功能进入正式服”的发布策略。

### 2. `feature/ai_v6.3.3_vibevideo` 相对健康

`feature/ai_v6.3.3_vibevideo` 单独合 `master` 的形态较干净：

```text
master...feature/ai_v6.3.3_vibevideo = 0 / 39
branch_only_vs_master = 39
master_only_vs_branch = 0
merge-tree: 无文本冲突
```

实际合并结果规模：

```text
42 files changed, 18213 insertions(+), 22 deletions(-)
```

注意：该分支仍有 3 个提交在当前 `origin/test` 之后：

```text
48f4a782 fix: preserve disabled model pool configs
64098a83 fix: release skipped preassigned model configs
3738fbc3 fix: improve hyperframes subtitles and translation
```

发布前应确认这 3 个提交已在测试服验证，或先补合到 test 后再验。

### 3. `feature/ai_v6.3.1_video_new` 比老分支干净很多，但不是零风险

`feature/ai_v6.3.1_video_new` 单独合 `master`：

```text
master...feature/ai_v6.3.1_video_new = 4 / 79
branch_only_vs_master = 79
master_only_vs_branch = 4
merge-tree: 无文本冲突
```

直接 diff 规模：

```text
74 files changed, 9912 insertions(+), 758 deletions(-)
```

实际 `merge-tree origin/master origin/feature/ai_v6.3.1_video_new` 结果规模：

```text
71 files changed, 9839 insertions(+), 646 deletions(-)
```

判断：`_new` 比老的 `feature/ai_v6.3.1_video` 干净很多，更适合作为 H20 v6.3.1 相关正式发布来源。但它仍然包含 VoxCPM、LatentSync、Docker、旧视频链路、scheduler、CRM 等较多 H20 生产化改动，发布前需要专项回归。

## 两个推荐分支一起合 master 的冲突情况

本次重点模拟了这两个分支一起合入 `master`：

- `feature/ai_v6.3.3_vibevideo`
- `feature/ai_v6.3.1_video_new`

单独合 master 都没有文本冲突；但两个都进 master 时，无论顺序如何都会冲突。

模拟顺序 1：

```text
master -> feature/ai_v6.3.3_vibevideo -> feature/ai_v6.3.1_video_new
```

模拟顺序 2：

```text
master -> feature/ai_v6.3.1_video_new -> feature/ai_v6.3.3_vibevideo
```

两种顺序都冲突，冲突文件一致：

```text
common/json_util.py
router/crm_server.py
router/service/video_server2/video_work.py
scheduler/collect_scheduler.py
```

两个分支重叠改动文件共 5 个：

```text
common/json_util.py
pojo/models.py
router/crm_server.py
router/service/video_server2/video_work.py
scheduler/collect_scheduler.py
```

其中 `pojo/models.py` 可以自动合并，其余 4 个会产生内容冲突。

## 冲突文件风险说明

### `scheduler/collect_scheduler.py`

高风险文件。涉及：

- 视频任务调度
- 模型池预分配和释放
- old minimal 旧链路
- science_guide / video_diary HyperFrames 路由
- CRM 回调状态
- 失败时模型池释放保护

解冲突时要特别确认：

- minimal 旧链路不能被 HyperFrames 逻辑破坏。
- science_guide / video_diary 失败不能 fallback 到 minimal。
- 模型池释放仍在整条链路最终 cleanup 中执行。
- 已跳过或失败的预分配配置仍能释放。
- `templates_style_id` 路由规则保持：`1=science_guide`，`2=video_diary`，`3=minimal`。

### `router/service/video_server2/video_work.py`

高风险文件。涉及：

- VoxCPM 声音克隆
- HeyGem / LatentSync 口型合成
- source video 时长对齐
- BGM / cover / subtitle 旧链路
- HyperFrames 前置标准化产物
- orientation / Display Matrix 修复

解冲突时要保留：

- v6.3.1_new 的 VoxCPM / LatentSync / 时长对齐 / Display Matrix rotation 修复。
- v6.3.3 的 HyperFrames 标准化前置、失败处理和后处理接口。
- `return_standardized_result` 相关逻辑不能破坏旧链路返回值。

### `router/crm_server.py`

中高风险文件。涉及：

- CRM 视频任务接口
- 手动触发 / 查询任务
- HeyGem Whisper 任务状态
- callback / Redis 状态记录
- 可能的模板字段透传

解冲突时要确认功能字段不会互相覆盖或漏传。

### `common/json_util.py`

中风险文件。两个分支都碰到 JSON/LLM 输出清洗能力。

解冲突时要确认：

- HyperFrames 分析 JSON 清洗仍可处理 markdown fence / 非严格 JSON / 前后缀噪声。
- v6.3.1_new 里和 copywriting JSON unwrap / LLM JSON cleanup 相关逻辑仍保留。

## 推荐发布路径

不要直接在 GitLab 上连续点两个 MR 合 master。建议使用 release 分支做一次目标侧合并和冲突解决。

推荐流程：

```text
1. 从 origin/master 新建 release 分支
   release/h20-v633-v631new-to-master

2. 在 release 分支合入 feature/ai_v6.3.3_vibevideo

3. 在 release 分支合入 feature/ai_v6.3.1_video_new

4. 手动处理 4 个核心冲突文件：
   - common/json_util.py
   - router/crm_server.py
   - router/service/video_server2/video_work.py
   - scheduler/collect_scheduler.py

5. 跑专项回归和冒烟测试

6. release 分支验证通过后，再合入 master
```

推荐优先使用 `feature/ai_v6.3.1_video_new`，不要使用老的 `feature/ai_v6.3.1_video` 作为正式发布来源。

## 发布前建议回归清单

至少覆盖以下链路：

```text
old minimal 旧链路视频生成
science_guide HyperFrames 路由与后处理
video_diary HyperFrames 路由与后处理
科普指南字幕翻译
视频日记 BGM / 时长同步
模型池释放：成功、失败、跳过、异常
voice audition / VoxCPM 参数
source video 时长对齐
Display Matrix rotation metadata 清理
CRM callback status / generate_video_duration
混剪素材和非混剪素材过滤
```

建议测试命令至少包含：

```text
python -m unittest test.test_video_time_align_orientation test.test_video_quality_pipeline test.test_voice_speed_timeline_alignment
```

如果 release 分支包含 HyperFrames 相关变更，应再跑项目内已有 HyperFrames 相关测试，例如：

```text
python -m unittest test.test_template_route test.test_hyperframes_analysis test.test_hyperframes_cli test.test_hyperframes_postprocess test.test_hyperframes_upload_callback
```

实际测试命令以 release 分支当时存在的测试文件为准。

## 已验证/已观察到的具体命令结论

单独合 master 的 `merge-tree` 结论：

```text
feature/ai_v6.3.3_vibevideo -> master: 无文本冲突
feature/ai_v6.3.1_video -> master: 无文本冲突，但强烈不推荐直接合
feature/ai_v6.3.1_video_new -> master: 无文本冲突
```

组合合 master 的 `merge-tree` 结论：

```text
v6.3.3_vibevideo + v6.3.1_video: 冲突
v6.3.1_video + v6.3.3_vibevideo: 冲突
v6.3.3_vibevideo + v6.3.1_video_new: 冲突
v6.3.1_video_new + v6.3.3_vibevideo: 冲突
```

冲突核心文件：

```text
common/json_util.py
router/crm_server.py
router/service/video_server2/video_work.py
scheduler/collect_scheduler.py
```

## 相关文件

- `common/json_util.py`
- `router/crm_server.py`
- `router/service/video_server2/video_work.py`
- `scheduler/collect_scheduler.py`
- `pojo/models.py`

## 相关记录

- [[projects/joying-bot-server/docs/h20-hyperframes-test-merge-rules-2026-06-17|h20-hyperframes-test-merge-rules-2026-06-17]]
- [[projects/joying-bot-server/docs/h20-hyperframes-runtime-bundle-drill-2026-06-17|h20-hyperframes-runtime-bundle-drill-2026-06-17]]
- [[projects/joying-bot-server/docs/h20-hyperframes-template3-quote-migration-2026-06-18|h20-hyperframes-template3-quote-migration-2026-06-18]]
