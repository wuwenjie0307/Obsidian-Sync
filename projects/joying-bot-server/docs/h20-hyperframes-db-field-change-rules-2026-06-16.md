---
date: 2026-06-16
project: joying-bot-server
type: doc
tags: [h20, hyperframes, database, schema, apidoc, test-env]
aliases: [H20 网感视频数据库字段变更规则, HyperFrames 字段迁移规则]
---

# H20 网感视频 / HyperFrames 数据库字段变更规则

## 背景

本记录用于约束当前 H20 网感视频 / HyperFrames 链路的字段依据、表结构变更和测试库操作规则。

适用范围：
- 功能分支：`feature/ai_v6.3.3_vibevideo`
- 测试集成方向：`feature/ai_v6.3.3_vibevideo -> test`
- 正式合并方向：`feature/ai_v6.3.3_vibevideo -> master`
- 主要本地表：`t_video_generate_task`

核心原则：任何测试库或生产库 schema 变更，都必须先有依据、先只读核对、再经用户明确确认；不能因为代码里“看起来需要”就直接改表。

## 已确认的外部接口依据

### `templates_style_id`

结论：`templates_style_id` 是 V1 主分流字段，属于真正需要落到本地任务表的字段。

依据：
- CRM apidoc 接口 `699`：`/crm/agent/pc/video/generateJobBatchCreate` 入参示例包含 `templates_style_id`。
- CRM apidoc 接口 `701`：`/crm/agent/pc/video/generateJobUserCreate` 入参示例包含 `templates_style_id`。
- CSM apidoc 接口 `712`：`/csm/agent/pc/video/generateTaskList` 返回示例包含 `templates_style_id`。
- CRM apidoc 接口 `2335`：`/crm/agent/pc/video/templatesStyleList` 返回网感模板列表字段 `id/style_name/cover_url/sort/status`。
- Obsidian 决策记录明确：`templates_style_id` 是 V1 主分流字段；`1=science_guide`，`2=video_diary`，`3=minimal`。

当前建议字段：

```sql
ALTER TABLE t_video_generate_task
ADD COLUMN templates_style_id INT NOT NULL DEFAULT 3 COMMENT '1=science_guide,2=video_diary,3=minimal';

CREATE INDEX idx_video_generate_task_templates_style_id
ON t_video_generate_task(templates_style_id, task_status);
```

### 回调字段

结论：HyperFrames V1 不主动新增模板字段到回调 payload；继续沿用现网回调口径。

依据：
- CSM apidoc 接口 `713`：`/csm/agent/pc/video/generateTaskCallback` 文档示例写的是 `status`。
- 现网 H20 代码和既有决策记录中实际回调用的是 `task_status`。
- 当前 V1 决策：继续发送 `task_status`，成功映射为 `7`，失败映射为 `-1`；如果 CSM/CRM 明确要求兼容 `status`，再评估双字段兼容，不能直接替换或删除 `task_status`。

## 内部链路字段：必须区分“业务必需”和“观测/恢复字段”

以下字段不是 apidoc 要求的对外字段，而是 H20 后端内部链路阶段产物字段。是否落库，需要结合当前代码实现、排查需要、表宽风险和用户确认决定。

### Whisper 阶段

候选字段：

```text
whisper_timeline_path
whisper_timeline_ms
```

用途：
- 记录 Whisper timeline JSON 路径。
- 记录 Whisper 打轴耗时。
- 当前开发文档阶段 03 要求记录 `whisper_timeline_path`、耗时和失败原因。

注意：如果 ORM `VideoGenerateTask` 定义了该字段，而数据库表缺少该字段，部署后普通 ORM 查询也可能失败。因此“代码定义字段”和“数据库存在字段”必须匹配。

### 结构化分析阶段

候选字段：

```text
analysis_path
analysis_ms
```

用途：
- 记录 HyperFrames structured analysis JSON 路径。
- 记录结构化分析耗时。
- 当前阶段 04/05 文档中，`analysis_path` 会被后续 CLI manifest 引用。

注意：这不是外部接口字段；若保留落库，推荐使用不会增加 MySQL 行内宽度压力的类型，并在改表前先做表宽评估。

### HyperFrames CLI / 渲染阶段

候选字段：

```text
hf_manifest_path
hf_result_path
hf_final_video_path
hf_cover_path
hf_subtitle_timeline_path
hf_render_ms
```

用途：
- 记录 manifest、result、本地最终视频、本地封面、本地字幕 timeline 路径。
- 记录渲染耗时。
- 便于排查、恢复、复现渲染问题。

注意：这些字段是内部观测/恢复字段，不是 apidoc 要求回传字段。

### 上传结果阶段

候选字段：

```text
hf_final_video_url
hf_cover_url
```

用途：
- 记录 HyperFrames 上传后的最终视频 URL 和封面 URL。
- 当前代码同时会把最终视频和封面写回现有业务字段：`generate_video_url`、`cover_image_url`，用于沿用原成功回调和后续发布逻辑。

注意：外部回调仍沿用现有字段，不新增 `hf_*` 字段到 callback payload。

## 当前测试库状态（2026-06-16 只读核对）

测试库：`zhugedata_test`

表：`t_video_generate_task`

当前已存在字段：

```text
templates_style_id INT NOT NULL DEFAULT 3
whisper_timeline_path VARCHAR(1000) NULL
whisper_timeline_ms INT NULL
```

当前已存在索引：

```text
idx_video_generate_task_templates_style_id(templates_style_id, task_status)
```

当前缺失字段：

```text
analysis_path
analysis_ms
hf_manifest_path
hf_result_path
hf_final_video_path
hf_cover_path
hf_subtitle_timeline_path
hf_render_ms
hf_final_video_url
hf_cover_url
```

## 已发生的迁移风险

2026-06-16 曾尝试执行网感视频 SQL 迁移，执行到 `analysis_path VARCHAR(1000)` 时 MySQL 报错：

```text
Row size too large. The maximum row size for the used table type, not counting BLOBs, is 65535.
```

原因判断：`t_video_generate_task` 已经是一张较宽的表，继续添加多个 `VARCHAR(1000)` 会增加 MySQL 最大行宽压力。路径和 URL 这类内部产物字段不应再默认用 `VARCHAR(1000)` 叠加。

## 表结构变更硬规则

1. 不允许因为“代码里字段存在”就直接改测试库或生产库。
2. 改表前必须只读核对：`information_schema.COLUMNS`、`information_schema.STATISTICS`、当前表字段类型、索引状态。
3. 必须核对 apidoc：确认字段是外部接口字段，还是后端内部字段。
4. 必须核对 Obsidian/开发文档：确认该字段属于最终决策、阶段文档要求，还是候选观测字段。
5. 必须区分字段级别：
   - 外部接口/主分流必需字段：例如 `templates_style_id`。
   - 内部链路运行字段：例如 `whisper_timeline_path`、`analysis_path`。
   - 内部排查/恢复观测字段：例如 `hf_manifest_path`、`hf_result_path`。
6. 对共享测试库执行 `ALTER TABLE` 前，必须展示：目标库、目标表、字段清单、字段类型、索引、当前已存在字段、预期影响、回滚/补救方案，并等待用户明确确认。
7. 如果测试服发现 bug，必须先修回 `feature/ai_v6.3.3_vibevideo`，再重新集成到 `test`，不能只修 test 集成分支或只手工改测试库。
8. `test` 集成分支只用于测试环境验收，不作为后续合入 `master` 的来源。
9. 后续合 `master` 的来源必须是 `feature/ai_v6.3.3_vibevideo`。

## 字段类型建议（需确认后执行）

对于内部路径/URL 类字段，如果决定继续落库，建议避免新增 `VARCHAR(1000)`，优先评估：

```sql
TEXT NULL
```

候选字段包括：

```text
whisper_timeline_path
analysis_path
hf_manifest_path
hf_result_path
hf_final_video_path
hf_cover_path
hf_subtitle_timeline_path
hf_final_video_url
hf_cover_url
```

耗时和分流字段仍使用标量类型：

```text
templates_style_id INT NOT NULL DEFAULT 3
whisper_timeline_ms INT NULL
analysis_ms INT NULL
hf_render_ms INT NULL
```

注意：`TEXT` 方案只是候选迁移策略，不代表已经允许改测试库。执行前仍需用户确认。

## 两种可选实施策略

### 策略 A：保守最小字段

只保留 `templates_style_id` 作为强依赖落库字段。

适用情况：
- 当前首要目标是降低共享测试库改表风险。
- 内部产物路径可以通过日志、本地目录、任务输出目录来排查。
- 愿意修改代码，移除或降级 `analysis_path/hf_*` 等 ORM 字段依赖。

风险：
- 问题复现和链路恢复能力下降。
- 需要改代码，确保 ORM 不引用数据库不存在字段。

### 策略 B：完整观测字段

保留阶段文档中的内部产物字段，但路径/URL 类字段使用 `TEXT`，并在改表前做完整只读核对和用户确认。

适用情况：
- 需要完整记录每个阶段产物，方便 E2E 验收、故障排查和恢复。
- 接受一次谨慎的测试库 schema 变更。

风险：
- 仍属于共享测试库结构变更，必须谨慎执行。
- 当前测试库已有 `whisper_timeline_path VARCHAR(1000)`，如需改为 `TEXT`，还要单独评估 `MODIFY COLUMN` 的影响。

## 当前执行状态

截至 2026-06-16：

- 测试库只读核对已完成。
- 不再继续执行任何测试库写操作，除非用户明确确认。
- 本地曾形成一个候选修复方向：将内部路径/URL 字段从 `VARCHAR(1000)` / `db.String(1000)` 调整为 `TEXT` / `db.Text`，用于解决 MySQL row size 风险；该方向需要先完成字段策略确认，再决定是否提交、推送、应用到测试库。
- 上测试服前必须重新确认测试库 schema 与最终代码字段策略一致。

## 图谱链接

- [[projects/joying-bot-server/00-项目概览|项目概览]]
- [[projects/joying-bot-server/docs/00-docs-index|参考文档索引]]
- [[projects/joying-bot-server/docs/h20-hyperframes-prd-uncertainty-decisions-2026-06-08|H20 HyperFrames PRD 不确定项与决策记录]]
- [[projects/joying-bot-server/docs/h20-hyperframes-local-lipsync-template-validation-2026-06-11|本地唇形样本与模板验证记录]]
## 2026-06-16 功能分支与 test 集成验证补充

### 本次代码状态

- 功能分支：`feature/ai_v6.3.3_vibevideo`
- 已推送提交：`a775e3a5 fix: use text for hyperframes artifact fields`
- 变更范围：`pojo/models.py`、4 个 HyperFrames SQL 迁移文件、4 个字段类型回归测试文件。
- 当前代码策略：采用“策略 B 候选方向”，保留 Whisper / analysis / hf_* 内部观测字段，但将路径/URL 类字段从 `db.String(1000)` / `VARCHAR(1000)` 调整为 `db.Text` / `TEXT`，避免继续增加 MySQL 行内宽度压力。
- 标量字段保持不变：`templates_style_id INT NOT NULL DEFAULT 3`、`whisper_timeline_ms INT NULL`、`analysis_ms INT NULL`、`hf_render_ms INT NULL`。

### apidoc 复核结论

- CRM `699` `/crm/agent/pc/video/generateJobBatchCreate`：创建入参包含 `templates_style_id`。
- CRM `701` `/crm/agent/pc/video/generateJobUserCreate`：创建入参包含 `templates_style_id`。
- CRM `2335` `/crm/agent/pc/video/templatesStyleList`：返回风格模板列表字段 `id/style_name/cover_url/sort/status`。
- CSM `712` `/csm/agent/pc/video/generateTaskList`：任务列表返回示例包含 `templates_style_id`。
- CSM `713` `/csm/agent/pc/video/generateTaskCallback`：文档示例仍写 `status`，但当前 H20 代码和既有决策继续沿用 `task_status`，本次不新增模板字段到 callback payload。

### 代码读写依据

- `templates_style_id`：由 `router/crm_server.py` 和 `scheduler/collect_scheduler.py` 在任务同步时读取 task/job payload 并写入本地任务表；scheduler 领取任务后据此进入 minimal 或 HyperFrames 路由。
- `whisper_timeline_path` / `analysis_path`：由 HyperFrames 准备链路写入，并作为后续 CLI manifest 必填输入。
- `hf_manifest_path` / `hf_result_path` / `hf_final_video_path` / `hf_cover_path` / `hf_subtitle_timeline_path`：由 HyperFrames CLI 渲染结果写入，用于排查、恢复和上传阶段输入。
- `hf_final_video_url` / `hf_cover_url`：由上传阶段写入，同时同步到现有业务字段 `generate_video_url` / `cover_image_url`，callback payload 仍沿用现网字段。

### 验证结果

在功能分支 `feature/ai_v6.3.3_vibevideo`：

```powershell
python -m py_compile common/json_util.py pojo/models.py router/crm_server.py scheduler/collect_scheduler.py router/service/video_server2/video_work.py router/service/video_server2/template_route.py router/service/video_server2/hyperframes_analysis.py router/service/video_server2/hyperframes_cli.py router/service/video_server2/whisper_timeline.py
node --check hyperframes-postprocess\index.js
python -m unittest test.test_template_route test.test_hyperframes_postprocess test.test_hyperframes_cli test.test_hyperframes_analysis test.test_whisper_timeline test.test_hyperframes_upload_callback -v
```

结果：65 个相关单测通过。

在临时 test 集成 worktree `C:\Users\admin\AppData\Local\Temp\joyingbot-new-ai-v633-test-merge`：

- 已在目标侧临时分支 `merge-check/ai_v6.3.3_vibevideo-to-test` 合入最新功能分支提交。
- `python -m py_compile ...` 通过。
- `node --check hyperframes-postprocess\index.js` 通过。
- `python -m unittest test.test_template_route test.test_hyperframes_postprocess test.test_hyperframes_cli test.test_hyperframes_analysis test.test_whisper_timeline test.test_hyperframes_upload_callback -v` 通过，65 项 OK。

### 测试库门禁状态

- 本次未继续执行任何测试库写操作。
- 已知测试库 `zhugedata_test.t_video_generate_task` 当前仅确认已有 `templates_style_id`、`whisper_timeline_path VARCHAR(1000)`、`whisper_timeline_ms` 和索引 `idx_video_generate_task_templates_style_id`，其余 analysis/hf_* 字段仍缺失。
- 若继续采用策略 B，上测试服前需要单独展示并确认具体 SQL，其中至少要包含：把现有 `whisper_timeline_path` 从 `VARCHAR(1000)` 调整为 `TEXT`，并新增 analysis/hf_* 字段为 `TEXT` 或 `INT`。
- 在用户明确确认目标库、字段、SQL、影响和回滚方案前，不允许执行 `ALTER TABLE`。
## 2026-06-16 测试库字段变更已执行

### 执行目标

- 目标库：`zhugedata_test`
- 目标表：`t_video_generate_task`
- 执行前安全校验：目标库名、目标表名、已有字段、缺失字段、索引 `idx_video_generate_task_templates_style_id(templates_style_id, task_status)` 均与已确认状态一致后才执行。

### 已执行 SQL 摘要

- `whisper_timeline_path`：从 `VARCHAR(1000)` 修改为 `TEXT`。
- 新增 `analysis_path TEXT NULL`、`analysis_ms INT NULL`。
- 新增 `hf_manifest_path TEXT NULL`、`hf_result_path TEXT NULL`、`hf_final_video_path TEXT NULL`、`hf_cover_path TEXT NULL`、`hf_subtitle_timeline_path TEXT NULL`、`hf_render_ms INT NULL`。
- 新增 `hf_final_video_url TEXT NULL`、`hf_cover_url TEXT NULL`。

### 执行后验证

执行后 `information_schema.COLUMNS` 验证通过：

```text
templates_style_id int NOT NULL DEFAULT 3
whisper_timeline_path text NULL
whisper_timeline_ms int NULL
analysis_path text NULL
analysis_ms int NULL
hf_manifest_path text NULL
hf_result_path text NULL
hf_final_video_path text NULL
hf_cover_path text NULL
hf_subtitle_timeline_path text NULL
hf_render_ms int NULL
hf_final_video_url text NULL
hf_cover_url text NULL
```

索引验证通过：

```text
idx_video_generate_task_templates_style_id(templates_style_id, task_status)
```

表状态：`ENGINE=InnoDB`，`ROW_FORMAT=Dynamic`，`TABLE_COLLATION=utf8mb4_0900_ai_ci`。

### 影响与后续门禁

- 测试库 schema 现在已与功能分支 `feature/ai_v6.3.3_vibevideo` 当前 ORM 字段策略匹配。
- 这只代表测试库结构已补齐，不代表代码已合入 `test`，也不代表测试服进程已部署或重启。
- 下一步仍应遵守：测试服发现 bug 必须先修回 `feature/ai_v6.3.3_vibevideo`，再重新集成到 `test`；不要只修 test 集成分支。
## 2026-06-16 test 分支发布与 H20 重启验证

### GitLab test 状态

- 已按用户明确确认，将临时目标侧集成分支 `merge-check/ai_v6.3.3_vibevideo-to-test` 推送到共享远端 `test`。
- 推送结果：`origin/test` 从 `a6f6db4a` 更新到 `1fb5e38935e7da6b5358dd6bbe5baac29825cd2e`。
- 远端复核：`refs/heads/test = 1fb5e38935e7da6b5358dd6bbe5baac29825cd2e`。

### H20 自动部署与代码标记

- H20 当前 release：`/data/project/test_ai_botserver.20260616162226`
- `/data/project/test_ai_botserver` 已指向该 release。
- 新代码标记已存在：
  - `hyperframes-postprocess/index.js`
  - `router/service/video_server2/hyperframes_cli.py`
  - `router/service/video_server2/hyperframes_analysis.py`
  - `router/service/video_server2/template_route.py`
  - `sql/h20_hyperframes_upload_callback.sql`
- grep 标记存在：`hf_final_video_url`、`HYPERFRAMES_UPLOAD_FAILED`、`H20_HYPERFRAMES_ROUTE_ENABLED`。

### 服务重启与健康检查

自动部署后：

- `8017` 已运行在新 release。
- `18017` 已运行在新 release。
- `8100` 仍运行在旧 release `/data/project/test_ai_botserver.20260616093915`。

已只重启 stale 的 `8100`：

- 旧 `8100` PID：`152366`，cwd 为旧 release。
- 新 `8100` PID：`458228`，cwd 为 `/data/project/test_ai_botserver.20260616162226`。
- `8017` PID：`454974`，cwd 为 `/data/project/test_ai_botserver.20260616162226`。
- `18017` PID：`454975`，cwd 为 `/data/project/test_ai_botserver.20260616162226`。

健康检查：

```text
8100 /status/check -> {"status":"ok"}
8017 /status/check -> {"status":"ok"}
```

### 队列和模型池只读检查

- `t_video_generate_task`：`task_status=3` 共 661 条，`task_status=4` 共 392 条。
- 当前无 `task_status IN (0,1,2)` 的 active 任务。
- `t_comfyui_config`：`comfyui_url is_active=1` 共 3 条，`is_active=0` 共 13 条，无 `is_active=2` 锁；`voice_audition_url is_active=0` 共 4 条。

### 后续门禁

- 代码已上 test 且服务已加载新 release。
- `H20_HYPERFRAMES_ROUTE_ENABLED` 仍是运行时门禁：若未显式开启，`science_guide` / `video_diary` 会明确失败为 disabled，不会误入半成品链路。
- 下一步进入真实任务 E2E：至少验证 `science_guide`、`video_diary`、`minimal` 各一条；检查 final video/cover URL、callback、ffprobe、抽帧视觉质量。