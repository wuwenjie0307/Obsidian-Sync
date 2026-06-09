---
tags: [project, h20, hyperframes, ai-prd, decision-record]
---

# H20 HyperFrames 网感视频 AI-PRD 不确定项与当前推荐答案

日期：2026-06-08
状态：待结合最新 `test` 分支代码复核

## 背景

当前 AI-PRD 的主方向已经明确：在 HeyGem/duix 标准化产物之后，按 `templates_style_id` 分流；`1/2` 进入 HyperFrames 网感后处理路线，`3` 保持原始旧路线。Whisper 在网感路线中只负责打轴，告诉 HyperFrames 动效字幕什么时候进场、什么时候消失；字幕视觉表现由 HyperFrames 动效逻辑负责。

## 当前推荐答案

| 问题 | 当前推荐选择 | 理由 |
|---|---|---|
| 模板 ID 是否固定 | 固定 `1=科普指南`、`2=视频日记`、`3=极简风格` | AI 分流最简单稳定，避免两套模板识别口径 |
| ID 不能固定怎么办 | CSM 额外返回稳定 `style_code`，只作为兜底校验 | 不优先引入第二主字段，避免联调复杂化 |
| 模板缺失/非法 | 未进入生成前默认 `3=minimal`；已进入 `1/2` 网感路线后不得回退 | 兼容历史任务，同时保证网感失败边界清晰 |
| Whisper 输入 | 从 HeyGem 标准化视频抽取音频，优先传音频 URL 给 8188 | Whisper 只需要音频；URL 更适合服务间调用；打轴必须基于成品音轨 |
| Whisper 职责 | 只打轴，不生成字幕样式和字幕动画 | 字幕表现由 HyperFrames 动效字幕图层负责 |
| 模型池释放 | 标准化视频服务端文件稳定可读并基础校验后释放 | 不让 Whisper、HyperFrames、上传拖住 VoxCPM/HeyGem 模型池 |
| HyperFrames 并发 | V1 做跨 scheduler 并发锁，默认并发 1 | 多进程 scheduler 下进程内锁不够，Chromium/Node 容易压垮机器 |
| 回调 payload | 沿用现网 payload，不主动新增模板字段 | 降低 CRM/CSM 协议变更；只需确认 `task_status/status` 口径 |
| 首帧提取失败 | 未提供确认兜底资源前按任务失败 | 封面是网感模板核心视觉，随意兜底可能验收不过 |
| BGM 下载失败 | 降级为无 BGM，记录 warning/fallback | BGM 是加分项，不建议因下载波动导致整条视频失败 |
| video_diary 复用范围 | 复用 diary 视觉风格和组件能力，不复用旧完整流程 | 避免把 watcher/旧字幕/旧 BGM/旧渲染链路带入新路线 |
| science_guide 设计稿 | 技术联调可先行，视觉验收必须等设计稿 | 避免后端因设计稿阻塞全部链路联调 |

## 待结合最新 test 分支复核的问题

1. `generateTaskList` 当前返回结构是否已有或能补齐 `templates_style_id`。
2. H20 同步任务入库逻辑是否已有模板字段扩展点。
3. HeyGem/duix 标准化产物的实际文件路径、URL、上传顺序和可读性校验位置。
4. 当前模型池锁释放逻辑在哪里，是否能拆到 HeyGem 后释放。
5. 8188 Whisper wrapper 当前到底接收音频 URL、视频 URL，还是服务端路径。
6. 当前 scheduler 是否多进程，HyperFrames 并发锁应落 DB、Redis 还是文件锁。
7. 当前回调代码实际使用 `task_status` 还是 `status`。
8. BGM 当前下载与合成失败如何处理。
9. 当前 diary 风格能力分布在哪些模块，哪些能复用到 HyperFrames 路线。

## 下一步

从 GitLab 拉取最新 `test` 分支完整项目后，基于现有代码复核以上推荐答案，判断是否需要调整 AI-PRD 的开发前确认项和推荐方案。

## 最新 test 分支代码复核结果（2026-06-08）

基于 GitLab `origin/test` 最新提交与 CRM apidoc 复核后，当前推荐答案需要做以下校准：

1. `templates_style_id` 已出现在 CRM 创建接口文档中，批量创建示例包含该字段；网感模板列表接口为 `/crm/agent/pc/video/templatesStyleList`，返回 `id/style_name/cover_url/sort/status`。
2. 最新 AI 后端代码尚未在 `t_video_generate_task` 模型中定义 `templates_style_id`，同步 `generateJobList/generateTaskList` 时也未落库该字段。
3. `generateTaskList` apidoc 返回示例暂未展示 `templates_style_id`，所以需要和 CRM 确认：AI 后端同步任务时从 Job 维度还是 Task 维度读取风格 ID。推荐优先从 Job 维度读取，Task 有值时可覆盖或校验一致性。
4. 现有视频生成函数 `video_work_Heygem_Whisper` 是完整旧链路：VoxCPM -> HeyGem/duix -> 标准化 -> Whisper/ASS -> 混剪 -> 烧字幕 -> BGM -> 封面 -> 上传。HyperFrames 新路线不宜直接调用到底，应拆出 HeyGem 标准化产物作为分叉点。
5. 当前模型池锁释放发生在 `_process_single_video_task_with_config` finally 中，也就是整个视频生成函数结束后才释放。HyperFrames 路线必须把释放点前移到 HeyGem 标准化视频产物稳定可读、完成基础校验之后。
6. 8188 Whisper wrapper 当前接口明确接收 `audio_url`、`language`、`word_timestamps`、`task_id`。现有字幕函数也是从视频抽音频、上传成 URL 后调用 8188，因此 HyperFrames 打轴推荐沿用该方式。
7. 当前完成回调使用 `/csm/agent/pc/video/generateTaskCallback`，payload 字段为 `task_status`、`progress`、`fail_reason`、`generate_video_source_url`、`generate_video_duration`；本地成功状态是 3，但回调成功状态映射为 7，失败映射为 -1。
8. 当前 BGM 处理失败会抛异常并导致任务失败；如果 PRD 选择 BGM 下载失败降级为无 BGM，这是新增策略，需要在 HyperFrames 路线单独实现并记录 warning/fallback。
9. 当前调度器会按可用模型配置数使用 ThreadPoolExecutor 并发处理任务；HyperFrames 渲染必须有独立并发锁，不能复用 `t_comfyui_config.is_active`，否则模型池释放后仍可能多个 Node/Chromium 渲染并发压垮机器。
10. 当前封面生成与任务生成前置依赖较强，调度条件要求 `cover_image_url` 和 `cover_title` 已有值；但网感模板要求 HyperFrames 视觉全接管封面，因此需要明确：网感路线可以只依赖个人形象视频，封面标题/封面图由 HyperFrames 路线内部生成，不应被旧调度条件卡住。

修正后的推荐方向：

- 模板字段用 `templates_style_id` 贴合现有 CRM 文档，不再优先引入 `video_style_template` 字符串字段。
- DB 字段建议为 `t_video_generate_task.templates_style_id INT DEFAULT 3`，必要时再保留 `style_code` 作为配置映射，不作为主分流字段。
- 分流点落在 scheduler 处理任务时：`1/2` 进入 HyperFrames 路线，`3/空/非法` 进入旧路线或生成前默认 3。
- HyperFrames 路线应新增一个“生成标准化 lip-sync 视频”的内部函数，返回本地路径、URL、时长、克隆音频 URL；模型池锁在该函数成功后释放。
- HyperFrames 后处理失败仍按任务失败处理，不回退旧路线。

## 最终决策补充（2026-06-09）

本节用于收口 2026-06-08 讨论中仍可能造成误读的两处口径。以下决策覆盖上文历史推荐项；历史内容保留为讨论轨迹，不作为 V1 执行口径。

### 模型池释放

最终决策：V1 继续沿用原始逻辑代码口径，整条视频生成链路完成或失败后，在最终 `finally` 释放 `t_comfyui_config` 模型池锁。

不采用“HeyGem 标准化视频产物稳定可读后提前释放模型池”的方案。该方案只保留为 V2 吞吐优化候选。

原因：

1. 保持现有调度语义一致，减少任务状态拆分风险。
2. HyperFrames 后处理仍属于本次任务完整生成链路。
3. V1 优先保证正确性、失败闭环和回调一致性。

### BGM 失败策略

最终决策：V1 按原始逻辑代码口径处理 BGM。

1. `hot_video_audio_url` 为空时，不加 BGM。
2. `hot_video_audio_url` 有值但下载失败时，任务失败，建议失败码 `BGM_DOWNLOAD_FAILED`。
3. `hot_video_audio_url` 有值但混音失败时，任务失败，建议失败码 `BGM_MIX_FAILED`。
4. 不静默降级为无 BGM。
5. 不从本地 BGM 目录随机选音频。

原因：用户显式配置 BGM 时，下载或处理失败应暴露为输入或处理异常；静默无 BGM 会造成产物和预期不一致，后续排查困难。

### 文档权威顺序

如历史记录与最终 PRD 冲突，按以下顺序执行：

1. `docs/h20-hyperframes-viral-template-ai-prd.md` 完整 PRD v0.4。
2. `docs/h20-hyperframes-viral-template-ai-prd-condensed.md` 提炼版。
3. `C:\Users\admin\Desktop\h20-hyperframes-development-order` 阶段拆解目录。
4. Obsidian 历史讨论记录。
