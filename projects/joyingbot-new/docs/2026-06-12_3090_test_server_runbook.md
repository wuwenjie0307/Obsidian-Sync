---
date: "2026-06-12"
project: joyingbot-new
type: doc
tags: [doc, runbook, test-server, 3090, supervisor, deployment]
aliases: ["3090 测试服运行手册", "3090 test server runbook"]
---

# 3090 测试服运行手册

## 图谱链接

- 项目: [[projects/joyingbot-new/00-项目概览|joyingbot-new]]
- 索引: [[projects/joyingbot-new/docs/00-docs-index|参考文档索引]]

## 背景

2026-06-12 确认测试服已迁到一台本地 3090 机器，用户在 Windows PowerShell 中通过 `wsl` 进入 Linux 环境操作。旧 H20 路径 `/data/project/test_ai_botserver` 在新机器不存在，新测试服实际运行在 `/data/project/crm.ai.joyingbot`。

本记录作为新的测试服运维分支入口，记录服务位置、如何确认是否为最新 `test` 分支代码、如何查看日志、如何重启服务，以及 2026-06-12 10:20 任务排查线索。

## 结论

- 代码目录: `/data/project/crm.ai.joyingbot`
- 当前服务进程由 `supervisor` 管理。
- `ai_botserver` 运行接口服务，端口参数为 `--port=8017`。
- `ai_botserver_sch` 运行调度服务，端口参数为 `--port=18017`。
- 2026-06-12 已确认本机 `test` 分支与 GitLab `origin/test` 一致:
  - commit: `81374ebe`
  - commit message: `Merge branch 'phone_activate_bug' into test`
  - commit time: `2026-06-12 09:18:18 +0800`
  - `git rev-list --left-right --count HEAD...origin/test` 输出 `0 0`
- 已重启服务加载该版本:
  - `ai_botserver` 新 PID: `282083`
  - `ai_botserver_sch` 新 PID: `282084`

## 登录与基础操作

在 Windows PowerShell 中进入 WSL:

```powershell
wsl
```

进入项目目录:

```bash
cd /data/project/crm.ai.joyingbot
```

查看机器上的项目目录:

```bash
ls -lah /data
ls -lah /data/project
```

已观察到的新机器目录包括:

```text
/data/project/crm.ai.admin
/data/project/crm.ai.joyingbot
/data/project/video_server_model_overseas
/data/server_logs
```

## Supervisor 服务

查看服务状态:

```bash
sudo supervisorctl status
```

已观察到的服务:

```text
ai_admin
ai_botserver
ai_botserver_sch
```

查看指定服务 PID:

```bash
sudo supervisorctl pid ai_botserver
sudo supervisorctl pid ai_botserver_sch
```

确认服务实际运行目录:

```bash
sudo readlink -f /proc/$(sudo supervisorctl pid ai_botserver)/cwd
sudo readlink -f /proc/$(sudo supervisorctl pid ai_botserver_sch)/cwd
```

期望输出:

```text
/data/project/crm.ai.joyingbot
/data/project/crm.ai.joyingbot
```

查看启动命令:

```bash
sudo tr '\0' ' ' < /proc/$(sudo supervisorctl pid ai_botserver)/cmdline; echo
sudo tr '\0' ' ' < /proc/$(sudo supervisorctl pid ai_botserver_sch)/cmdline; echo
```

已观察到的启动命令:

```text
/data/server/anaconda3/envs/botserver/bin/python app_server_api.py --env=dev --jobStatus=false --port=8017
/data/server/anaconda3/envs/botserver/bin/python app_server_sch.py --env=dev --jobStatus=true --port=18017
```

查看进程启动时间:

```bash
ps -p $(sudo supervisorctl pid ai_botserver) -o pid,lstart,cmd
ps -p $(sudo supervisorctl pid ai_botserver_sch) -o pid,lstart,cmd
```

## 判断是否为最新 test 分支代码

进入项目目录:

```bash
cd /data/project/crm.ai.joyingbot
```

查看远端、分支和工作区:

```bash
git remote -v
git status -sb
git branch --show-current
```

已观察到远端:

```text
origin git@git.joyingai.cn:services/crm.ai.joyingbot.git
```

拉取最新 `test` 状态:

```bash
git fetch origin test --prune
```

对比本地与远端:

```bash
echo "HEAD:        $(git rev-parse --short HEAD)"
echo "origin/test: $(git rev-parse --short origin/test)"
git log -1 --format='HEAD commit:        %h %ci %s'
git log -1 origin/test --format='origin/test commit: %h %ci %s'
git rev-list --left-right --count HEAD...origin/test
```

判断规则:

```text
0 0 = 本地就是最新 origin/test
0 N = 本地落后 origin/test，需要拉代码
N 0 = 本地有远端 test 没有的提交
N M = 本地和 origin/test 分叉
```

如果 `git fetch` 报错 `Could not resolve hostname git.joyingai.cn`，说明当前机器 DNS 或网络不能访问 GitLab。此时只能证明本机代码等于上一次成功拉取到的 `origin/test`，不能证明等于 GitLab 当前最新 `test`。

网络恢复后重新执行:

```bash
git fetch origin test --prune
git rev-list --left-right --count HEAD...origin/test
```

## 更新代码并重启服务

如果本地落后远端，并且没有需要保留的本地改动，更新:

```bash
cd /data/project/crm.ai.joyingbot
git pull --ff-only origin test
```

重启接口服务和调度服务:

```bash
sudo supervisorctl restart ai_botserver ai_botserver_sch
sudo supervisorctl status
```

重启后再次确认运行目录:

```bash
sudo readlink -f /proc/$(sudo supervisorctl pid ai_botserver)/cwd
sudo readlink -f /proc/$(sudo supervisorctl pid ai_botserver_sch)/cwd
```

注意: 仅确认 Git 目录最新还不够，还需要确认正在运行的进程 `cwd` 指向该目录，并且进程启动时间晚于代码更新/拉取时间。

## 查看日志

主日志目录:

```bash
/data/server_logs/supervisord
```

查看日志文件:

```bash
cd /data/server_logs/supervisord
ls -lh
```

实时查看接口服务日志:

```bash
tail -n 200 -f /data/server_logs/supervisord/ai_botserver.out
```

按时间查日志。示例: 查 2026-06-12 10:20 附近:

```bash
grep -RniC 80 "2026-06-12.*10:20" /data/server_logs/supervisord
grep -RniC 80 "10:20:" /data/server_logs/supervisord
```

按任务查日志。示例: 查 `job_id=1216` / `task_id=1190`:

```bash
grep -RniC 80 "job_id=1216\|task_id=1190\|1190\|1216" /data/server_logs/supervisord
grep -Rni "job_id=1216\|task_id=1190\|1190\|1216" /data/server_logs/supervisord | tail -n 300
```

查错误:

```bash
grep -RniC 80 "error\|exception\|traceback\|failed\|失败" /data/server_logs/supervisord
```

## 2026-06-12 10:20 任务排查记录

已从日志看到 10:20 的任务进入接口链路:

```text
job_id=1216
task_id=1190
templates_style_id=2
```

关键时间线:

```text
10:20:33 /crm/rewrite_video_desc 200
10:20:40 拉取 CRM 工作组 job_id=1216
10:20:41 拉取素材任务 task_id=1190
10:20:42 同步数据完成并提交数据库 tasks=1
10:20:42 /crm/generate_video_task 200
10:20:42 异步处理开始 job_id=1216 task_id=1190
10:20:42 materialSubtitleCallback 回调成功 resp_code=200
10:20:42 异步处理结束 cost_ms=190
```

这证明接口侧任务同步、数据写入和字幕回调成功。若要确认视频是否真正生成完成，需要继续查调度进程 `ai_botserver_sch` 是否捞到并处理 `task_id=1190`。

相关素材字段:

```text
imagery_video=https://files.joyingai.cn/crm/20260605/user4_1780637795609_4832260309e54bcb.mp4
cover_image_url=https://videos-test.joyingai.cn/video/crm/20260612/user4_1781230829124_a2a09c11fb1eca03.png
hot_video_audio_url=https://videos.joyingai.cn/video/crm/bgm/调频/舒缓-Sunrise-new.mp3
```

同时看到一条看似无关的外部 CRM 超时:

```text
10:21:29 /crm/open_wechat_accounts 500
crm2.yunkecn.com/open/wechat/accounts connect timeout
10:25:28 之后 /crm/open_wechat_accounts 连续返回 200
```

初步判断该错误更像外部 CRM 网络短暂超时，不是 10:20 视频生成任务主链路。

## VoxCPM 音色 Docker 服务

2026-06-12 继续确认 3090 上的音色服务。昨天的音频修正主要在 VoxCPM 服务代码中，不是只重启 `ai_botserver` 就能生效。

相关修复标记:

```text
VOICE_OUTPUT_TARGET_PEAK = 0.92
def limit_audio_peak(...)
audio = limit_audio_peak(audio)
```

宿主机代码位置:

```bash
/data/project/crm.ai.joyingbot/router/service/video_server/voxcpm_api.py
```

确认宿主机代码是否包含音频修复:

```bash
cd /data/project/crm.ai.joyingbot
git fetch origin test --prune
git rev-list --left-right --count HEAD...origin/test
grep -n 'VOICE_OUTPUT_TARGET_PEAK\|limit_audio_peak' router/service/video_server/voxcpm_api.py
```

2026-06-12 已确认宿主机 `test` 最新，且文件包含修复标记:

```text
345:VOICE_OUTPUT_TARGET_PEAK = 0.92
348:def limit_audio_peak(audio: np.ndarray, target_peak: float = VOICE_OUTPUT_TARGET_PEAK) -> np.ndarray:
370:    audio = limit_audio_peak(audio)
```

3090 当前只有一个 VoxCPM 容器:

```text
container: voxcpm-api-h20-test
image: joying/voxcpm-api:h20-test
host port: 7001
container port: 8105
health: http://127.0.0.1:7001/health
```

查看容器:

```bash
docker ps --format '{{.ID}} {{.Names}} {{.Image}} {{.Ports}}' | grep -i voxcpm
```

已观察到端口映射:

```text
0.0.0.0:7001->8105/tcp
```

容器启动命令:

```bash
docker exec voxcpm-api-h20-test sh -lc 'tr "\0" " " < /proc/1/cmdline; echo; readlink -f /proc/1/cwd'
```

已观察到:

```text
python /app/voxcpm_api.py --host 0.0.0.0 --port 8105
/app
```

容器挂载:

```bash
docker inspect voxcpm-api-h20-test --format '{{range .Mounts}}{{.Type}} {{.Source}} -> {{.Destination}}{{println}}{{end}}'
```

已确认是单文件 bind mount:

```text
bind /data/project/crm.ai.joyingbot/router/service/video_server/voxcpm_api.py -> /app/voxcpm_api.py
bind /data/video_tmp -> /data/video_tmp
bind /data/model_cache/huggingface -> /root/.cache/huggingface
```

这意味着: 宿主机拉到最新代码后，VoxCPM 容器需要重启，才能重新挂载并加载最新 `/app/voxcpm_api.py`。

2026-06-12 重启前曾出现容器内 `/app/voxcpm_api.py` 异常:

```text
ls: cannot access '/app/voxcpm_api.py': No such file or directory
-????????? ? ? ? ? ? voxcpm_api.py
```

这是单文件 bind mount 在宿主机 Git 更新后常见的旧 inode/挂载异常表现。服务进程可能仍在内存中运行，但不能据此确认已经加载新代码。

重启 VoxCPM 音色容器:

```bash
docker restart voxcpm-api-h20-test
```

重启后验证:

```bash
docker ps --filter name=voxcpm-api-h20-test --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
curl -sS --connect-timeout 2 --max-time 20 http://127.0.0.1:7001/health
docker exec voxcpm-api-h20-test sh -lc 'ls -lah /app; grep -n "VOICE_OUTPUT_TARGET_PEAK\|limit_audio_peak" /app/voxcpm_api.py'
```

2026-06-12 已完成重启并验证:

```text
/app/voxcpm_api.py 文件恢复正常
345:VOICE_OUTPUT_TARGET_PEAK = 0.92
348:def limit_audio_peak(audio: np.ndarray, target_peak: float = VOICE_OUTPUT_TARGET_PEAK) -> np.ndarray:
370:    audio = limit_audio_peak(audio)
http://127.0.0.1:7001/health -> {"status":"ok"}
```

结论:

```text
3090 VoxCPM Docker 音色服务已经加载昨天的音频修正。
后续修改 router/service/video_server/voxcpm_api.py 后，需要重启 voxcpm-api-h20-test，并验证容器内 /app/voxcpm_api.py 的标记和 7001/health。
```

注意:

- `sudo supervisorctl restart ai_botserver ai_botserver_sch` 只重启 Bot 接口和调度服务，不会让 VoxCPM Docker 音色服务加载新代码。
- 这台 3090 的 VoxCPM 健康检查走 `7001/health`，不是旧 H20 记录里的 `8120/health`。
- `docker ps` 里的 `health: starting` 或短暂 `connection reset by peer` 可能是模型刚启动时的暂态；最终以 `http://127.0.0.1:7001/health -> {"status":"ok"}` 为准。

## 2026-06-12 11:53 排队加速中排查

现场现象: 用户在 3090 测试服前端发布一个视频任务后，页面一直显示“排队加速中”。需要判断是前面有任务正在生成、scheduler 没捞到任务、模型池被占用，还是任务状态没有刷新。

第一步先找到 11:53 左右新任务的 `job_id` / `task_id`:

```bash
grep -RniC 80 -E "2026-06-12 11:5[0-9]|12/Jun/2026 11:5[0-9]|generate_video_task|job_id=|task_id=" \
  /data/server_logs/supervisord /data/project/crm.ai.joyingbot/logs 2>/dev/null | tail -n 500
```

如果已经知道任务 ID，用任务 ID 精确查:

```bash
grep -RniC 120 -E "job_id=JOB_ID|task_id=TASK_ID|JOB_ID|TASK_ID|处理任务|待生成|生成开始|生成完成|失败|ERROR|Exception" \
  /data/server_logs/supervisord /data/project/crm.ai.joyingbot/logs 2>/dev/null | tail -n 800
```

实时观察接口和 scheduler:

```bash
tail -f /data/server_logs/supervisord/ai_botserver.out /data/project/crm.ai.joyingbot/logs/run.log \
  | grep --line-buffered -E "generate_video_task|job_id|task_id|待生成|处理任务|生成开始|生成完成|videos-test|callback|失败|ERROR|Exception"
```

查看 scheduler 是否还活着:

```bash
sudo supervisorctl status ai_botserver_sch
pid=$(sudo supervisorctl pid ai_botserver_sch)
echo "ai_botserver_sch pid=$pid"
sudo readlink -f "/proc/$pid/cwd"
sudo tr '\0' ' ' < "/proc/$pid/cmdline"; echo
ps -p "$pid" -o pid,lstart,cmd
```

查看最近 scheduler 扫描情况:

```bash
tail -n 300 /data/project/crm.ai.joyingbot/logs/run.log | grep -E "待生成|无待生成|处理任务|task_status|模型池|comfyui|config_id|is_active|生成开始|生成完成|失败|ERROR|Exception"
```

判断口径:

```text
1. ai_botserver.out 有 /crm/generate_video_task 200
   = 前端任务已经同步到后端。

2. run.log 能看到对应 task_id 的“处理任务/生成开始”
   = scheduler 已经捞到任务，继续看生成阶段日志。

3. run.log 一直没有对应 task_id，但有“无待生成任务”
   = 可能任务未入库、状态不是 0、字幕/描述前置条件不满足，或页面显示的是 CRM 侧排队状态。

4. run.log 有其它 task_id 正在生成，当前 task_id 尚未开始
   = 当前排队是正常的，需要等前一个任务释放模型池。

5. 模型池 is_active 长时间为 2，且没有对应任务继续产生日志
   = 可能模型池锁或任务卡住，需要进一步查 DB 和模型服务。
```

如果需要看模型服务是否可用:

```bash
curl -sS --connect-timeout 2 --max-time 8 http://127.0.0.1:7001/health
docker ps --format '{{.Names}} {{.Status}} {{.Ports}}' | grep -i voxcpm
```

注意: 当前 3090 只有一个 VoxCPM 容器 `voxcpm-api-h20-test`，音色健康检查走 `7001/health`。完整视频生成还可能依赖视频/口型服务，不能只看 VoxCPM。

## 常用一键检查脚本

```bash
cd /data/project/crm.ai.joyingbot || exit 1

echo "== Git =="
git fetch origin test --prune
echo "branch: $(git branch --show-current)"
echo "HEAD:        $(git rev-parse --short HEAD)"
echo "origin/test: $(git rev-parse --short origin/test)"
git log -1 --format='%h %ci %s'
git rev-list --left-right --count HEAD...origin/test

echo
echo "== Supervisor =="
sudo supervisorctl status

echo
echo "== Runtime =="
for svc in ai_botserver ai_botserver_sch; do
  pid=$(sudo supervisorctl pid "$svc")
  echo "$svc pid=$pid"
  sudo readlink -f "/proc/$pid/cwd"
  sudo tr '\0' ' ' < "/proc/$pid/cmdline"; echo
  ps -p "$pid" -o pid,lstart,cmd
  echo
done
```

## 相关记录

- 2026-06-12 会话中确认新 3090 测试服路径与运行态。
- [[projects/joyingbot-new/bugs/2026-06-12_3090_mix_flag_and_subtitle_rewrite_db|3090 混剪标记与字幕二创失败排查]]
- 旧 H20 路径 `/data/project/test_ai_botserver` 不适用于这台新机器。

## 2026-06-12 16:03-17:03 任务同步、6001 进度与方向元数据排查

### job_id=1224 / task_id=1198：前端失败但本地未入队

现象：前端显示任务失败或排队异常，但 scheduler 一直打印“待生成任务数: 0 / task_status=0 的任务数=0”。

排查结论：

```text
3090 服务连接的 MySQL: 222.71.55.27:3306 / zhugedata_test
本地生成任务表 t_video_generate_task 一开始没有 job_id=1224 / task_id=1198
本地素材表 t_video_material_template 一开始也没有该 task
CRM generateTaskList 实际能返回 task_id=1198，素材接口也能返回 material_id=666
手动重打 /crm/generate_video_task 后 synced_tasks=1 / synced_materials=1
```

关键命令：

```bash
cd /data/project/crm.ai.joyingbot

/data/server/anaconda3/envs/botserver/bin/python - <<'PY'
import json
from pathlib import Path
cfg = json.loads(Path("config/config-dev.json").read_text(encoding="utf-8"))
print("mysql_host:", cfg.get("mysql_connection_ip"))
print("mysql_port:", cfg.get("mysql_connection_port"))
print("mysql_db:", cfg.get("mysql_connection_database"))
PY
```

查询本地/A800 测试库是否落库：

```bash
/data/server/anaconda3/envs/botserver/bin/python - <<'PY'
import json
from pathlib import Path
import mysql.connector
cfg = json.loads(Path("config/config-dev.json").read_text(encoding="utf-8"))
conn = mysql.connector.connect(
    host=cfg["mysql_connection_ip"],
    port=int(cfg["mysql_connection_port"]),
    user=cfg["mysql_connection_username"],
    password=cfg["mysql_connection_password"],
    database=cfg["mysql_connection_database"],
)
cur = conn.cursor(dictionary=True)
cur.execute("select id, job_id, task_id, task_status, progress, fail_reason, created_time, updated_time from t_video_generate_task where job_id=1224 or task_id=1198 order by id desc")
print("tasks:", cur.fetchall())
cur.execute("select id, job_id, task_id, material_id, material_type, material_source_url, is_mix_material from t_video_material_template where job_id=1224 or task_id=1198 order by id desc")
print("materials:", cur.fetchall())
cur.close(); conn.close()
PY
```

手动重新同步任务：

```bash
curl -sS -X POST http://127.0.0.1:8017/crm/generate_video_task \
  -H 'Content-Type: application/json' \
  -d '{"job_id":1224}'
```

成功返回：

```json
{"code":200,"data":{"job_id":1224,"synced_materials":1,"synced_tasks":1},"success":true}
```

后续判断：

```text
task_status=0: scheduler 待捞取
task_status=1: 已进入生成中，video_work 已回调 CRM task_status=1
task_status=2: 合成阶段继续推进中
task_status=3: 本地生成完成
task_status=4: 本地失败，通常已经向 CRM 回调 task_status=-1
```

### 1198：6001 合成进度排查

1198 同步后进入生成流程，关键阶段：

```text
16:53:02 提交到 http://127.0.0.1:6001/easy/submit
16:53:09 进度 5%
16:53:10 进度 20%
16:58:20 进度 80%
16:58:26 进度 100% 状态仍为 1
16:58:28 状态变为 2，结果 /1198-r.mp4
16:58:30 bt709 color metadata fixed
16:58:43 standardize_9x16_30fps 成功
16:58:47 上传成片成功
16:58:55 Whisper 字幕生成成功
16:58:56 找到混剪图片插入时间段 (26.36, 42.24)
16:59:02 开始 ffmpeg overlay 图片混剪
```

查看 6001 当前任务状态：

```bash
curl -sS "http://127.0.0.1:6001/easy/query?code=1198"
```

查看 6001/HeyGem 相关进程：

```bash
ps -ef | grep -E "1198|ffmpeg|video_work|app_server_sch|python" | grep -v grep
```

若进度卡住但 `python /code/app_local.py` CPU 仍在跑，通常表示 6001 仍在生成；若无进程且 DB 仍停在 `task_status=1/2`，再查异常日志与最终回调。

### job_id=1227 / task_id=1200：混剪方向元数据失败

失败日志：

```text
1200 [混剪方向归一化] 处理完成: input=/tmp/tmp_ia7axxt.mp4, output=/tmp/tmp_ia7axxt_oriented.mp4, width=1920, height=1080, rotate=90, filter=transpose=1
RuntimeError: 1200 orientation bake output still has rotation metadata: path=/tmp/tmp_ia7axxt_oriented.mp4, size=1080x1920, rotate=90
```

结论：画面像素已经通过 `transpose=1` 转成竖屏 `1080x1920`，但输出 mp4 仍残留 `rotate=90` metadata，导致 `_validate_orientation_bake_output` 判定失败。该问题不是 6001 服务卡住，也不是任务队列问题，而是 `router/service/video_server2/video_time_align.py` 的方向归一化后处理不完整。

已修复并合并：

```text
个人分支: feature/ai_v6.3.1_video
合并目标: test
远端提交: 2019a93c4445b8195a3c2cf327367b7859604542
commit: 284527b1 fix: clear baked video rotation metadata
验证: python -m unittest test.test_llm_json_cleanup test.test_video_time_align_orientation test.test_voxcpm_voice_style_prompt
结果: Ran 35 tests OK (skipped=2)
```

3090 更新部署：

```bash
cd /data/project/crm.ai.joyingbot
git pull origin test
sudo supervisorctl restart ai_botserver_sch
sudo supervisorctl status ai_botserver_sch
```

部署后可重试 `job_id=1227 / task_id=1200`。

## 2026-06-12 18:34 job_id=1229 / task_id=1202：scheduler 重启导致生成中卡住

现象：3090 测试服 `job_id=1229 / task_id=1202` 前端长时间停在生成中。`run.log` 显示任务已进入 6001 视频生成轮询，进度从 0% 到 20% 后停住；随后 `ai_botserver_sch` 在 18:36:26 被重启，打断了正在等待 6001 结果的 Python 调用链。

关键判断：

```bash
curl -sS "http://127.0.0.1:6001/easy/query?code=1202"
```

一开始 6001 返回：

```json
{
  "code": 10000,
  "data": {
    "code": "1202",
    "msg": "任务完成",
    "progress": 100,
    "result": "/1202-r.mp4",
    "status": 2,
    "video_duration": 39520,
    "width": 720,
    "height": 1280
  },
  "success": true
}
```

但 `run.log` 没有后续：

```text
任务完成! 结果: /1202-r.mp4
正在下载视频到本地
视频下载成功
回调完成
```

因此判断不是 6001 卡住，而是 scheduler 重启后没人继续下载 `/1202-r.mp4` 并回调 CRM。

DB 状态确认：

```bash
cd /data/project/crm.ai.joyingbot

/data/server/anaconda3/envs/botserver/bin/python - <<'PY'
import json
from pathlib import Path
import mysql.connector

cfg = json.loads(Path("config/config-dev.json").read_text(encoding="utf-8"))
conn = mysql.connector.connect(
    host=cfg["mysql_connection_ip"],
    port=int(cfg["mysql_connection_port"]),
    user=cfg["mysql_connection_username"],
    password=cfg["mysql_connection_password"],
    database=cfg["mysql_connection_database"],
)
cur = conn.cursor(dictionary=True)
cur.execute("""
select id, job_id, task_id, task_status, progress, fail_reason,
       generate_video_url, callback_status, updated_time
from t_video_generate_task
where task_id=1202 or job_id=1229
""")
print(cur.fetchall())
cur.close()
conn.close()
PY
```

当时结果：

```text
id=1418
job_id=1229
task_id=1202
task_status=2
progress=0
generate_video_url=''
callback_status=0
```

恢复步骤：

1. 将任务重置回待生成：

```bash
/data/server/anaconda3/envs/botserver/bin/python - <<'PY'
import json
from pathlib import Path
import mysql.connector

cfg = json.loads(Path("config/config-dev.json").read_text(encoding="utf-8"))
conn = mysql.connector.connect(
    host=cfg["mysql_connection_ip"],
    port=int(cfg["mysql_connection_port"]),
    user=cfg["mysql_connection_username"],
    password=cfg["mysql_connection_password"],
    database=cfg["mysql_connection_database"],
)
cur = conn.cursor()
cur.execute("""
update t_video_generate_task
set task_status = 0,
    progress = 0,
    fail_reason = '',
    callback_status = 0,
    updated_time = now()
where id = 1418
  and job_id = 1229
  and task_id = 1202
  and task_status = 2
  and generate_video_url = ''
""")
conn.commit()
print("updated rows:", cur.rowcount)
cur.close()
conn.close()
PY
```

本次输出：

```text
updated rows: 1
```

2. scheduler 随后能看到待生成任务，但配置池不可用：

```text
[定时任务2] 待生成任务数: 1
[定时任务2] 可用配置数: 0
[定时任务2] 没有可用配置（is_active=1），跳过处理，等待下一次执行
```

原因：`config_id=16` 在任务被重启打断时未释放，仍为 `is_active=2`。

查询配置表真实字段：

```bash
/data/server/anaconda3/envs/botserver/bin/python - <<'PY'
import json
from pathlib import Path
import mysql.connector

cfg = json.loads(Path("config/config-dev.json").read_text(encoding="utf-8"))
conn = mysql.connector.connect(
    host=cfg["mysql_connection_ip"],
    port=int(cfg["mysql_connection_port"]),
    user=cfg["mysql_connection_username"],
    password=cfg["mysql_connection_password"],
    database=cfg["mysql_connection_database"],
)
cur = conn.cursor(dictionary=True)
cur.execute("""
select id, config_key, config_value, config_value_audio, description,
       is_active, type, created_time, updated_time
from t_comfyui_config
where id=16
""")
print(cur.fetchall())
cur.close()
conn.close()
PY
```

当时结果：

```text
id=16
config_key=comfyui_url
config_value=http://127.0.0.1:6001
config_value_audio=http://127.0.0.1:7001
is_active=2
type=1
```

3. 确认没有进程正在处理该任务后释放配置：

```bash
ps -ef | grep -E "1202|video_work|video_gen_service|ffmpeg|python" | grep -v grep
curl -sS "http://127.0.0.1:6001/easy/query?code=1202"
```

旧 6001 任务后来返回 `任务不存在`，说明旧结果已经清掉；可以重新提交完整链路。

释放 `config_id=16`：

```bash
/data/server/anaconda3/envs/botserver/bin/python - <<'PY'
import json
from pathlib import Path
import mysql.connector

cfg = json.loads(Path("config/config-dev.json").read_text(encoding="utf-8"))
conn = mysql.connector.connect(
    host=cfg["mysql_connection_ip"],
    port=int(cfg["mysql_connection_port"]),
    user=cfg["mysql_connection_username"],
    password=cfg["mysql_connection_password"],
    database=cfg["mysql_connection_database"],
)
cur = conn.cursor()
cur.execute("""
update t_comfyui_config
set is_active = 1,
    updated_time = now()
where id = 16
  and is_active = 2
""")
conn.commit()
print("updated rows:", cur.rowcount)
cur.close()
conn.close()
PY
```

本次输出：

```text
updated rows: 1
```

4. 释放后 scheduler 下一轮重新领取成功：

```text
18:54:25 [定时任务2] 配置分配概览: 任务数=1 可用配置数=1 本轮实际分配任务数=1
18:54:25 [定时任务2] 预分配任务与配置: job_id=1229 task_id=1202 config_id=16 voxcpm_api_base=http://127.0.0.1:7001 heygem_video_domain=http://127.0.0.1:6001
18:54:26 [处理任务-标记生成中] job_id=1229 task_id=1202 数据库更新成功
18:54:27 [处理任务-生成开始] job_id=1229 task_id=1202
18:54:36 [定时任务2] 待生成任务数: 0
```

排查命令模板：

```bash
grep -nE "待生成任务数|可用配置数|预分配任务与配置|job_id=JOB_ID|task_id=TASK_ID|任务 TASK_ID|任务完成|正在下载视频|回调完成|失败|异常|ERROR|Exception" \
  /data/project/crm.ai.joyingbot/logs/run.log \
  | tail -n 120

curl -sS "http://127.0.0.1:6001/easy/query?code=TASK_ID"

/data/server/anaconda3/envs/botserver/bin/python - <<'PY'
# 查询 t_video_generate_task 与 t_comfyui_config 状态，按上方脚本替换 TASK_ID / JOB_ID / config_id
PY
```

注意事项：

- 视频任务已经进入 6001 轮询后，不要重启 `ai_botserver_sch`；重启会杀掉等待 6001 完成、下载结果、后处理、回调 CRM 的调用链。
- 如果必须重启 scheduler，重启后要检查是否有任务卡在 `task_status=1/2` 且 `generate_video_url=''`，并检查 `t_comfyui_config.is_active` 是否卡在 `2`。
- `t_video_generate_task` 的结果字段是 `generate_video_url`，不是 `generate_video_source_url`。
- `t_comfyui_config` 的字段是 `config_key/config_value/config_value_audio/is_active/type/created_time/updated_time`，没有 `config_name/status/updated_at`。
- 释放配置前先确认没有对应任务进程在跑，避免把正在使用的模型配置误标为空闲。

## 2026-06-12 19:09 / 19:11 两个任务：一个排队未入库，一个卡声音克隆

背景：用户在 3090 测试服连续提交两个视频任务：第一个约 19:09 提交后前端显示“正在排队”；第二个约 19:11 提交后马上开始执行，但随后卡在声音克隆阶段。用户明确要求先不要手动同步第一个任务，因为不能把“手动同步”变成常规处理方式。

已确认事实：

1. 按日志时间段提取 `job_id/task_id`：

```bash
grep -nE "2026-06-12 19:0[8-9]|2026-06-12 19:1[0-2]" logs/run.log \
  | grep -oE "job_id[=:] ?[0-9]+|task_id[=:] ?[0-9]+" \
  | sort | uniq -c
```

输出中只明确看到第二个任务：

```text
19 job_id=1231
17 task_id=1204
1 task_id: 1204
```

还有一批历史/无关 `job_id=622/623/624/625/656/657/658/659` 与 `task_id=698/699/700/701/732/733/734/735`，不是本次 19:09/19:11 新任务主线。

2. DB 时间是 UTC，日志时间是北京时间。查询北京时间 19:08-19:13 对应 DB `created_time` 要用 `2026-06-12 11:08:00` 到 `11:13:00`。

查询脚本：

```bash
cd /data/project/crm.ai.joyingbot

/data/server/anaconda3/envs/botserver/bin/python - <<'PY'
import json
from pathlib import Path
import mysql.connector

cfg = json.loads(Path("config/config-dev.json").read_text(encoding="utf-8"))
conn = mysql.connector.connect(
    host=cfg["mysql_connection_ip"],
    port=int(cfg["mysql_connection_port"]),
    user=cfg["mysql_connection_username"],
    password=cfg["mysql_connection_password"],
    database=cfg["mysql_connection_database"],
)
cur = conn.cursor(dictionary=True)
cur.execute("""
select id, job_id, task_id, task_status, progress, fail_reason,
       generate_video_url, callback_status, created_time, updated_time
from t_video_generate_task
where created_time >= '2026-06-12 11:08:00'
  and created_time <= '2026-06-12 11:13:00'
order by id
""")
for r in cur.fetchall():
    print(r)
cur.close()
conn.close()
PY
```

结果只有第二个任务：

```text
id=1419
job_id=1231
task_id=1204
task_status=1
progress=0
fail_reason=''
generate_video_url=''
callback_status=1
created_time=2026-06-12 11:11:42
updated_time=2026-06-12 11:11:59
```

结论：19:11 的第二个任务已入 `t_video_generate_task` 并开始执行；19:09 的第一个任务没有出现在该时间段 DB 查询结果里，也没有在 `run.log` 19:08-19:12 中明确出现新 `job_id/task_id`。它更像是停在 CRM/前端侧，尚未稳定同步到 3090 botserver 本地任务表。不要急着手动 `POST /crm/generate_video_task`，应先查触发链路。

当前未完成排查 1：第一个 19:09 任务为什么未入库

需要查 admin 是否收到创建请求：

```bash
grep -nE "2026-06-12 19:08|2026-06-12 19:09|2026-06-12 19:10" \
  /data/server_logs/supervisord/ai_admin.out \
  | grep -E "创建视频生成任务接口|接收到的传参|job_id|generate_video_task|ERROR|Exception" \
  | tail -n 200
```

再查 botserver 是否收到 `/crm/generate_video_task` 或同步动作：

```bash
grep -nE "2026-06-12 19:08|2026-06-12 19:09|2026-06-12 19:10" \
  /data/server_logs/supervisord/ai_botserver.out /data/project/crm.ai.joyingbot/logs/run.log \
  | grep -E "generate_video_task|获取crm视频工作组列表|获取crm视频素材|job_id|task_id|同步|失败|异常|ERROR|Exception" \
  | tail -n 300
```

判断口径：

- `ai_admin.out` 没有第一条请求：前端/CRM 没打到 3090。
- `ai_admin.out` 有请求，但 botserver/run.log 没有同步：admin 到 botserver 的触发链路有问题。
- botserver 有同步请求但 DB 没入：`generate_video_task` 内部拉 CRM 工作组/素材失败或数据条件不满足。
- DB 有任务但 `task_status=0`：scheduler 或配置池问题。

当前未完成排查 2：第二个 `job_id=1231 / task_id=1204` 卡声音克隆

用户反馈：`1204` 已开始执行，但卡在声音克隆阶段很久。该任务正在占用模型配置时会影响后续任务排队，因此比第一个未入库任务更紧急。

先查 botserver/scheduler 日志中的 VoxCPM 阶段：

```bash
grep -nE "job_id=1231|task_id=1204|1204" /data/project/crm.ai.joyingbot/logs/run.log \
  | grep -E "voice|VoxCPM|voxcpm|音色|克隆|reference_audio|whisper|voxcpm_api|voxcpm_clone|生成开始|失败|异常|ERROR|Exception|video_perf" \
  | tail -n 200
```

再查 VoxCPM 容器日志：

```bash
docker logs --tail 200 voxcpm-api-h20-test \
  | grep -E "VoxCPM|1204|合成|分段|语速后处理|音频后处理|ERROR|Exception|Traceback"
```

确认 VoxCPM 服务健康：

```bash
curl -i --connect-timeout 2 --max-time 20 http://127.0.0.1:7001/health
docker ps --filter name=voxcpm-api-h20-test --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
```

如果日志显示 `调用 VoxCPM API` 后长期没有 `voxcpm_api success` / `voxcpm_clone success`，基本是 VoxCPM 合成慢或卡住。此时不要直接重启 scheduler；先确认 VoxCPM 容器是否仍在处理、GPU 是否有负载：

```bash
nvidia-smi
ps -ef | grep -E "1204|voxcpm|ffmpeg|python" | grep -v grep
```

注意：刚刚 18:34 的 `1202` 事故已经证明，视频任务进入生成链路后重启 `ai_botserver_sch` 会打断等待 6001 完成、下载结果、后处理、回调 CRM 的调用链，并可能导致 `t_comfyui_config.is_active=2` 不释放。因此排查 `1204` 时优先查日志和容器/GPU，不要先重启 scheduler。

相关运行信息：

- 3090 项目目录：`/data/project/crm.ai.joyingbot`
- 主日志：`/data/project/crm.ai.joyingbot/logs/run.log`
- scheduler stdout：`/data/server_logs/supervisord/botserver_sch.out`
- botserver stdout：`/data/server_logs/supervisord/ai_botserver.out`
- admin stdout：`/data/server_logs/supervisord/ai_admin.out`
- VoxCPM 容器：`voxcpm-api-h20-test`
- VoxCPM health：`http://127.0.0.1:7001/health`
- 6001 视频服务：`duix-avatar-gen-video-1`，`http://127.0.0.1:6001`
- 当前已知模型配置：`t_comfyui_config.id=16`，`config_value=http://127.0.0.1:6001`，`config_value_audio=http://127.0.0.1:7001`

## 2026-06-12 19:09 job_id=1230 / task_id=1203：同步中途被服务重启打断，未入库

现象：
- 前端 19:09 提交第一个视频任务后显示排队。
- admin 收到创建请求：`job_id=1230`。
- botserver 日志只看到两步：
  - `获取crm视频工作组列表` 成功，`id=1230`。
  - `获取crm视频素材库列表(新接口)` 成功，素材里有 `task_id=1203`。
- 后续没有 `get_crm_video_generate_task_list` / 任务列表同步日志，没有 `[generate_video_task][同步数据]`，也没有接口返回日志。
- DB 查询 `t_video_generate_task where job_id=1230 or task_id=1203` 为空；`t_video_material_template where job_id=1230 or task_id=1203` 也为空。

关键证据：
- `ai_botserver` 和 `ai_botserver_sch` 当前进程均为 `2026-06-12 19:13:48` 启动。
- supervisor 主日志显示 `2026-06-12 19:12:07` 对 `ai_botserver_sch` 执行了 SIGKILL，随后同时 spawned `ai_botserver` 与 `ai_botserver_sch`。
- InnoDB 最近一次 deadlock 是 `2026-06-10 11:17:44`，表为 `t_agent_chat_record_room`，与本次视频任务表无关。

阶段性结论：
- 本次不是 3090 因资源吃紧/OOM 自动重启的证据链。
- 更像人工或部署脚本触发 supervisor 重启，打断了 `/crm/generate_video_task` 同步请求。
- 因该接口最后统一 commit，重启前未提交，导致 job/material/task 都没有落本地库，前端仍显示排队。
- 但 `1230` 从 19:09:28 到 19:12:07 之间没有继续进入任务列表同步，也说明同步链路缺少阶段日志和超时保护，需要补偿机制而不是依赖人工同步。

处理建议：
1. 止血：不要把手动 `/crm/generate_video_task` 当常规方案；只在确认任务未入库且没有运行中生成链路时作为救援。
2. 代码补偿：增加一个定时补偿逻辑，扫描 CRM 已创建但本地 `t_video_generate_task` 缺失的 job/task，自动重新执行同步。
3. 同步接口增强：在 `/crm/generate_video_task` 增加 material 入库前后、task list 调用前后、commit 前后日志，并捕获 DB/CRM 异常返回明确失败。
4. 重启安全：部署/重启前检查 `task_status in (0,1,2)`、`t_comfyui_config.is_active=2`、以及近期 `/crm/generate_video_task` 请求，避免直接 SIGKILL 打断同步/生成链路。
5. 后续根因：继续查 19:12 重启来源，是人工 `supervisorctl restart`、部署脚本，还是其他管理进程触发。
