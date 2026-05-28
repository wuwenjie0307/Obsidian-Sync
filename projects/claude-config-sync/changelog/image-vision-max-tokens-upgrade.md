---
date: "2026-05-28"
tags: [changelog]
---

# image-vision skill max_tokens 提升

## 改动类型

- [ ] 新功能
- [ ] Bug 修复
- [ ] 重构
- [x] 配置变更

## 改动内容

- `max_tokens` 默认值从 2048 提升到 16384，避免大图片（如数据库表结构截图）输出被截断
- 新增 `SILICONFLOW_MAX_TOKENS` 环境变量支持，可按需覆盖默认值
- 文档同步更新：新增环境变量一览表（`SILICONFLOW_API_KEY` / `SILICONFLOW_MODEL` / `SILICONFLOW_MAX_TOKENS`）

## 影响范围

- `C:\Users\admin\.claude\skills\image-vision\vision.py` — max_tokens 读取逻辑改为 `os.environ.get("SILICONFLOW_MAX_TOKENS", "16384")`
- `C:\Users\admin\Desktop\Obsidian\projects\claude-config-sync\docs\image-vision-视觉识别skill配置.md` — 补充环境变量表 + max_tokens 说明
