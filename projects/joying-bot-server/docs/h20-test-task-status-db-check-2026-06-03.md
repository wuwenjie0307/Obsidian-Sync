---
date: "2026-06-03"
tags: [h20, mysql, db-check, task-status, model-pool, runbook]
---

# h20 测试服任务队列与异常检查 SQL 记录

## 用途

用于确认 h20 测试服当前是否有：

- 排队任务。
- 处理中任务。
- 模型池资源锁死。
- 最近失败任务。
- 回调异常任务。
- 最近任务整体状态。

本记录对应 2026-06-03 对 `zhugedata_test` 的只读检查。

## 数据库登录方式

检查是在 Codex 本机 PowerShell 里执行的，不是登录 h20 后查库。

方式：本地 Python + `pymysql` 直连 MySQL。

连接目标：

```text
host=222.71.55.27
port=3306
user=root
database=zhugedata_test
charset=utf8mb4
cursorclass=pymysql.cursors.DictCursor
connect_timeout=15
```

密码只在本次查询命令中临时使用，没有写入 Obsidian、Git、代码文件或最终回复。后续记录和 runbook 中统一写成：

```python
password='<redacted>'
```

连接代码骨架：

```python
import pymysql

conn = pymysql.connect(
    host='222.71.55.27',
    port=3306,
    user='root',
    password='<redacted>',
    database='zhugedata_test',
    connect_timeout=15,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
)
```

说明：本次是只读查询，没有执行 INSERT / UPDATE / DELETE。

## 查询的表

### 1. `zhugedata_test.t_video_generate_task`

用途：判断视频任务是否排队、处理中、失败、回调异常，以及最近任务状态。

本次用到的字段：

| 字段 | 用途 |
|---|---|
| `id` | 本地任务表主键，用于排序和定位 |
| `job_id` | CRM/job 维度任务 id |
| `task_id` | 视频生成任务 id，和日志排查常用口径一致 |
| `task_status` | 任务状态：重点看 `0/1/2/3/4` |
| `progress` | 任务进度 |
| `callback_status` | CRM 回调状态 |
| `publish_call_status` | 发布回调/发布调用状态，用于辅助看任务后续状态 |
| `created_time` | 任务创建时间 |
| `updated_time` | 任务更新时间，用于判断是否卡住 |
| `fail_reason` | 失败原因 |

当前判断口径：

```text
task_status=0：待处理/排队
task_status=1/2：处理中或已被领取处理中
task_status=3：成功
task_status=4：失败
callback_status=1：主回调成功
```

注意：具体状态枚举以代码为准；当前排查只按现有测试服数据和 scheduler 习惯口径使用。

### 2. `zhugedata_test.t_comfyui_config`

用途：判断模型池配置是否空闲、锁定或禁用。

本次用到的字段：

| 字段 | 用途 |
|---|---|
| `id` | 模型池配置 id，scheduler 锁资源时使用 |
| `config_key` | 配置类型，当前模型池使用 `comfyui_url` |
| `config_value_audio` | VoxCPM 声音克隆服务地址 |
| `config_value` | LatentSync 唇形同步服务地址 |
| `is_active` | 资源池状态：`1` 空闲，`2` 使用中，`0` 禁用 |
| `description` | 人工描述，当前 h20 Docker 组统一为 `h20` |
| `type` | 展示/历史分类字段，当前调度代码不依赖它 |
| `updated_time` | 配置更新时间，用于判断是否长时间锁住 |

当前判断口径：

```text
config_key='comfyui_url' and is_active=1：可被 scheduler 领取
config_key='comfyui_url' and is_active=2：正在被任务占用
config_key='comfyui_url' and is_active=0：禁用，不参与调度
```

## 本次实际执行的 SQL

### 1. 查是否有排队/处理中任务数量

```sql
SELECT task_status, COUNT(*) AS cnt
FROM t_video_generate_task
WHERE task_status IN (0,1,2)
GROUP BY task_status
ORDER BY task_status;
```

用途：如果返回空数组，说明当前没有排队/处理中任务。

### 2. 查排队/处理中任务明细

```sql
SELECT id, job_id, task_id, task_status, progress, callback_status,
       created_time, updated_time, fail_reason
FROM t_video_generate_task
WHERE task_status IN (0,1,2)
ORDER BY id DESC
LIMIT 20;
```

用途：确认具体有没有任务卡住、进度是多少、更新时间是否异常。

### 3. 查模型池是否有锁死配置

```sql
SELECT id, config_value_audio, config_value, is_active,
       description, type, updated_time
FROM t_comfyui_config
WHERE config_key='comfyui_url'
  AND is_active=2
ORDER BY id ASC;
```

用途：如果返回空数组，说明没有模型池处于使用中/锁定状态。结合任务表为空，可以判断没有资源锁死。

### 4. 查最近失败任务

```sql
SELECT id, job_id, task_id, task_status, progress, callback_status,
       created_time, updated_time, fail_reason
FROM t_video_generate_task
WHERE task_status=4
ORDER BY id DESC
LIMIT 10;
```

用途：看最近失败是否是当前问题，还是历史失败/人工清理任务。

### 5. 查成功任务里的回调异常

```sql
SELECT id, job_id, task_id, task_status, progress, callback_status,
       publish_call_status, created_time, updated_time, fail_reason
FROM t_video_generate_task
WHERE task_status=3
  AND (callback_status IS NULL OR callback_status<>1)
ORDER BY id DESC
LIMIT 10;
```

用途：找生成成功但主回调未成功的历史异常。这个查询可能返回历史老数据，不代表当前队列异常，需要结合 `created_time/updated_time/task_id` 判断。

### 6. 查最近 20 条任务状态

```sql
SELECT id, job_id, task_id, task_status, progress, callback_status,
       publish_call_status, created_time, updated_time,
       LEFT(fail_reason, 200) AS fail_reason
FROM t_video_generate_task
ORDER BY id DESC
LIMIT 20;
```

用途：看最近任务整体是否连续成功，是否出现新失败或回调异常。

### 7. 查当前模型池总状态

```sql
SELECT id, config_value_audio, config_value, is_active,
       description, type
FROM t_comfyui_config
WHERE config_key='comfyui_url'
ORDER BY id ASC;
```

用途：确认 h20 当前 active 模型池有哪些，以及 `description/type/is_active` 是否统一。

## 2026-06-03 本次查询结论

### 当前队列

```text
task_status in (0,1,2)：0 条
```

结论：没有排队任务，没有处理中任务。

### 当前模型池

```text
is_active=2：0 条
```

结论：没有模型池资源被锁住。

当前 active Docker 模型池：

| id | VoxCPM | LatentSync | is_active | description | type |
|---:|---|---|---:|---|---:|
| `1` | `http://127.0.0.1:8120` | `http://127.0.0.1:8121` | `1` | `h20` | `1` |
| `2` | `http://127.0.0.1:8122` | `http://127.0.0.1:8123` | `1` | `h20` | `1` |
| `10` | `http://127.0.0.1:8124` | `http://127.0.0.1:8125` | `1` | `h20` | `1` |
| `11` | `http://127.0.0.1:8126` | `http://127.0.0.1:8127` | `1` | `h20` | `1` |

### 最近任务

最近 20 条任务均为：

```text
task_status=3
progress=100
callback_status=1
```

结论：最近 20 条任务生成成功且主回调成功。

### 历史异常

最近失败查询能看到历史失败记录，例如：

```text
task_id=1041 / 1042：视频合成阶段失败
```

也能看到部分历史人工清理任务，例如：

```text
docker compose refresh cleanup: cancelled by test operator
```

这些不属于当前排队/当前异常。

成功任务回调异常查询能看到一些更早的历史数据，例如 2026-05-22 或 2026-03 的记录。该类记录只说明历史库中存在老数据，不代表当前 h20 队列异常。

## 对外口径

可以这样说：

```text
我查的是测试库 zhugedata_test 的 t_video_generate_task 和 t_comfyui_config。
任务表看 task_status in (0,1,2) 判断有没有排队/处理中；模型池表看 is_active=2 判断有没有资源锁住；再看最近失败和最近 20 条任务状态确认有没有新异常。
当前没有排队任务，没有处理中任务，没有模型池锁死；最近 20 条任务都是成功并回调成功。历史库里有失败和回调异常老数据，但不是当前异常。
```
