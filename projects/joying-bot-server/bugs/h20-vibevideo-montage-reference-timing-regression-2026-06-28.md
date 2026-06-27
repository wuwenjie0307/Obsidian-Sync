---
date: "2026-06-28"
project: "joying-bot-server"
type: bug
status: fixed
severity: high
tags: [bug, h20, vibevideo, hyperframes, montage, subtitle-timing]
aliases: ["网感视频混剪素材文案对齐回归"]
---

# 网感视频混剪素材文案对齐回归

## 图谱链接

- 项目: [[projects/joying-bot-server/00-项目概览|joying-bot-server]]
- 索引: [[projects/joying-bot-server/bugs/00-bugs-index|Bug 记录索引]]
- 相关旧记录: [[projects/joying-bot-server/bugs/h20-montage-material-filter-is-mix-flag-2026-06-12|h20-montage-material-filter-is-mix-flag-2026-06-12]]

## 问题描述

网感视频混剪在多轮修复后仍出现回归：用户选择了指定分镜文案对应的混剪素材，但最终视频里出现素材和文案时间不对齐、素材从开头就覆盖、部分选中文案没有被素材覆盖、相邻混剪之间短暂露出原视频等问题。

这次重点复现任务：

- `task_id=1581`: `https://videos-test.joyingai.cn/video/crm/20260628/user4_1782578002113_51ec1196e5462e74.mp4`
- `task_id=1582`: `https://videos-test.joyingai.cn/video/crm/20260628/user4_1782578070340_51ec1196e5462e74.mp4`

## 复现现象

1. `1581` 的混剪素材只覆盖口播文案中间大段内容，开头和结尾有未选择文案，但旧逻辑把第一个素材从视频 0 秒开始铺上，导致“未选择文案也被混剪覆盖”。
2. `1582` 的素材在数据库里的 `sort_order` 是 C、B、A，但真实文案顺序是 A、B、C。旧 fallback 没有按文案位置重排，导致时间轴和素材顺序错位。
3. 相邻混剪素材如果被旧逻辑错误切分或补间，可能在两个素材之间短暂露出原视频，看起来像闪一下。

## 期望行为

- 用户选了哪段分镜文案，混剪素材就只覆盖那段文案对应的口播时间。
- 没选中的开头、结尾、中间空白文案保持原视频，不要被“全覆盖兜底”吞掉。
- 多个混剪素材必须按文案出现顺序排，而不是盲信数据库返回顺序。
- 相邻选中文案应连续衔接，不应人为插入原视频闪一下。

## 实际行为

旧逻辑在“素材文案总覆盖率较高”时，会进入 full-cover 兜底：

- 要求覆盖率大于 80%。
- 允许首尾 10% 的文案不匹配。
- 允许内部少量 gap。
- 一旦通过，就把第一个素材从 `video_start` 开始，最后一个素材铺到 `video_end`。

这个兜底对“用户确实选择全篇混剪”有用，但对“用户故意留出开头/结尾/中间不混剪”的场景过度激进。

## 原因

根因是混剪时间轴把“素材文案覆盖率高”误判成“整条视频都应被混剪覆盖”。

更具体地说：

1. `1581` 中用户没有选择开头约 5.9% 和结尾约 7.3% 的文案，但旧逻辑因为总覆盖率超过 80%，直接把素材拉满到整条视频，导致一开始就混剪。
2. `1582` 中第一个选中素材从文案约 11% 处开始，超过旧逻辑 10% 边界阈值，full-cover 兜底没有生效，后续 fallback 又按数据库顺序处理 C、B、A，最终与文案顺序 A、B、C 对不上。
3. 旧逻辑为了“补齐覆盖”会桥接到下一个素材开始时间或视频结尾，这会把用户没选的文案也当作混剪区间处理。

## 解决方案

最小修复放在 `scheduler/collect_scheduler.py` 的 `_apply_hyperframes_overlay_timings`：

- 仍保留“素材文案总覆盖率 >= 80%”这个识别入口。
- 进入该入口后，不再做首尾边界吸附，不再用下一个素材开始时间强行桥接。
- 按每个素材在原始口播文案里的匹配位置排序。
- 每个素材只映射自己的 `start/end` 文案区间到视频时间。
- 未被选中的前后文和中间 gap 保持原视频。

这条规则是当前最小可控方案：既能修复“用户只选中部分文案”的场景，也不破坏全篇都选中时的连续覆盖。

## 优化点

后续不要轻易恢复以下逻辑：

- 不要因为覆盖率高就把混剪强制铺满整条视频。
- 不要用数据库 `sort_order` 替代文案匹配顺序。
- 不要用边界阈值判断是否丢弃 reference matching；首尾留白本身就是合法选择。
- 不要为了消除小 gap 去吞掉用户未选择的文案。

如果未来要继续增强，优先做数据校验：在创建任务时检查每个混剪素材的“分镜文案”能否在最终口播文案里找到，而不是在渲染阶段猜。

## 回归测试覆盖

混剪相关回归现在至少要覆盖这些场景：

- 文案和素材对齐：素材按原始文案位置映射时间，而不是按 DB 顺序。
- 少混剪素材 / 素材没用上：显式混剪素材、fallback 到任务素材、下载后的 overlay 都要进入 manifest。
- 只覆盖部分选中文案：素材时间不能被强行扩展到整条视频。
- 未选择的开头/结尾：不应被混剪覆盖。
- 未选择的中间 gap：应保留原视频。
- 相邻混剪素材：相邻文案可以连续衔接，不应插入原视频闪一下。
- ASR/字幕断句或错字：仍通过原文案 reference matching 尽量对齐。

本次新增/确认的测试：

- `test_hyperframes_overlay_timings_keeps_unselected_script_edges`
- `test_hyperframes_overlay_timings_sorts_reference_matches_and_keeps_gaps`
- `test_hyperframes_overlay_timings_reuse_minimal_gap_repair`
- `test_hyperframes_overlay_timings_covers_selected_subtitle_across_cues`
- `test_hyperframes_overlay_timings_tolerates_asr_typos_across_cues`
- `test_hyperframes_overlay_timings_uses_original_script_segments_for_full_cover`

## 验证结果

本地验证命令：

```powershell
python -m unittest test.test_video_material_montage_sync
python -m py_compile scheduler\collect_scheduler.py test\test_video_material_montage_sync.py
git diff --check -- scheduler\collect_scheduler.py test\test_video_material_montage_sync.py
```

验证结论：

- `test.test_video_material_montage_sync`: 14 个测试通过。
- `py_compile`: 通过。
- `git diff --check`: 通过，仅有 Windows 工作区 LF/CRLF 提示。

## 相关文件

- `scheduler/collect_scheduler.py`
- `test/test_video_material_montage_sync.py`

## 相关记录

- 2026-06-28 测试库 `task_id=1581`：部分选中文案被错误拉满覆盖。
- 2026-06-28 测试库 `task_id=1582`：DB 素材顺序和文案顺序不一致导致错位。