---
date: "2026-06-23"
project: joyingbot-new
type: doc
tags: [doc, crm, video, material, api, apidoc, h20]
aliases: ["CRM 用户任务素材列表返回体字段说明", "materialUsertaskList 返回体字段"]
---

# CRM 用户任务素材列表返回体字段说明

## 图谱链接

- 项目: [[projects/joyingbot-new/00-项目概览|joyingbot-new]]
- 索引: [[projects/joyingbot-new/docs/00-docs-index|参考文档索引]]

## 背景

本笔记记录一个典型的 CRM 用户任务素材列表接口返回体，用于解释视频生成链路里 `materialUsertaskList` 返回的素材字段含义。

来源：`apidoc` 插件查询 `crm` 项目。

- 分类：`视频生成 | 视频获客`
- 接口 ID：`1130`
- 标题：`短视频 | 模板 | 用户任务素材列表`
- 方法：`POST`
- 路径：`/crm/agent/pc/video/materialUsertaskList`

注意：该 JSON 是接口返回体，不是请求体。该接口文档中的请求体示例为：

```json
{
  "filter": {
    "job_id": 113,
    "task_id": 138
  },
  "from": 1,
  "size": 10
}
```

## 典型返回体

```json
{
  "code": 200,
  "data": {
    "total": 1,
    "list": [
      {
        "id": 705,
        "job_id": 1415,
        "task_id": 1360,
        "category_id": 0,
        "material_name": "9d00985fa5f12f550938c82719f26339..mp4",
        "material_type": 1,
        "material_duration": 17,
        "material_subtitle": "南京半个月出了4个王炸利好！第一个就关系到所有老板！6月15号开始，《南京市规范涉企行政检查办法》正式落地执行，现在直接从源头严控检查准入门槛，给南京的营商环境再加一层保障。截止目前，江苏已经有15家银行的整整2084个网点，都能办理本外币合一账户了，一个账户就能搞定所有币种结算，帮南京出海的企业省了超多麻烦。这次南京还放了真金白银的福利：淘汰老旧非营运货车、非道路移动机械就能领补贴，总补贴池足足1.6个亿，单个车主最高能拿到28万多的补贴。最后还有个国家级好消息：南京刚刚入选金砖国家新工业革命伙伴城市网络的首批成员，接下来就要往产业新高度冲刺了。这一波南京的全新动态，哪一个戳到你了？赶紧把你最关心的那条打在评论区，别忘了点赞收藏加关注，我会第一时间更南京最新的消息！",
        "material_source_url": "https://files.joyingai.cn/crm/20260623/user119_1782178880392_7fa1caa58d808ac8.mp4",
        "templates_id": 120,
        "company_id": 1,
        "user_id": 119,
        "is_mix_material": 1,
        "is_lip_sync": 0,
        "sort_order": 1,
        "status": 1,
        "created_at": 1782178910,
        "updated_at": 1782178910
      }
    ]
  },
  "message": "success",
  "time": 0,
  "traceId": ""
}
```

## 顶层字段含义

| 字段 | 含义 |
|---|---|
| `code` | 业务状态码，`200` 表示成功。 |
| `data` | 返回数据主体。 |
| `data.total` | 符合查询条件的素材总数。 |
| `data.list` | 素材列表，每一项是一条用户任务素材记录。 |
| `message` | 返回消息，成功时一般是 `success`。 |
| `time` | 接口耗时或时间字段，当前示例为 `0`。 |
| `traceId` | 链路追踪 ID，用于日志排查；为空表示当前未返回追踪 ID。 |

## `data.list[]` 字段含义

| 字段 | 含义 |
|---|---|
| `id` | 素材记录 ID，也就是这条用户任务素材记录的主键。 |
| `job_id` | 视频生成 job ID，表示这一批视频生成任务或工作组。 |
| `task_id` | 视频生成 task ID，表示 job 下的具体视频任务。 |
| `category_id` | 素材分类 ID。`apidoc` 在素材库接口里标注为“分类ID”；这里返回 `0` 通常表示未分类或默认分类。 |
| `material_name` | 素材名称，通常是上传后的文件名。 |
| `material_type` | 素材类型。`apidoc` 明确标注：`1` 表示视频，`2` 表示图片。 |
| `material_duration` | 素材时长，单位通常是秒。视频一般有时长，图片一般可能为 `0`。 |
| `material_subtitle` | 素材字幕或分镜文案。`apidoc` 在该接口里注释为“分镜素材标识”，本地模型注释为“素材字幕”。 |
| `material_source_url` | 素材源文件 URL，也就是实际视频或图片地址。 |
| `templates_id` | 关联的视频模板 ID。 |
| `company_id` | 公司 ID / 租户 ID。 |
| `user_id` | 用户 ID，通常是创建或拥有该素材/任务的用户。 |
| `is_mix_material` | 是否混剪/分镜素材。`apidoc` 在用户任务素材列表里写“是否设置分镜”，素材库接口里写“是否混合素材”；本地模型注释为 `是否混剪素材 0否 1是`。 |
| `is_lip_sync` | 是否唇形同步。该字段在 `apidoc` 的接口示例中未完全同步，但本地模型注释为 `是否唇形同步 0否 1是`。实际处理里仅当 `material_type=1` 且 `is_lip_sync=1` 时，视频素材会被当作唇形同步素材。 |
| `sort_order` | 排序值，决定素材在列表或分镜里的顺序。 |
| `status` | 状态字段。文档没有给枚举，本地模型注释为“状态”；当前示例的 `1` 可按正常/有效状态理解。 |
| `created_at` | CRM 侧创建时间戳，Unix 秒级时间戳。示例 `1782178910` 对应本地时间 `2026-06-23 09:41:50`。 |
| `updated_at` | CRM 侧更新时间戳，Unix 秒级时间戳。示例 `1782178910` 对应本地时间 `2026-06-23 09:41:50`。 |

## 这个案例的业务含义

这条记录表示：`job_id=1415`、`task_id=1360` 下有一条用户任务素材记录，素材记录 ID 为 `705`。素材是一个视频文件，`material_type=1`，时长 `17` 秒，源文件地址为 `material_source_url`，关联模板 `templates_id=120`，属于公司 `1` 和用户 `119`。

该素材被标记为混剪/分镜素材，`is_mix_material=1`；但没有开启唇形同步，`is_lip_sync=0`。素材排序为第 `1` 个，状态为 `1`。

## 相关代码依据

- `pojo/models.py`：`VideoMaterialTemplate` 相关字段注释包括素材类型、素材字幕、素材源地址、模板 ID、是否混剪素材、是否唇形同步、排序和状态。
- `scheduler/collect_scheduler.py`：组装素材字典时，`material_type=1` 进入视频素材字典，`material_type=2` 进入图片素材字典；只有 `material_type=1` 且 `is_lip_sync=1` 时，唇形同步标记才会被视为 `True`。

## 相关文件

- `C:\Users\admin\Desktop\joyingbot-new-h20-hyperframes-dev\pojo\models.py`
- `C:\Users\admin\Desktop\joyingbot-new-h20-hyperframes-dev\scheduler\collect_scheduler.py`
- `C:\Users\admin\Desktop\joyingbot-new-h20-hyperframes-dev\crm\crm_request_util.py`

## 相关记录

- [[projects/joyingbot-new/docs/00-docs-index|参考文档索引]]
