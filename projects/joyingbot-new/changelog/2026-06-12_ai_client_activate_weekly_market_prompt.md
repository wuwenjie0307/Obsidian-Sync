---
date: 2026-06-12
project: joyingbot-new
type: changelog
tags: [changelog, crm, prompt, production, redis]
aliases: ["楼市周报提示词 150 字控制"]
---

# 楼市周报提示词 150 字控制

## 改动类型

正式服提示词配置调整与 Redis 缓存清理。

## 改动内容

针对产品反馈“楼市周报”提示词要求 200 字左右，但实际输出接近 380 字的问题，定位到正式服提示词配置：

```text
表：zhugedata.t_agent_prompt_config
id：149
model：COMMON
type：AI_CLIENT_ACTIVATE
缓存 key：prompt:COMMON:AI_CLIENT_ACTIVATE
```

代码入口：

```text
router/crm_server.py
/doubao_question
当用户问题包含“楼市周报”时读取 COMMON / AI_CLIENT_ACTIVATE
```

已将提示词中的输出要求改为 130-170 个中文字符，最多 3 个核心信息点，不强制覆盖政策、土地、成交、房价全部板块；无可靠数据或最新动态的板块直接省略；示例同步改为 150 字左右，避免模型继续模仿长例子。

## 生效方式

保存 DB 后，需要清正式服 Redis prompt 缓存：

```bash
redis-cli -h 127.0.0.1 -p 6389 -a 123456 -n 0 DEL prompt:COMMON:AI_CLIENT_ACTIVATE
```

本次执行结果：

```text
(integer) 1
```

说明旧缓存已删除。后续请求会重新从 `zhugedata.t_agent_prompt_config` 读取新提示词并写回 Redis。

如果不清缓存，代码中的缓存过期时间为 3600 秒，最多约 1 小时后自动生效。

## 验证结果

- 已确认 Redis 删除返回 `(integer) 1`。
- 下一步由产品重新测试“楼市周报”输出，确认字数是否稳定在 130-170 字附近。

## 影响范围

- 影响 `/doubao_question` 中包含“楼市周报”的正式服生成链路。
- 不影响 `AI_GENERAL_INDUSTRY` 通用行业周报。
- 不影响 `CUSTOM_LEVEL_HYPER_PROMPT` 客户分级/意向分析链路。

## 图谱链接

- [[projects/joyingbot-new/00-项目概览|项目概览]]
- [[projects/joyingbot-new/changelog/00-changelog-index|更新日志索引]]
