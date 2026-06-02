---
date: "2026-06-02"
tags: [changelog, h20, docker, production-alignment, voxcpm, latentsync, scheduler]
---

# h20 Docker 服务对齐生产逻辑差距说明

## 当前结论

如果目标只是“两个新模型能用 Docker 服务方式跑起来”，当前已经完成大约 70%。

如果目标是“完全对齐生产服原来的 Docker 模型池调度逻辑”，当前只完成大约 40%，还差约 60%。

原因是：VoxCPM / LatentSync 这两个模型的 Docker 旁路服务已经验证通过，但 Bot 调度链路还没有真正改成生产那种“从 `t_comfyui_config` 领取空闲 Docker 服务，再按配置行里的地址调用模型”的方式。

## 当前已经完成了什么

### 1. Docker 旁路服务已跑通

当前 h20 上已经有两个旁路 Docker 服务：

| 模型 | Docker 地址 | 用途 | 当前状态 |
|---|---|---|---|
| VoxCPM | `http://127.0.0.1:8120` | 声音克隆 / 音色克隆 | 健康检查通过，直接声音生成已通过 |
| LatentSync | `http://127.0.0.1:8121` | 唇形同步 | 健康检查通过，直接 lip-sync 已通过 |

这两个 Docker 目前不影响当前 CRM 测试链路，只是旁路验证。

### 2. VoxCPM Docker 已验证

VoxCPM Docker 已完成：

- 容器启动。
- `/health` 返回 ok。
- 直接请求 `/v1/clone-voice` 能生成音频。
- GPU1 能正常加载和运行。

### 3. LatentSync Docker 已验证

LatentSync Docker 已完成：

- 容器启动。
- `/health` 返回 ok。
- 修复了容器依赖冲突。
- 直接请求 `/v1/lip-sync` 已返回 HTTP 200。
- 3.6 秒短视频验证成功，输出 `/tmp/latentsync-docker-test-ok.mp4`。
- GPU2 能正常参与推理。

### 4. GitLab test 已提交

当前 Docker 依赖修复已经推送到 GitLab `test` 分支：

```text
f0275ea1 fix: isolate latentsync docker dependencies
```

Jenkins 已部署到 h20：

```text
/data/project/test_ai_botserver -> /data/project/test_ai_botserver.20260602102443
```

### 5. 当前 Bot 没有被切换

当前 Bot 仍然走裸机模型服务：

```json
{
  "voxcpm_api_base": "http://127.0.0.1:8110",
  "latentsync_api_base": "http://127.0.0.1:8101"
}
```

Docker 当前只是验证通过的备用旁路：

```json
{
  "voxcpm_api_base": "http://127.0.0.1:8120",
  "latentsync_api_base": "http://127.0.0.1:8121"
}
```

今天没有切换 Bot，是因为测试库当前还有待处理/处理中任务：

- `task_status=0` 待处理任务：18 条。
- `task_status=2` 任务：1 条。
- `t_comfyui_config.id=1` 是 `is_active=2`，说明调度锁被占用。

## 和生产服逻辑相比还差什么

### 差距 1：还没有真正使用 `t_comfyui_config` 里的模型地址

生产服原逻辑更像这样：

```text
定时任务扫描待处理 task
-> 查询 t_comfyui_config 哪个 Docker 服务空闲
-> 把 is_active 从 1 改成 2，锁住这个服务
-> 使用该行配置里的 Docker 服务地址生成视频
-> 任务完成或失败后释放 is_active 回 1
```

当前 h20 虽然还使用 `t_comfyui_config` 做锁，但模型调用地址主要还是从全局配置读取：

```json
{
  "voxcpm_api_base": "...",
  "latentsync_api_base": "..."
}
```

也就是说，当前还不是“领取哪条配置，就调用哪条配置的 Docker 服务”。

### 差距 2：Docker 服务还没有写入模型池配置

理想状态应该是：

```text
t_comfyui_config.config_value_audio -> VoxCPM Docker 地址
t_comfyui_config.config_value       -> LatentSync Docker 地址
```

例如 h20 单实例可以先这样：

```text
config_value_audio = http://127.0.0.1:8120
config_value       = http://127.0.0.1:8121
is_active          = 1
```

当前测试库里还不是这个结构，里面仍然是旧生产/旧模型地址风格。

### 差距 3：调度代码还没有按配置行传递两个模型地址

当前代码需要继续改成：

```text
调度领取 config_model
-> config_model.config_value_audio 传给 VoxCPM
-> config_model.config_value        传给 LatentSync
-> video_work_Heygem_Whisper 不再只读全局 config
```

这样才算真正沿用生产服模型池逻辑。

### 差距 4：Docker 还没有做成多实例池

现在 h20 只有旁路单实例：

```text
VoxCPM: 8120
LatentSync: 8121
```

生产式模型池后续可能需要多组：

```text
第 1 组：VoxCPM 8120 + LatentSync 8121
第 2 组：VoxCPM 8130 + LatentSync 8131
...
```

每组对应 `t_comfyui_config` 一行，由调度锁控制空闲/占用。

不过 h20 当前 LatentSync 单任务就很慢，且 GPU 负载重，第一阶段建议只跑 1 组，不急着扩多实例。

### 差距 5：Docker 构建还没有完全离线可复现

今天 h20 上直接 compose build 时，构建流程会尝试从 GitHub clone `ByteDance/LatentSync`，但 h20 访问 GitHub 超时。

今天为了先验证模型服务，采用了离线增量镜像方式：基于已有 LatentSync 镜像增加 venv 修复层。

后续要和生产部署方式对齐，需要整理为更稳定的方案：

- 要么把 LatentSync 源码放进内部 GitLab / 内部制品仓库。
- 要么做一个固定 source base image。
- 要么在 h20/A800 上固定一份源码目录，构建时使用本地源码。
- 不建议生产构建依赖 GitHub 实时 clone。

### 差距 6：还没有按生产 yml 风格沉淀部署目录

晋良之前说旧模型是嘉豪做镜像，然后用 yml 文件启动，A800 上目录是：

```text
/data/Comfyui_Duix/Duix-Avatar/deploy/docker-employ
```

当前 h20 已经有仓库里的 compose：

```text
deploy/docker/docker-compose.h20.yml
```

但还没有完全沉淀成运维可直接接手的一套目录，包括：

- compose/yml 文件。
- 镜像 tag 规范。
- GPU 绑定规则。
- 日志目录。
- 启停命令。
- 健康检查命令。
- 回滚命令。

## 下一步怎么做才能对齐生产逻辑

### 第一步：等当前队列空闲，再做 Bot 临时切 Docker 验证

前提：

```text
t_video_generate_task 没有 task_status=1/2 的任务
t_comfyui_config.id=1 释放为 is_active=1
```

然后临时把 Bot 配置改为：

```json
{
  "voxcpm_api_base": "http://127.0.0.1:8120",
  "latentsync_api_base": "http://127.0.0.1:8121"
}
```

只提交 1 个 CRM 视频任务验证：

- 声音克隆走 VoxCPM Docker。
- 唇形同步走 LatentSync Docker。
- 字幕、封面、上传、回调仍走生产底座逻辑。
- 任务结束后锁释放。

如果失败，立即切回：

```json
{
  "voxcpm_api_base": "http://127.0.0.1:8110",
  "latentsync_api_base": "http://127.0.0.1:8101"
}
```

### 第二步：改代码，让模型地址从 `t_comfyui_config` 传入

目标：不再只依赖全局配置里的模型地址。

需要改的方向：

```text
scheduler 领取 config_model
-> _process_single_video_task_with_config / _process_single_video_task
-> video_work_Heygem_Whisper
-> VoxCPM / LatentSync API 调用
```

要把：

```text
config_model.config_value_audio
config_model.config_value
```

一路传到模型调用处。

### 第三步：更新 h20 测试库模型池配置

第一阶段只建议配置 1 组：

```text
config_value_audio = http://127.0.0.1:8120
config_value       = http://127.0.0.1:8121
is_active          = 1
```

等单组稳定后，再考虑多组 Docker。

### 第四步：端到端验证生产式调度链路

验证路径应该是：

```text
CRM 创建视频任务
-> CRM 调 /crm/generate_video_task
-> Bot 入库
-> scheduler 扫描 task_status=0
-> 领取 t_comfyui_config 空闲配置
-> 调 VoxCPM Docker
-> 调 LatentSync Docker
-> 字幕/封面/上传/回调
-> 释放 t_comfyui_config 锁
```

验证重点：

- 任务成功后 `task_status=3`。
- 失败后 `task_status=4`，不能卡在 2。
- `t_comfyui_config.is_active` 必须释放回 1。
- CRM 能收到最终视频 URL 或失败回调。
- 不允许绕过 `/crm/generate_video_task` 直接实时生成。

### 第五步：整理运维部署材料

需要给晋良/运维沉淀：

- 镜像名和 tag。
- compose/yml 目录。
- 启动命令。
- 停止命令。
- 重启命令。
- 查看日志命令。
- 健康检查命令。
- GPU 绑定规则。
- 回滚到裸机 `8110/8101` 的步骤。
- 构建不依赖 GitHub 的方案。

## 当前一句话状态

现在是：

```text
两个新模型 Docker 服务本身已经旁路跑通；但还没有真正接入生产服那套 t_comfyui_config 空闲 Docker 池调度逻辑。
```

接下来最关键的不是继续证明 Docker 能跑，而是让 Bot 调度链路从“读全局模型地址”改成“领取哪条 t_comfyui_config，就调用哪条配置里的 VoxCPM/LatentSync Docker 地址”。
