---
date: "2026-06-02"
tags: [h20, docker, execution-plan, model-pool, voxcpm, latentsync]
---

# h20 Docker 多开执行计划

## 结论

这是一份可以执行的 h20 测试服多开计划，但不是无条件立即执行。执行前必须先确认：

1. 运维允许在 h20 启动第二组 Docker 容器。
2. DB 允许 `t_comfyui_config` 存在多条 `config_key='comfyui_url'` 记录。
3. CRM/产品确认测试窗口内只提交本次 2 个并发验证任务。
4. 不停止现有第一组 Docker：`8120/8121`。
5. 不停止旧裸机回滚服务：`8110/8101`。

短期目标是验证 2 并发，不在同一窗口做生产化重构。

## 当前状态

h20 已验证：

```text
voxcpm-api-h20-test       joying/voxcpm-api:h20-test       127.0.0.1:8120 healthy GPU1
latentsync-api-h20-test   joying/latentsync-api:h20-test   127.0.0.1:8121 healthy GPU2
8122/8123                 当前未监听，可作为第二组端口
8110/8101                 旧裸机模型服务仍在，仅作为回滚/对照
```

生产旧口型 Docker 多开方式：多份 `docker-compose-text*.yml` 起多个 `guiji2025/duix.avatar:2.9` 容器，每个容器独立端口和 GPU。h20 只能借鉴这种多实例运维方式，不能复用生产 duix 镜像、命令或 yml。

## Task 1：只读预检

在 h20 执行：

```bash
cd /data/project/test_ai_botserver
/cm/local/apps/docker/current/bin/docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'
ss -ltnp | grep -E ':(8017|8100|8101|8110|8120|8121|8122|8123|8188)\b' || true
curl -s --max-time 5 http://127.0.0.1:8120/health; echo
curl -s --max-time 5 http://127.0.0.1:8121/health; echo
curl -sS --max-time 3 http://127.0.0.1:8122/health || true; echo
curl -sS --max-time 3 http://127.0.0.1:8123/health || true; echo
nvidia-smi --query-gpu=index,name,memory.used,memory.total,utilization.gpu --format=csv,noheader,nounits
```

预期：

```text
8120 -> ok
8121 -> ok
8122 -> connection refused
8123 -> connection refused
GPU3/GPU4 基本空闲
```

## Task 2：DB 索引确认

由 DBA 或有权限的人执行：

```sql
SHOW INDEX FROM zhugedata_test.t_comfyui_config;

SELECT id, config_key, config_value_audio, config_value, is_active, description
FROM zhugedata_test.t_comfyui_config
WHERE config_key = 'comfyui_url'
ORDER BY id ASC;
```

继续执行条件：真实库允许多条 `config_key='comfyui_url'` 记录。

停止条件：如果 `config_key` 有唯一索引，不能插入第二条 `comfyui_url`，必须先处理表结构或调整调度查询逻辑。

## Task 3：备份 compose

```bash
cd /data/project/test_ai_botserver
cp deploy/docker/docker-compose.h20.yml deploy/docker/docker-compose.h20.yml.bak.$(date +%Y%m%d%H%M%S)
ls -l deploy/docker/docker-compose.h20.yml*
```

预期：生成一份带时间戳的备份。

## Task 4：新增第二组服务

修改 `/data/project/test_ai_botserver/deploy/docker/docker-compose.h20.yml`，在 `services:` 下追加：

```yaml
  voxcpm-api-2:
    image: joying/voxcpm-api:h20-test
    container_name: voxcpm-api-h20-test-2
    network_mode: host
    restart: unless-stopped
    command: ["python", "/app/voxcpm_api.py", "--host", "0.0.0.0", "--port", "8122"]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ["3"]
              capabilities: [gpu]
    environment:
      NVIDIA_VISIBLE_DEVICES: "3"
      NVIDIA_DRIVER_CAPABILITIES: compute,utility
      HF_HOME: /root/.cache/huggingface
      TRANSFORMERS_CACHE: /root/.cache/huggingface
      HF_ENDPOINT: https://hf-mirror.com
      TMPDIR: /data/video_tmp
      PYTHONUNBUFFERED: "1"
    volumes:
      - /data/project/test_ai_botserver/router/service/video_server/voxcpm_api.py:/app/voxcpm_api.py:ro
      - /data/model_cache/huggingface:/root/.cache/huggingface
      - /data/video_tmp:/data/video_tmp
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8122/health', timeout=5)"]
      interval: 30s
      timeout: 10s
      start_period: 120s
      retries: 5
    logging:
      driver: json-file
      options:
        max-size: 200m
        max-file: "3"

  latentsync-api-2:
    image: joying/latentsync-api:h20-test
    container_name: latentsync-api-h20-test-2
    network_mode: host
    restart: unless-stopped
    command: ["/opt/latentsync-venv/bin/python", "/app/latentsync_api.py", "--host", "0.0.0.0", "--port", "8123"]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              device_ids: ["4"]
              capabilities: [gpu]
    environment:
      NVIDIA_VISIBLE_DEVICES: "4"
      NVIDIA_DRIVER_CAPABILITIES: compute,utility,video
      LATENTSYNC_DIR: /opt/LatentSync
      LATENTSYNC_USE_CONDA: "false"
      HF_HOME: /root/.cache/huggingface
      TRANSFORMERS_CACHE: /root/.cache/huggingface
      HF_ENDPOINT: https://hf-mirror.com
      TMPDIR: /data/video_tmp
      PYTHONUNBUFFERED: "1"
      LATENTSYNC_INFERENCE_TIMEOUT_SECONDS: "7200"
    volumes:
      - /data/project/test_ai_botserver/router/service/video_server/latentsync_api.py:/app/latentsync_api.py:ro
      - /data/model_cache/huggingface:/root/.cache/huggingface
      - /data/models/LatentSync-1.6:/opt/LatentSync/checkpoints
      - /data/video_tmp:/data/video_tmp
    healthcheck:
      test: ["CMD", "/opt/latentsync-venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8123/health', timeout=5)"]
      interval: 30s
      timeout: 10s
      start_period: 120s
      retries: 5
    logging:
      driver: json-file
      options:
        max-size: 200m
        max-file: "3"
```

校验 compose：

```bash
cd /data/project/test_ai_botserver
/cm/local/apps/docker/current/bin/docker compose -f deploy/docker/docker-compose.h20.yml config >/tmp/docker-compose.h20.rendered.yml
echo $?
```

预期：退出码为 `0`。

## Task 5：启动第二组容器

```bash
cd /data/project/test_ai_botserver
/cm/local/apps/docker/current/bin/docker compose -f deploy/docker/docker-compose.h20.yml up -d voxcpm-api-2 latentsync-api-2
/cm/local/apps/docker/current/bin/docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Status}}' | grep -E 'voxcpm|latentsync'
curl -s --max-time 5 http://127.0.0.1:8122/health; echo
curl -s --max-time 5 http://127.0.0.1:8123/health; echo
```

预期：四个 Docker 模型容器 healthy，`8122/8123` 返回 `{"status":"ok"}`。

## Task 6：启用第二条模型池记录

如果已有可复用记录，例如 `id=2`：

```sql
UPDATE zhugedata_test.t_comfyui_config
SET config_key = 'comfyui_url',
    config_value_audio = 'http://127.0.0.1:8122',
    config_value = 'http://127.0.0.1:8123',
    is_active = 1,
    description = 'h20 docker pair 2'
WHERE id = 2;
```

如果没有可复用记录：

```sql
INSERT INTO zhugedata_test.t_comfyui_config
  (config_key, config_value_audio, config_value, is_active, description)
VALUES
  ('comfyui_url', 'http://127.0.0.1:8122', 'http://127.0.0.1:8123', 1, 'h20 docker pair 2');
```

确认：

```sql
SELECT id, config_key, config_value_audio, config_value, is_active, description
FROM zhugedata_test.t_comfyui_config
WHERE config_key = 'comfyui_url'
ORDER BY id ASC;
```

预期：至少两条记录，一条指向 `8120/8121`，一条指向 `8122/8123`，且 `is_active=1`。

## Task 7：并发验收

提交任务前记录当前最大 id：

```sql
SELECT MAX(id) AS before_max_id
FROM zhugedata_test.t_video_generate_task;
```

让 CRM 测试环境连续提交 2 个视频任务，两个任务都走 `/crm/generate_video_task`。

只筛模型池相关日志，不要 tail 完整配置日志：

```bash
grep -nE '配置分配概览|预分配任务与配置|并发处理启动|释放配置|8122|8123' \
  /data/server_logs/supervisord/botserver_sch.out | tail -80
```

预期：

```text
并发处理启动 max_workers=2
两个任务分配到不同 config_id
一组使用 8120/8121
一组使用 8122/8123
结束后两条配置都释放回 is_active=1
```

DB 验收：

```sql
SELECT id, config_key, config_value_audio, config_value, is_active
FROM zhugedata_test.t_comfyui_config
WHERE config_key = 'comfyui_url'
ORDER BY id ASC;

SELECT id, job_id, task_id, task_status, progress, callback_status, video_url, fail_reason
FROM zhugedata_test.t_video_generate_task
ORDER BY id DESC
LIMIT 5;
```

预期：最新 5 条里能看到本次两个任务，两个任务 `task_status=3`、`progress=100`、`callback_status=1`、`video_url` 非空，模型池两条记录都回到 `is_active=1`。

## Task 8：回滚

先禁用第二条 DB 资源：

```sql
UPDATE zhugedata_test.t_comfyui_config
SET is_active = 0,
    description = CONCAT(COALESCE(description, ''), ' disabled after h20 pair2 rollback')
WHERE config_value_audio = 'http://127.0.0.1:8122'
  AND config_value = 'http://127.0.0.1:8123';
```

停止第二组容器：

```bash
cd /data/project/test_ai_botserver
/cm/local/apps/docker/current/bin/docker compose -f deploy/docker/docker-compose.h20.yml stop voxcpm-api-2 latentsync-api-2
```

如果需要恢复 compose 文件：

```bash
cd /data/project/test_ai_botserver
BACKUP=$(ls -1t deploy/docker/docker-compose.h20.yml.bak.* | head -1)
cp "$BACKUP" deploy/docker/docker-compose.h20.yml
/cm/local/apps/docker/current/bin/docker compose -f deploy/docker/docker-compose.h20.yml config >/tmp/docker-compose.h20.rollback.rendered.yml
```

预期：第一组 `8120/8121` 不受影响。

## 后续优化

本次只验证第二组多开。验证通过后再单独做：

1. 固定运维目录，不长期依赖 Jenkins 软链部署目录。
2. 镜像内置 `voxcpm_api.py` / `latentsync_api.py`，不要长期 bind mount 当前发布目录代码。
3. 端口环境变量化，Dockerfile 的 CMD 和 HEALTHCHECK 不再写死第一组端口。
4. 评估从 host network 改成 bridge + ports，靠宿主机端口映射多开。
5. 第二组稳定后，明确旧裸机 `8110/8101` 仅为回滚，不再作为默认配置。
6. 加健康巡检，不健康的模型服务自动或人工把对应 `t_comfyui_config` 置为不可领取。