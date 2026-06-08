---
date: "2026-06-08"
status: open
severity: high
tags: [bug, production, lucky-prod, video-generation, montage, crm-sync, scheduler, apidoc]
---

# 生产 scheduler 未同步用户混剪素材导致纯口播

## 问题描述

2026-06-08 客户反馈连续 3 次提交视频任务，每次都选择了 1 个混剪/分镜素材，但生成结果都是纯口播，没有混剪画面覆盖。

业务预期是：用户选中某一段文案后，视频播放到这句口播文案时，使用用户选择的分镜视频/素材覆盖原口播画面。

本次排查确认：不是 ffmpeg 覆盖阶段失败，也不是文案太短导致无法匹配；问题发生在更早的素材同步阶段。

## 生产证据

失败任务来自生产库 `zhugedata.t_video_generate_task`：

| local id | job_id | task_id | company_id | video_category | generate_source | 结果 |
|---:|---:|---:|---:|---:|---:|---|
| `9694` | `10433` | `9687` | `193` | `0` | `2` | 生成成功但纯口播 |
| `9696` | `10435` | `9689` | `193` | `0` | `2` | 生成成功但纯口播 |
| `9697` | `10436` | `9690` | `193` | `0` | `2` | 生成成功但纯口播 |

生产本地表 `t_video_material_template` 对这 3 个任务没有素材记录，`material_count=0`。这说明后续视频生成链路根本没有拿到混剪素材。

同时，CRM 实时接口 `/csm/agent/pc/video/materialUsertaskList` 能查到用户选中的素材：

- `company_id=193, job_id=10436, task_id=9690` 返回 `total=1`，有素材 URL，`material_type=1`，`is_mix_material=1`。
- `company_id=193, job_id=10433, task_id=9687` 也能返回 1 条用户任务素材。

结论：用户在 CRM 侧确实选了混剪素材，但生产后端本地没有同步下来。

## apidoc 对照

apidoc 里相关接口含义如下：

| 接口 | apidoc 标题 | 作用 |
|---|---|---|
| `/crm/agent/pc/video/materialTemplatesList` | 短视频 / 模板 / 模板素材列表 | 模板素材库，不是用户本次任务实际选择的素材 |
| `/crm/agent/pc/video/materialUsertaskList` | 短视频 / 模板 / 用户任务素材列表 | 查询用户任务维度素材 |
| `/csm/agent/pc/video/materialUsertaskList` | 短视频 / 视频分镜素材列表 | 查询用户任务/分镜维度素材 |

`materialUsertaskList` 的入参示例包含：

```json
{
  "filter": {
    "company_id": 1,
    "job_id": 118,
    "task_id": 143
  },
  "from": 1,
  "size": 10
}
```

返回素材字段包括：

- `job_id`
- `task_id`
- `material_type`
- `material_subtitle`
- `material_source_url`
- `is_mix_material`
- `sort_order`

这说明判断用户有没有选混剪素材，应该看 `materialUsertaskList`，不能只看 `video_category`，也不能从 `materialTemplatesList` 判断。

注意：`csm` 项目里的 `/csm/agent/pc/video/materialUsertaskList` apidoc 返回示例疑似复制了 job 列表字段，里面出现了 `video_category` 等字段，容易误导；`crm` 项目里的同类接口示例更接近真实素材结构。

## 原因

直接原因：生产 scheduler 链路同步素材时使用了旧逻辑。

生产分支 `origin/dev-lucky-yk-prod` 中，`scheduler/collect_scheduler.py` 仍然是：

- 先判断 `video_category == 2`
- 满足后才同步素材
- 同步时调用的是 `materialTemplatesList`

但这次失败任务的真实混剪素材在 `materialUsertaskList` 中，且任务 `video_category=0`。因此 scheduler 没有把用户任务素材同步到本地 `t_video_material_template`，后续生成时只能按“没有混剪素材”的纯口播任务处理。

更准确地说，这不是前端没选上，而是后端 scheduler 没有从正确接口同步用户任务素材。

## 为什么之前没明显出现

这个更像是遗留链路问题，不是 2026-06-08 当天新写坏的逻辑。

旧 scheduler 逻辑早就存在，但之前能混剪的任务可能更多走 `/generate_video_task` 这条 router 链路。生产分支 router 里已经有“按 job 调用 `materialUsertaskList` 同步素材”的逻辑，所以那条链路能把素材写入本地表。

近期生成流程更多走 scheduler 后，scheduler 没同步 `materialUsertaskList` 的旧问题才暴露出来。

补充证据：5 月 21 日曾经成功混剪的任务里，`video_category` 也不一定是 `2`，`is_mix_material` 也不一定是 `1`；真正区别是当时本地 `t_video_material_template` 里有素材记录。

## 复现步骤

1. 在 CRM/前端创建视频生成任务。
2. 给某段文案选择 1 个混剪/分镜素材。
3. 让任务走生产 scheduler 生成链路。
4. 生成完成后查看视频，结果是纯口播。
5. 查生产本地 `t_video_material_template`，对应 `job_id/task_id` 没有素材记录。
6. 同时查 CRM `/csm/agent/pc/video/materialUsertaskList`，对应 `company_id/job_id/task_id` 能查到用户选的素材。

## 期望行为

scheduler 同步任务时，应根据 `company_id + job_id + task_id` 或至少 `company_id + job_id` 调用 `materialUsertaskList`，把用户实际选择的任务素材同步到本地 `t_video_material_template`。

生成阶段应能读取本地素材表，并在对应口播文案处覆盖混剪/分镜素材。

## 实际行为

scheduler 仍按旧逻辑依赖 `video_category == 2`，并调用 `materialTemplatesList`。对于 `video_category=0` 但实际有用户混剪素材的任务，素材没有入库，最终生成成纯口播。

## 解决方案

建议修复 scheduler 素材同步逻辑：

1. scheduler 不再用 `video_category == 2` 作为是否同步混剪素材的开关。
2. scheduler 改为调用 `get_crm_video_material_usertask_list` / `/materialUsertaskList`。
3. 按 `company_id + job_id + task_id` 同步用户任务素材；如果接口按 job 返回多任务素材，则入库时使用返回行里的真实 `task_id` 做隔离。
4. 不要硬性只保留 `is_mix_material=1`。历史成功任务里存在 `is_mix_material=0` 但仍有素材的情况，生成侧应优先看 `task_id`、`material_source_url`、`material_subtitle`、`material_type` 等有效素材字段。
5. 增加回归测试，覆盖 `video_category=0` 但 `materialUsertaskList` 有素材的任务。

## 当前沟通口径

对前端/CRM 同事可以这样说明：

> 我查了下 apidoc 和生产数据，用户选的混剪素材应该在 `materialUsertaskList` 里，不是靠 `video_category` 或 `materialTemplatesList` 判断。这次 CRM 里能查到素材，但我们后端 scheduler 没同步到本地表，所以生成成纯口播。你们那边帮忙确认 `materialUsertaskList` 里的 `job_id`、`task_id`、素材地址这些字段正常写入就行。

更简短版本：

> 前端应该是选上了，问题在后端 scheduler 没把 `materialUsertaskList` 里的素材同步下来，所以生成时当成没混剪。

## 环境信息

- 项目：`joying-bot-server` / `joyingbot-new`
- 生产分支参考：`origin/dev-lucky-yk-prod`
- 本地工作分支：`test` / `feature/ai_v6.3.1_video` 曾做过修复验证
- 生产 DB：`zhugedata`
- 相关表：`t_video_generate_task`、`t_video_material_template`
- 相关接口：`/csm/agent/pc/video/materialUsertaskList`、`/crm/agent/pc/video/materialUsertaskList`、`/crm/agent/pc/video/materialTemplatesList`
- 本次生产排查为只读查询：没有修改生产代码、生产 DB，也没有重启生产服务。

## 优化点

- scheduler 素材同步日志里明确打印：调用的素材接口、`company_id/job_id/task_id`、返回 `total`、实际入库条数。
- 素材同步失败或返回 0 条时，如果 CRM 任务疑似有混剪配置，应记录 warning，避免最后只看到纯口播结果。
- 不要把 `video_category` 当作“是否存在用户混剪素材”的唯一依据；它更像视频大类字段，历史数据中不稳定。
- apidoc 中 `/csm/agent/pc/video/materialUsertaskList` 的返回示例建议请接口维护方修正，避免继续误导成 job 列表或 `video_category` 判断。
- 生成侧对空素材表增加可观测日志：明确输出“当前 task 本地素材数为 0，按纯口播生成”。

## 相关文件

- `C:\Users\admin\Desktop\joyingbot-new\scheduler\collect_scheduler.py`
- `C:\Users\admin\Desktop\joyingbot-new\router\crm_server.py`
- `C:\Users\admin\Desktop\joyingbot-new\router\service\video_server2\video_work.py`
- `C:\Users\admin\Desktop\joyingbot-new\router\service\video_server2\video_select_overlay.py`
- apidoc：`/csm/agent/pc/video/materialUsertaskList`
- apidoc：`/crm/agent/pc/video/materialUsertaskList`
- apidoc：`/crm/agent/pc/video/materialTemplatesList`
## 2026-06-08 补充发现：CRM 素材 ID bigint 超出 AI 本地表 int 范围

合并 `hotfix/prod-montage-material-sync` 到 `master` 前，CRM 同事补充确认：CRM 素材库的 `id` 是 `bigint`，而 AI 本地表 `t_video_material_template.material_id` 仍是 `int` 类型。

AI 代码模型当前对应字段为：

```python
class VideoMaterialTemplate(db.Model):
    __tablename__ = 't_video_material_template'

    material_id = db.Column(db.Integer, nullable=False, comment='素材ID（materialTemplatesList 返回的 id）')
```

因此即使 scheduler 已经改为调用 `materialUsertaskList`，只要 CRM 返回的素材 `id` 超过 MySQL signed int 范围（`2147483647`），同步本地素材表时仍可能失败，常见表现类似：

```text
Out of range value for column 'material_id'
```

这会导致混剪素材无法保存到 AI 本地表，后续生成阶段仍然查不到素材，最终表现依旧可能是纯口播。

### 新增根因

除 scheduler 接口/判断逻辑问题外，还存在数据库字段类型不匹配：

| 字段 | CRM | AI 本地表当前 | 风险 |
|---|---|---|---|
| 素材 ID | `bigint` | `int` | CRM 素材 id 超 int 后无法入库 |

### 对 hotfix 的影响

当前 hotfix 已推到 GitLab 分支：

```text
hotfix/prod-montage-material-sync
```

但尚未合并到 `master`。由于发现字段类型新阻断项，暂缓合并 `master` 是正确的。

### 需要补充的修复

1. 代码模型改为 `BigInteger`：

```python
material_id = db.Column(db.BigInteger, nullable=False, comment='素材ID（materialUsertaskList 返回的 bigint id）')
```

2. 测试库和生产库需要同步执行表结构变更：

```sql
ALTER TABLE t_video_material_template
MODIFY COLUMN material_id BIGINT NOT NULL COMMENT '素材ID（materialUsertaskList 返回的 id）';
```

3. 增加回归测试，确保 `VideoMaterialTemplate.material_id` 不再是 `db.Integer`。

4. 重新验证 `materialUsertaskList` 返回 bigint 素材 id 时能成功写入 AI 本地表，并能进入后续 `Montage_dict` / `Photo_dict`。

### 对外沟通口径

> 刚确认还有一个更底层的问题：CRM 素材库 `id` 是 bigint，但 AI 本地表 `t_video_material_template.material_id` 是 int。这样即使接口拉到了素材，只要素材 id 超 int，就会在 AI 入库时失败，导致后面生成还是查不到混剪素材。我们先不合 master，hotfix 需要补 `material_id` BigInteger，同时测试库/生产库执行 ALTER TABLE，再重新验证素材入库和混剪生成。
## 2026-06-08 补充记录：hotfix 远端分支已撤回，master 未合并

由于 CRM 侧发现素材 `id` 被异常写成毫秒时间戳，导致 CRM 素材表自增 ID 剧增，团队决定先由 CRM 侧排查/修复该数据问题。因此本次用于生产 `master` 的 hotfix 暂停合并。

### Git 状态

原 hotfix 分支：

```text
hotfix/prod-montage-material-sync
```

处理结果：

- 未合并到 `master`。
- GitLab 远端分支 `hotfix/prod-montage-material-sync` 已删除。
- `origin/master` 仍停留在原提交：

```text
8660c153393e41bd3174b1374804b0d8043cdbb2 refs/heads/master
```

远端验证结果：

```text
git ls-remote --heads origin hotfix/prod-montage-material-sync
# 返回为空，说明远端 hotfix 分支已不存在
```

本地临时 worktree 暂时保留，便于 CRM 侧确认完后继续调整或重新制作补丁；它不会影响远端分支和生产 `master`。

### 当前建议

1. 先由 CRM 侧确认异常素材 ID 为什么被写成毫秒时间戳。
2. 修正 CRM 素材表异常数据和 `AUTO_INCREMENT` 自增值。
3. 再决定 AI 侧是否仍需要把 `t_video_material_template.material_id` 改为 `BIGINT`。
4. 在 CRM 数据恢复正常前，不继续合并生产 `master`。
## 2026-06-08 补充记录：需要核对的表、字段和 SQL

当前排查需要同时看 AI 本地表和 CRM 素材来源表。

### AI 侧表：t_video_material_template

AI 侧明确表名：

```text
t_video_material_template
```

用途：保存从 CRM 同步过来的用户任务素材，后续视频生成阶段会从这里读取素材并组装 `Montage_dict` / `Photo_dict`。

重点字段：

| 字段 | 含义 | 本次关注点 |
|---|---|---|
| `id` | AI 本地自增主键 | 非本次核心 |
| `company_id` | 公司 ID | 用于定位任务素材 |
| `job_id` | CRM 视频 job_id | 用于定位任务素材 |
| `task_id` | CRM 视频 task_id | 用于定位任务素材 |
| `material_id` | CRM 素材 id | 本次核心，当前 AI 代码模型是 `int`，可能存不下 CRM bigint/异常毫秒时间戳 id |
| `material_name` | 素材名称 | 辅助确认素材 |
| `material_type` | 素材类型 | `1`=视频混剪，`2`=图片素材 |
| `material_subtitle` | 素材绑定文案 | 生成时用于匹配口播覆盖位置 |
| `material_source_url` | 素材源地址 | 生成时实际使用的视频/图片地址 |
| `is_mix_material` | 是否混剪素材 | 只作为返回字段记录，不建议作为唯一硬判断 |
| `is_lip_sync` | 是否唇形同步 | 生成参数之一 |
| `sort_order` | 排序 | 素材顺序 |

AI 侧建议查询：

```sql
SHOW CREATE TABLE t_video_material_template;
```

或只看 `material_id` 字段类型：

```sql
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 't_video_material_template'
  AND column_name = 'material_id';
```

按任务查素材是否落库：

```sql
SELECT id, company_id, job_id, task_id, material_id, material_name,
       material_type, material_subtitle, material_source_url,
       is_mix_material, sort_order
FROM t_video_material_template
WHERE job_id = <job_id>
  AND task_id = <task_id>;
```

如果这里没有对应素材记录，生成阶段就会认为没有混剪素材。

### CRM 侧表：materialUsertaskList / generateJobUserCreate 的 video_material 来源表

CRM 侧真实表名暂未从 AI 代码中确认，需要 CRM 同事确认：

```text
/csm/agent/pc/video/materialUsertaskList
```

或：

```text
/crm/agent/pc/video/generateJobUserCreate 请求体里的 video_material
```

对应 CRM 哪张素材表。

本次异常样例：

```json
{
  "id": 1780827482284,
  "material_name": "mmexport1780651652241.jpg",
  "material_type": 2,
  "material_duration": 0,
  "is_mix_material": 1,
  "sort_order": 2
}
```

`1780827482284` 是 13 位数，形态接近毫秒时间戳，超过 MySQL signed int 最大值 `2147483647`。

CRM 侧需要重点核对：

1. 素材来源表里是否真的存在 `id = 1780827482284`。
2. 这个 id 是怎么被写成毫秒时间戳的。
3. 这张素材表的 `AUTO_INCREMENT` 是否已经被异常大 id 顶高。
4. 是否还有更多 `id > 2147483647` 的素材记录。
5. 这些异常 id 是否已经被返回给 `materialUsertaskList` 或生成任务创建接口。

CRM 侧建议 SQL（表名由 CRM 同事替换成真实素材表）：

```sql
SELECT id, material_name, material_type, created_at, updated_at
FROM <CRM素材表>
WHERE id IN (557, 1780827482284);
```

查是否有更多超过 int 范围的素材 id：

```sql
SELECT COUNT(*) AS big_id_count
FROM <CRM素材表>
WHERE id > 2147483647;
```

查看最大 ID 附近的数据：

```sql
SELECT id, material_name, material_type, created_at, updated_at
FROM <CRM素材表>
ORDER BY id DESC
LIMIT 20;
```

查看自增值是否被顶高：

```sql
SHOW TABLE STATUS LIKE '<CRM素材表名>';
```

重点看返回里的：

```text
Auto_increment
```

如果 `Auto_increment` 已变成类似 `1780827482285`，说明 CRM 素材表自增值已被异常毫秒时间戳 id 顶高。

### 当前判断

如果 CRM 自增 ID 被脏数据顶飞，优先修 CRM 数据和 `AUTO_INCREMENT`。AI 侧不要急着通过改 `material_id` 为 `BIGINT` 来兼容异常数据，否则可能只是兜住脏数据，根因仍然留在 CRM。

### 当前沟通口径

> 我这边主要要看两块：AI 这边是 `t_video_material_template`，重点看 `material_id` 字段类型是不是 int，以及对应 `job_id/task_id` 的素材有没有落库。CRM 那边需要你们确认 `/materialUsertaskList` 返回的 `video_material.id` 来源是哪张表，重点查 `id=1780827482284` 这条记录、有没有更多 `id > 2147483647` 的数据，以及这张表的 `AUTO_INCREMENT` 是不是已经被这个毫秒时间戳顶上去了。如果 CRM 自增被顶飞了，那先修 CRM 数据；AI 这边先不要急着改字段类型。
## 2026-06-08 补充记录：test 分支已回退，H20 测试服已运行回退后的代码

根据用户要求，本次已直接回退远端 `test` 分支上的混剪 hotfix 相关改动。回退方式为 `git revert`，不是 `reset`，不会改写历史，也不会覆盖 test 上其它提交。

### test 分支回退提交

远端 `test` 已推入两个 revert 提交：

```text
b8d3a075 Revert "fix: keep scheduler task materials without mix flag gate"
edf1f8dd Revert "fix: use usertask material sync for montage"
```

当前远端 `test` HEAD：

```text
edf1f8dd7597932b99e7a1d2ce9e98af8c727dfa refs/heads/test
```

推送前已重新 `fetch origin --prune`，确认当时 `origin/test` 没有其它新提交压在本次混剪提交之后；因此本次回退只撤销这两次混剪相关提交。

### 本地验证

```text
python -m unittest test.test_video_material_montage_sync
Ran 2 tests OK
```

```text
只读语法检查：syntax ok
```

```text
git diff --check origin/test..HEAD
通过
```

### H20 测试服发布/运行状态

H20 测试服当前发布目录：

```text
/data/project/test_ai_botserver.20260608195147
```

代码标记确认已经是回退后的版本：

```text
selected_material_count=missing
skipped_invalid_material_count=missing
get_crm_video_material_usertask_list=missing
selected_mix_material_count=present
skipped_non_mix_material_count=present
get_crm_video_material_templates_list=present
```

含义：测试服代码已不再包含本次 `materialUsertaskList` 混剪 hotfix，已回到原 test 逻辑。

### H20 进程状态

检查时发现：

```text
8017  已经运行在 /data/project/test_ai_botserver.20260608195147
18017 已经运行在 /data/project/test_ai_botserver.20260608195147
8100  仍运行在旧目录 /data/project/test_ai_botserver.20260608174831
```

因此只重启了 stale 的 `8100`，没有动 `8017` / `18017`。

重启后：

```text
8100  -> /data/project/test_ai_botserver.20260608195147
8017  -> /data/project/test_ai_botserver.20260608195147
18017 -> /data/project/test_ai_botserver.20260608195147
```

健康检查：

```text
8100 {"status":"ok"}
8017 {"status":"ok"}
```

### H20 任务/模型池状态

测试库：`zhugedata_test`

```text
ACTIVE_TASKS: none
```

模型池：

```text
comfyui_url: is_active=0 count=11
comfyui_url: is_active=1 count=4
voice_audition_url: is_active=1 count=4
```

没有发现 `is_active=2` 的模型池占用锁。

### 当前结论

远端 `test` 已回退，本次混剪 hotfix 已从测试服运行代码中撤掉。H20 测试服三个关键端口均运行在最新回退后的发布目录，健康检查正常，当前没有活跃视频任务和模型池锁。
