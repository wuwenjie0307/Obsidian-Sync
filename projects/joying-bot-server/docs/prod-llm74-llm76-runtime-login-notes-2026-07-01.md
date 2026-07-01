---
date: 2026-07-01
project: joying-bot-server
type: doc
tags: [doc, production, llm76, llm74, botserver, hyperframes, runbook]
aliases: [prod-llm74-llm76-runtime-login-notes-2026-07-01]
---

# 正式服 LLM74 / LLM76 运行与登录记录

## 结论

截至 2026-07-01 的排查结论：正式服当前需要同时区分 LLM74 和 LLM76。排查视频任务时不要默认只看旧正式服节点，也不要默认只看 H20 测试服。

- LLM74：历史正式服/旧链路相关节点，既有记录里见过 `prod_ai_autodone`、`ai_autodone_py_prod`。
- LLM76：新 botserver 定时任务节点，视频任务日志和 HyperFrames 产物优先在这里查。
- 本次线上视频任务 `task_id=18387` 的日志和产物确认在 LLM76。

## LLM74 已知情况

既有正式服记录里，LLM74 曾作为正式服旧链路运行节点出现：

- 机器标识：`LLM-74`
- 旧正式服务目录示例：`/data/project/prod_ai_autodone -> /data/project/prod_ai_autodone.<release>`
- 旧正式进程示例：`ai_autodone_py_prod`
- 旧链路文档参考：[[projects/joying-bot-server/docs/prod-hyperframes-docker-runner-mount-check-2026-06-29|prod-hyperframes-docker-runner-mount-check-2026-06-29]]

注意：LLM74 和 LLM76 可能同时存在正式链路相关服务。查具体视频任务时，以数据库里的 `hf_*` 路径、当前任务日志和实际进程 cwd 为准，不要靠机器名猜。

## LLM76 已知情况

LLM76 是本次确认到的 botserver 定时任务节点。

- SSH 主机：`222.71.55.26`
- SSH 端口：`31222`
- SSH 用户：`llm-76`
- Jenkins：`Prod_Ai_BotServer_llm76`
- scheduler 主日志：`/data/server_logs/supervisord/botserver_sch.out`
- 当前任务运行目录示例：`/data/project/prod_ai_botserver.20260701030636`
- 任务内部日志示例：`/data/project/prod_ai_botserver.20260701030636/logs/run.log`
- HyperFrames 任务产物示例：`/data/project/prod_ai_botserver.20260701030636/tmp/h20_hyperframes/<task_id>/`

密码不要写入 Obsidian、Git、脚本、命令历史或最终回复；只使用当前排查时的临时授权信息。

## LLM76 登录注意事项

本机在同时开 VPN / 内网环境时，默认 SSH 路由可能走错网卡，导致 Paramiko 报 `Error reading SSH protocol banner`，但实际网络是通的。

本次可用方式：绑定本地源地址 `192.168.1.32` 后登录 LLM76。

OpenSSH 示例：

```bash
ssh -b 192.168.1.32 -p 31222 llm-76@222.71.55.26
```

Paramiko 非交互排查时也需要手动 bind 本地 socket：

```python
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind(("192.168.1.32", 0))
sock.connect(("222.71.55.26", 31222))
client.connect("222.71.55.26", port=31222, username="llm-76", sock=sock, ...)
```

不要把密码写进持久脚本。临时脚本只用于当前诊断，结束后不落盘。

## 视频任务排查顺序

遇到正式服视频产物异常时，优先按这个顺序查：

1. 用产物 URL 反查 `t_video_generate_task`。
2. 看 `task_id`、`job_id`、`templates_style_id`、`voice_file_url`、`imagery_video`、`video_user_subtitle`、`personal_intro`。
3. 看 `hf_manifest_path`、`hf_result_path`、`whisper_timeline_path`、`hf_final_video_path`。
4. 登录实际路径所在机器，例如 LLM76。
5. 对比三份文件：
   - `manifest.json`：后端传给 HyperFrames 的目标脚本。
   - `whisper_timeline.json`：对口型后视频音频的识别结果。
   - `subtitle_timeline.json`：最终字幕时间轴。
6. 如果 `manifest.json` 正确，但 `whisper_timeline.json` 已经错误，问题在 HyperFrames 渲染前，通常要查 TTS / 对口型 / 参考音频。
7. 如果 `whisper_timeline.json` 正确，但 `subtitle_timeline.json` 错，才继续查字幕重建和断句逻辑。

## 18387 线上排查记录

目标视频：`https://videos.joyingai.cn/video/crm/20260701/user4_1782874136900_51ec1196e5462e74.mp4`

数据库反查：

- `task_id=18387`
- `job_id=20927`
- `templates_style_id=2`
- 模板：视频日记
- `voice_file_url=https://files.joyingai.cn/crm/20260527/user1625_1779868135276_92e6ab35927bd312.wav`
- `hf_final_video_path=/data/project/prod_ai_botserver.20260701030636/tmp/h20_hyperframes/18387/final.mp4`
- `hf_manifest_path=/data/project/prod_ai_botserver.20260701030636/tmp/h20_hyperframes/18387/manifest.json`
- `whisper_timeline_path=/data/project/prod_ai_botserver.20260701030636/tmp/h20_hyperframes/18387/whisper_timeline.json`

关键证据：

- `manifest.json` 里的 `script_text` 是正确的目标文案。
- LLM76 日志显示参考音频 Whisper 文案是类似《水调歌头》的内容，而且重复两遍。
- `voxcpm_tts.py` 调用 VoxCPM 时传了 `reference_text_len=124`。
- 克隆音频上传 URL 转写后，已经出现参考音频内容和目标文案交错。
- `whisper_timeline.json` 只是继承了克隆音频里的错误内容，HyperFrames 不是源头。

本次根因判断：

VoxCPM hifi 克隆把参考音频的 `prompt_text/reference_text` 当成强上下文，未能只学习音色，导致参考音频中的诗词/歌词类内容被夹进目标口播。这个风险在长参考音频、重复内容、歌词/诗词、与目标文案无关的参考音频上更高。

## HyperFrames Docker runner 运行观察

LLM76 当前可见 HyperFrames runner 以动态 `docker run` 方式执行，不是常驻容器池。

观察到的关键信息：

- Docker binary：`/usr/bin/docker`
- 镜像：`h20-hyperframes-renderer:0.6.42-node22.22.2`
- 挂载：`/data:/data`、`/tmp:/tmp`
- 工作目录：当前 release，例如 `/data/project/prod_ai_botserver.20260701030636`
- 典型执行：`node /data/project/prod_ai_botserver.<release>/hyperframes-postprocess/index.js --input .../manifest.json --output .../result.json`

如果正式服 sudo 策略要求前面加 sudo，不建议把 `HF_DOCKER_BINARY` 写成 `sudo docker` 字符串；更稳的是准备一个免密 wrapper，例如 `/usr/local/bin/hf-docker`，里面执行 `sudo -n /usr/bin/docker "$@"`，再配置：

```bash
HF_DOCKER_BINARY=/usr/local/bin/hf-docker
```

## 排查提醒

- 不要把 H20 测试服路径当成正式服路径。
- 不要只看 LLM74 或只看 LLM76，先由 DB 的 `hf_*` 路径判断任务实际落点。
- 查日志时不要宽搜裸 `job_id`，容易命中其他数据；优先精确搜 `task_id=<id>`、`h20_hyperframes/<task_id>`、`<task_id>-r_bt709_916_30fps`。
- 日志里可能含 token 或业务敏感信息，复制给外部时需要脱敏。
- 密码不入库、不进脚本、不进最终回复。

## 图谱链接

- [[projects/joying-bot-server/00-项目概览|项目概览]]
- [[projects/joying-bot-server/docs/00-docs-index|参考文档索引]]
- [[projects/joying-bot-server/docs/prod-hyperframes-docker-runner-mount-check-2026-06-29|正式服 HyperFrames Docker runner 挂载检查]]
- [[projects/joying-bot-server/docs/gitlab-vpn-intranet-connectivity-2026-07-01|GitLab VPN 内网访问差异记录]]