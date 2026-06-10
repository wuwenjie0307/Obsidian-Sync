---
date: 2026-06-10
tags: [changelog, crm, prompt, intent_tag, customer-profile]
---

# CRM 意向标签提示词定位记录

## 背景

根据正式服客户详情截图排查红框内“意向标签”来源。截图中的标签示例包括：`上海徐汇区`、`凌云新村`、`46.32平米`、`4房`。

最初同时排查了 DB 提示词表 `t_agent_prompt_config` 中的客户画像相关 prompt；后续根据截图特征确认，红框内这种短标签更直接对应 `intent_tag -> leave_contact` 链路中的内联提示词。

## 结论

截图红框内“意向标签”下方的短标签，不是 H20 服务，也不是 DB 中的长 prompt。它来自 joyingbot-new 代码内联的一段短提示词：在用户留下手机号/微信号后，从聊天记录中抽取“房地产关键词”，返回 `{"tags": []}`，再写入 `intent_tag` 字段，通过 `/phone/leave_contact` 保存。

这类标签正好覆盖城市/城区、小区、预算、面积、户型等信息，因此会出现 `上海徐汇区`、`凌云新村`、`46.32平米`、`4房` 这样的展示。

## 关键提示词原文

```text
交流内容：[{聊天记录}]
json格式： {"tags":[]}
要求：识别客户表达的房地产关键词
json数据说明：
1、tags为聊天记录中存在的城市名称、小区名称、预算、户型等信息
请你根据上述思路识别交流内容，并做出对应意图分级及主要依据。只返回按json格式返回
```

## 代码位置

### 主链路位置

`agent/hyper_agent/node/channel_chat_node.py:1026`

```python
response = '{"tags":[]}'
explain_result = llm_chat(question=f"""
交流内容：[{state['channel_list']}]
json格式： {response}
要求：识别客户表达的房地产关键词
json数据说明：
1、tags为聊天记录中存在的城市名称、小区名称、预算、户型等信息
请你根据上述思路识别交流内容，并做出对应意图分级及主要依据。只返回按json格式返回
""")
```

模型返回后写入：

```python
"intent_tag": explain_result_json['tags']
```

随后调用：

```python
qa_api_client.leave_contact(data)
```

### 路由层同款逻辑

`router/chat_server.py:1109`

```python
response = '{"tags":[]}'
channel_list.append({'round': 4, 'customer_message': question, 'ai_reply': ''})
explain_result = _llm_chat(question=f"""
    交流内容：[{channel_list}]
    json格式： {response}
    要求：识别客户表达的房地产关键词
    json数据说明：
    1、tags为聊天记录中存在的城市名称、小区名称、预算、户型等信息
    请你根据上述思路识别交流内容，并做出对应意图分级及主要依据。只返回按json格式返回
    """)
```

同样写入：

```python
"intent_tag": explain_result_json['tags']
```

并调用：

```python
qa_api_client.leave_contact(data)
```

### 保存接口

`common/qa_api.py:119`

```python
def leave_contact(self, data):
    response = requests.post(self.base_url + '/phone/leave_contact', json=data)
```

## 链路梳理

```text
客户留下手机号/微信号
-> PROMPT_GEN_PHONE 识别联系方式
-> 内联短 prompt 从聊天记录提取房地产关键词 tags
-> data.intent_tag = tags
-> qa_api_client.leave_contact(data)
-> POST /phone/leave_contact
-> CRM 客户详情页展示为“意向标签”
```

## 相关但不是红框短标签的 prompt

DB 中还有一条客户画像/需求分析长 prompt，也会抽位置、面积、户型、偏好等信息，但它更偏“聊天结束后的客户画像同步”，不是截图红框短标签最直接的来源。

正式库查询到：

```text
表：zhugedata.t_agent_prompt_config
id：136
model：COMMON
type：USER_TAGS_EXPLAIN_PROMPT
长度：28828
created_time：2025-03-04 15:15:33
缓存 key：prompt:COMMON:USER_TAGS_EXPLAIN_PROMPT
```

该 prompt 输出结构包括：

```text
lead_grade
location
requirements
summary
```

代码中会把 `requirements.preferences` 映射为 `intent_tag`，但截图中 `上海徐汇区 / 凌云新村 / 46.32平米 / 4房` 这种短标签，更直接对应 `leave_contact` 链路中的内联短 prompt。

## 修改建议

如果后续要调整截图红框内“意向标签”的抽取规则，优先改：

1. `agent/hyper_agent/node/channel_chat_node.py:1026`
2. `router/chat_server.py:1109`

如果要统一正式服行为，建议把这段内联 prompt 抽到 `t_agent_prompt_config`，例如新增 `COMMON / INTENT_TAG_EXTRACT_PROMPT`，避免两处代码重复，也方便线上调整后通过 Redis 缓存控制生效。
