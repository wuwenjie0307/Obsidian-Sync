---
date: "2026-06-05"
status: fixed
severity: medium
tags: [bug]
---

# 多平台自动回复 AI JSON 偶发解析失败

## 问题描述

多平台自动回复相关接口（自媒体私信、评论区回复、改写/联系方式识别等 LLM JSON 输出链路）偶发把 AI 返回的非标准 JSON 直接交给 `json.loads` 或 `extract_json_from_string(...)[0]`，当模型输出带代码块、说明文字、尾逗号、全角标点、字符串内真实换行或数组格式时，后端可能抛出解析异常并传到前端。

## 原因

历史代码主要依赖提示词要求模型“只返回 JSON”，但代码侧没有统一的二次清洗。`common/json_util.extract_json_from_string` 只支持 `{...}` 对象片段，且对数组、尾逗号、全角 JSON 结构符、未转义换行不够鲁棒；部分路径仍直接 `json.loads(output_result.replace(...))`。

## 复现步骤

1. 让 LLM 输出类似 ```json 包裹的 JSON，且对象末尾带尾逗号。
2. 或让 REBUILD_PROMPT 输出数组 JSON，数组末尾带尾逗号。
3. 旧代码直接 `json.loads` 或取 `extract_json_from_string(...)[0]`，解析失败时接口异常。

## 期望行为

AI 输出仍要求是 JSON；代码在使用前统一清洗一次，能解析常见非标准 JSON 格式；无法解析时记录日志并返回安全兜底，不把异常直接抛给前端。

## 实际行为

旧逻辑在部分路径直接解析模型输出，偶发 `JSONDecodeError` 或 `IndexError`。

## 环境信息

- 分支: `merge-check/ai_v6.3.1_video-to-test`
- 本地仓库: `C:\Users\admin\Desktop\joyingbot-new-h20-model-pool-productionize`

## 修复方案

新增 `common.json_util.parse_llm_json_value` 和更鲁棒的 `extract_json_from_string`：支持代码块/正文中的 JSON 片段抽取、对象和数组解析、全角结构符、尾逗号、字符串内真实换行、JSON 注释和少量未加引号 key 修复。多平台私信链路改为统一清洗后取值，评论区回复沿用增强后的 `extract_json_from_string`。

## 优化点

后续可继续把 `router/chat_server.py` 中其他非本次核心链路的 `extract_json_from_string(...)[0]` 改成统一 helper，并补充接口级回归测试。

## 相关文件

- `common/json_util.py`
- `agent/hyper_agent/node/channel_chat_node.py`
- `router/chat_server.py`
- `test/test_llm_json_cleanup.py`
