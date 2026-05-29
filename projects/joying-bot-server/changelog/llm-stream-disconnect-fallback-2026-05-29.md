---
date: "2026-05-29"
tags: [changelog, llm, stream]
---

# LLM 流式断流兜底

## 改动类型

- [ ] 新功能
- [x] Bug 修复
- [ ] 重构
- [ ] 配置变更

## 改动内容

- 新增 LLM 流式断流识别与非流式兜底工具。
- `/hyper_agent_chat_stream` 依赖的 `llm_chat_stream` 上游流断开时，会自动使用非流式请求补齐回答。
- `realize_think_while_search` 改为非流式获取最终答案，减少内部 SSE 断流风险。
- 增加标准库单元测试覆盖断流兜底行为。

## 影响范围

- 影响 LLM 流式回答链路，尤其是 `agent/llm_models.py::ask_question_with_logging_stream` 和 `agent/llm_models.py::realize_think_while_search`。
- 正常流式返回不改变；仅在上游流中断时触发兜底。
- 兜底会多发起一次非流式模型请求，可能增加一次失败场景下的模型调用成本。

## 相关 Commit

- 未提交
