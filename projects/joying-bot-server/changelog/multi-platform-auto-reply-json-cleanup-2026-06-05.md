---
date: "2026-06-05"
tags: [changelog]
---

# 多平台自动回复 JSON 清洗

## 改动类型

- [ ] 新功能
- [x] Bug 修复
- [ ] 重构
- [ ] 配置变更

## 改动内容

- 新增 LLM JSON 输出清洗解析能力，覆盖代码块、说明文字、对象/数组、尾逗号、全角结构符、字符串内真实换行等常见模型输出偏差。
- 多平台私信回复链路从直接取 `extract_json_from_string(...)[0]` / `json.loads(...)` 改为清洗后解析，并在解析失败时记录日志和安全兜底。
- 评论区回复接口继续使用 `extract_json_from_string`，自动获得增强后的 JSON 清洗能力。
- 增加 `test/test_llm_json_cleanup.py` 回归测试。

## 影响范围

- 自媒体私信自动回复：`agent/hyper_agent/node/channel_chat_node.py`
- 评论区回复及相关接口解析：`router/chat_server.py`
- 通用 JSON 工具：`common/json_util.py`

## 相关 Commit

- 未提交
