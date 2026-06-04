---
date: "2026-06-04"
tags: [changelog, h20, model-pool, heygem, voxcpm, lip-sync, test-env]
---

# h20 测试服切回旧 Heygem 唇形模型池 2026-06-04

## 改动类型

- [ ] 新功能
- [ ] Bug 修复
- [ ] 重构
- [x] 配置变更

## 改动内容

2026-06-04，将 h20 测试服 CRM 视频生成链路从“VoxCPM + LatentSync 唇形”切回为“新克隆模型/VoxCPM + 旧 Heygem 唇形模型”。

本次保留 LatentSync 相关代码和模型池记录，不删除；测试库只通过 `t_comfyui_config.is_active` 控制模型池启停。

### 代码状态

- 已恢复旧 Heygem 唇形调用逻辑。
- 当前 LatentSync 调用逻辑没有删除，已在代码中注释保留，便于后续需要时恢复或参考。
- 相关代码已提交并合并到 GitLab `test` 分支。

相关提交：

```text
75143382 fix: restore heygem lip sync model pool
e05fdc96 merge into test
```

### h20 服务实例

h20 测试服当前运行 4 个旧 Heygem/duix 唇形实例：

| 服务 | 端口 | GPU |
|---|---:|---:|
| `duix-avatar-h20-test-6004` | `6004 -> 8383` | GPU 1 |
| `duix-avatar-h20-test-6005` | `6005 -> 8383` | GPU 2 |
| `duix-avatar-h20-test-6006` | `6006 -> 8383` | GPU 3 |
| `duix-avatar-h20-test-6007` | `6007 -> 8383` | GPU 4 |

其中 `6006`、`6007` 是本次为四路模型池补齐的新实例。

镜像：

```text
registry.hd-04.alayanew.com:8443/alayanew-5580740d-b175-49a9-9409-98b01b89bdc1/guiji2025/duix.avatar:2.9
```

### 测试库模型池配置

`zhugedata_test.t_comfyui_config` 当前启用的新组合：

| DB id | 新克隆模型/VoxCPM | 旧 Heygem 唇形 | description | 状态 |
|---:|---|---|---|---|
| `16` | `http://127.0.0.1:8120` | `http://127.0.0.1:6004` | `h20 voxcpm 8120 + old heygem lip 6004` | `is_active=1` |
| `17` | `http://127.0.0.1:8122` | `http://127.0.0.1:6005` | `h20 voxcpm 8122 + old heygem lip 6005` | `is_active=1` |
| `18` | `http://127.0.0.1:8124` | `http://127.0.0.1:6006` | `h20 voxcpm 8124 + old heygem lip 6006` | `is_active=1` |
| `19` | `http://127.0.0.1:8126` | `http://127.0.0.1:6007` | `h20 voxcpm 8126 + old heygem lip 6007` | `is_active=1` |

旧 LatentSync 模型池记录保留但停用：

```text
id=1,2,10,11 -> is_active=0
```

试听相关模型池未调整。

## 影响范围

- 影响 h20 测试服 CRM 视频生成调度使用的 active 模型池。
- 调度层继续从 `t_comfyui_config` 领取模型池记录：
  - `config_value_audio` 调用新克隆模型/VoxCPM。
  - `config_value` 调用旧 Heygem 唇形模型。
- LatentSync 相关服务、代码和 DB 记录未删除，仅不作为当前 active 视频生成模型池。
- 不影响生产库和正式服。

## 验证结果

### 端口健康检查

旧 Heygem 唇形端口全部可用：

```text
6004 /easy/query -> code=10004, success=true, msg=任务不存在
6005 /easy/query -> code=10004, success=true, msg=任务不存在
6006 /easy/query -> code=10004, success=true, msg=任务不存在
6007 /easy/query -> code=10004, success=true, msg=任务不存在
```

新克隆模型/VoxCPM 端口全部可用：

```text
8120 /health -> {"status":"ok"}
8122 /health -> {"status":"ok"}
8124 /health -> {"status":"ok"}
8126 /health -> {"status":"ok"}
```

### 真实唇形提交验证

对四个 Heygem 唇形端口分别执行真实 `/easy/submit`，均生成成功并进入完成状态 `status=2`：

| Heygem 端口 | 测试任务 code | 结果 | 状态 |
|---:|---|---|---|
| `6004` | `codex_pool_lip_6004_20260604170611` | `/codex_pool_lip_6004_20260604170611-r.mp4` | `status=2` |
| `6005` | `codex_pool_lip_6005_20260604170620` | `/codex_pool_lip_6005_20260604170620-r.mp4` | `status=2` |
| `6006` | `codex_pool_lip_6006_20260604170629` | `/codex_pool_lip_6006_20260604170629-r.mp4` | `status=2` |
| `6007` | `codex_pool_lip_6007_20260604170645` | `/codex_pool_lip_6007_20260604170645-r.mp4` | `status=2` |

输出视频参数一致：

```text
duration=1760ms
resolution=720x1280
```

### 全流程验证

已用当前 active 组合中的 `6004 + 8120` 跑通一次完整 CRM 视频合成链路：

```text
task=codex_h20_fullflow5_20260604164536
url=https://videos-test.joyingai.cn/video/crm/20260604/user4_1780562901406_20370a5d28000053.mp4
```

产物校验：

```text
HTTP 200
video=h264 720x1280
audio=aac
duration=2.304218s
size=346811
```

## 回滚方式

如需回到 LatentSync 组合：

1. 将当前 Heygem 组合 `id=16,17,18,19` 置为 `is_active=0`。
2. 将原 LatentSync 组合 `id=1,2,10,11` 按需要重新置为 `is_active=1`。
3. 保持代码中注释保留的 LatentSync 调用逻辑，用于后续恢复参考。

## 注意事项

- 之前发现四条新组合都指向单个 `6004` 会带来并发“忙碌中”风险；现在已拆成 `6004/6005/6006/6007` 四个独立 Heygem 实例。
- 后续建议观察 scheduler 真实队列中四路模型池的领取和释放情况，重点看 `t_comfyui_config.is_active` 是否按 `1 -> 2 -> 1` 正常回收。

## 相关 Commit

- `75143382 fix: restore heygem lip sync model pool`
- `e05fdc96 merge into test`
