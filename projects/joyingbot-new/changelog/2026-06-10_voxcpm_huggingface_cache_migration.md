---
date: "2026-06-10"
tags: [changelog, ops, h20-test, voxcpm, model-cache]
---

# 2026-06-10 VoxCPM HuggingFace 缓存迁移口径

## 改动类型

- [ ] 新功能
- [ ] Bug 修复
- [ ] 重构
- [x] 配置变更

## 改动内容

记录运维沟通口径：VoxCPM 容器 compose 中的 `/data/model_cache/huggingface:/root/.cache/huggingface` 是 HuggingFace 模型缓存挂载。

- 宿主机目录：`/data/model_cache/huggingface`
- 容器内目录：`/root/.cache/huggingface`
- 当前环境变量包含：`HF_HOME=/root/.cache/huggingface`、`TRANSFORMERS_CACHE=/root/.cache/huggingface`、`HF_ENDPOINT=https://hf-mirror.com`
- 迁移到新机器时，可以按 compose 直接启动容器；如果新机器能访问 `hf-mirror.com`，第一次启动会自动下载模型。
- 对外简短回复：`对，按 compose 把容器 run 起来就行，第一次会自动下载模型。`

## 影响范围

- H20 / 新机器上的 VoxCPM 模型服务部署。
- 不涉及后端代码改动。
- 不涉及 API 参数改动。

## 注意事项

- 如果不挂载 `/data/model_cache/huggingface:/root/.cache/huggingface`，模型可能下载到容器内部，容器删除后缓存也会丢。
- 如果新机器网络无法访问 `hf-mirror.com`，自动下载会失败；这种情况下需要提前同步 `/data/model_cache/huggingface`。

## 相关 Commit

- 无，仅运维记录。
