---
date: "2026-05-29"
status: fixed
severity: high
tags: [bug, llm, stream, openai, sse]
---

# LLM 流式响应中断导致回答失败

## 问题描述

上游 LLM / OpenAI-compatible 流式接口在生成过程中可能返回 `stream disconnected before completion`，导致 `/hyper_agent_chat_stream` 本次 SSE 回答进入错误分支，前端看到断流或错误信息。

## 原因

根因是服务端把上游 SSE 流直接作为主路径消费：

- `agent/llm_models.py::ask_question_with_logging_stream` 在 `response.iter_lines()` 中遇到上游连接中断时直接抛异常，没有非流式兜底。
- `agent/llm_models.py::realize_think_while_search` 实际只返回最终文本，但内部仍启用 `client.responses.create(..., stream=True)`，多了一层不必要的上游 SSE 断流风险。
- 路由层虽然会捕获异常并返回 error chunk，但无法恢复已经中断的上游模型回答。

## 复现步骤

1. 调用 `/chat/hyper_agent_chat_stream` 触发需要 LLM 流式生成的分支。
2. 让上游流式接口在已经返回部分内容后断开，或复现 OpenAI-compatible SDK 报 `stream disconnected before completion`。
3. 原逻辑会抛异常，最终返回错误 chunk，而不是继续完成回答。

## 期望行为

上游流式接口断开后，服务端应自动调用同模型的非流式接口兜底；如果前面已经发出部分内容，只继续补齐缺失后缀，避免重复输出。

## 实际行为

原逻辑没有兜底和去重，断流异常直接冒泡到 SSE generator。

## 解决方案

- 新增 `common/llm_streaming.py`：识别常见流中断异常，并提供 `stream_text_with_fallback`。
- `ask_question_with_logging_stream` 接入非流式兜底：流断开时调用 `ask_question_with_logging(..., stream=False)` 获取完整答案，并根据已输出内容只补发后缀。
- `realize_think_while_search` 改为非流式调用，因为该函数只需要最终答案，不需要内部 SSE。
- 新增 `test/test_llm_streaming.py` 覆盖断流后缀补齐、非断流异常继续抛出、OpenAI 断流文案识别。

## 优化点

- 后续可以把 LLM 请求超时、重试次数、是否启用流式兜底做成配置项。
- 生产日志不应打印完整鉴权 header，后续可单独清理历史日志输出。

## 相关文件

- `agent/llm_models.py`
- `common/llm_streaming.py`
- `test/test_llm_streaming.py`
