---
tags: [bug, h20, vibevideo, hyperframes, montage, timing]
status: fixed
severity: medium
date: 2026-06-28
---

# H20 网感视频混剪全文覆盖估时偏移

## 问题描述

测试视频 `user4_1782622529312_51ec1196e5462e74.mp4` 中，混剪素材和对应口播文案出现约一句话的偏移。实看视频后确认：约 7.5s 字幕已经进入“目前均价19875元/m²总价”，但画面仍停留在室内素材；直到约 9.5s 才切到室外素材，导致价格文案前半句仍被上一段素材覆盖。

## 原因

网感视频的 `_apply_hyperframes_overlay_timings` 在 `material_reference_texts` 能覆盖原始文案 80% 以上时，会进入 `full_cover_time_ranges()`。旧逻辑用“原始文案字符位置 / 全文长度”线性映射到视频时间，没有优先使用 Whisper `subtitle_segments` 的真实时间边界。口播各句语速不均时，线性估算会把素材边界推迟或提前，形成一句左右的错位。

## 解决方案

保留原有参考文案排序和 80% 覆盖判断，避免恢复旧问题；但在全文覆盖分支中先把 Whisper subtitle cue 映射回参考文案位置。如果素材的开始/结束边界能落到真实 cue 上，就用 cue 的真实时间计算覆盖区间；只有 cue 无法匹配时，才回退到旧的线性估时。

## 优化点

- 不改极简风格旧链路，只调整 HyperFrames / 网感视频 overlay timing helper。
- 不取消参考文案排序，继续保护 DB sort_order 与真实脚本顺序不一致的问题。
- 不恢复“高覆盖率就整段铺满视频”的旧行为，首尾未选中文案仍应露出原视频。
- 后续如果日志允许，生成时可以打印 full-cover 分支采用 cue timing 还是 linear fallback，便于线上复盘。

## 验证

- 本地抽帧确认真实视频在 7.5s 到 9.5s 之间存在素材/文案错位。
- 新增回归测试：`test_hyperframes_overlay_timings_full_cover_uses_real_cue_timing_when_available`。
- `python -m unittest test.test_video_material_montage_sync`：15 tests OK。
- 相关 HyperFrames/模板/素材策略测试组：181 tests OK。

## 相关文件

- `scheduler/collect_scheduler.py`
- `test/test_video_material_montage_sync.py`

## 关联记录

- [[projects/joying-bot-server/bugs/h20-vibevideo-montage-reference-timing-regression-2026-06-28|h20-vibevideo-montage-reference-timing-regression-2026-06-28]]

## 2026-06-28 追加复盘：task_id=1605

测试服 `task_id=1605` 仍出现混剪素材和口播文案相差半句到一句：第一段应在“每年三月份这份报告”附近立即出现但慢了一点，第三段应在“核心方向其实没差”开始切换但仍停留在上一段素材。

更准确的根因是断句边界不够干净：用户选择的混剪文案边界和最终 `subtitle_segments` 的 cue 边界不一定完全一致，半句可能被分到上一条或下一条 cue。旧逻辑只接受素材边界落在 cue 内部，边界正好贴着相邻 cue 起点/终点时会错过真实时间，然后整组回退到全文线性估算，表现为少半句、多半句或慢一句。

修复方向：`full_cover_time_ranges()` 中的 `cue_time()` 在常规 cue 内插值之外，额外识别相邻 cue 的精确边界。素材起点贴着上一条 cue 的结束、或素材终点贴着下一条 cue 的开始时，都优先使用真实 cue 时间；只有 cue 完全无法证明边界时才保留线性 fallback。

验证补充：
- 新增 `test_hyperframes_overlay_timings_full_cover_uses_neighbor_cue_boundaries`，覆盖第三段交界处 cue 缺失/断句偏移时不应回退线性估算。
- 新增 `test_hyperframes_overlay_timings_full_cover_starts_after_unselected_neighbor_cue`，覆盖第一段前方有未选中文案、素材起点贴着前一个 cue 结束的场景。
- `python -m unittest test.test_video_material_montage_sync`：17 tests OK。
- HyperFrames/混剪相关子集 145 tests OK。

## 2026-06-28 追加复盘：重复文案顺序匹配

产品参考的模板5方案说明，副视频不应靠“第几个素材对应第几句字幕”，而应靠 `enterText / exitText / anchorText` 这类文本锚点去主视频 ASR 时间轴定位。结合现有链路，短期不引入前端选区索引字段，先在后端增强 full-cover 匹配策略。

新增风险：如果用户把同一段文案复制多遍，多个混剪素材绑定的文案文本完全相同，旧的 `reference.find(needle)` 会每次从全文开头匹配，后面的素材可能落回第一段重复文案，或导致 full-cover 覆盖率不足后退回普通 cue 匹配。

修复方向：在 `full_cover_time_ranges()` 中优先按素材顺序向后匹配文案位置；只有顺序匹配失败时，再保留旧的任意位置匹配作为兼容兜底，避免影响历史数据里素材顺序异常的场景。

验证补充：
- 新增 `test_hyperframes_overlay_timings_full_cover_matches_repeated_text_in_order`，覆盖同一段文案重复两遍时，两个素材应分别落到 0-10 秒和 10-20 秒。
- `python -m unittest test.test_video_material_montage_sync`：18 tests OK。
- HyperFrames/混剪相关子集 146 tests OK。

## 2026-06-28 追加复盘：task_id=1610 漏图片素材与第一段切早

测试服 `task_id=1610` 使用模板2网感链路，用户侧认为选择了 3 个混剪素材，但最终视频只生效 2 个，并且第一段混剪素材在口播文案没说完时提前结束。对照产品认为正确的 URL 后确认：正确视频对应 `task_id=1611`，且是模板1；它的 3 个素材在库里都是 `material_type=1/is_mix_material=1`，manifest 里有 3 个 overlay，时间段连续。

1610 的差异点：
- DB 中 3 条有效素材按 `id.asc()` 为视频A、视频B、图片C。
- 视频A、视频B 是 `material_type=1/is_mix_material=1`。
- 图片C 是 `material_type=2/is_mix_material=0`，但它的文案正好是第三段混剪应覆盖的文案。
- 旧 selected-only 逻辑一旦存在显式选中素材，就只使用 `is_mix_material=1` 的素材，因此图片C被当作未选素材过滤，manifest 只剩 2 个 overlay。

H20 只读检查确认：
- 1610 manifest `overlay_materials count=2`。
- A: `[8.54, 27.46]`，只覆盖到 cue “着力稳定房地产市场”，后续“因城施策...”被提前切掉。
- B: `[43.12, 69.62]`。
- 图片C完全不在 manifest 中。
- 1611 manifest `overlay_materials count=3`，时间段连续 `[7.08,32.66] [32.66,62.12] [62.12,98.36]`。

进一步原因：图片C丢失后，A+B 对用户原文覆盖不足，无法进入 full-cover/cue-boundary 分支，于是回到旧逐 cue 匹配。旧匹配直接拿素材文案找 ASR cue，遇到 ASR 错字、断句和漏词会在第一个断点停止，所以 A 被截到 27.46s。

修复方向：
- 不放开所有未选素材，避免把普通未选素材误混入。
- 仅在网感 HyperFrames 链路中启用上下文恢复：当显式选中素材本身不足以形成连续主选区，但所有有效素材按原始顺序能在用户原文中形成高密度连续覆盖时，恢复这些漏标的图片/视频素材。
- 对 full-cover 判断增加“连续主选区密度”条件：整体覆盖率略低于 80%，但素材覆盖区间内部几乎连续时，也允许使用原文定位 + cue 边界校准，避免回退旧 cue 兜底。

验证补充：
- 新增 `test_generation_recovers_contextual_unselected_materials_for_full_cover`，覆盖 1610 这种 2 个视频选中、1 张图片漏标但文案连续的恢复。
- 新增 `test_hyperframes_overlay_timings_uses_dense_selected_span_below_eighty_percent`，覆盖整体覆盖率低于 80% 但连续主选区应使用 cue 边界校准的情况。
- 新增 `test_generation_recovers_mixed_video_photo_contextual_materials`，覆盖多个视频/图片混排、多个图片漏标但文案连续时应恢复。
- `python -m unittest test.test_video_material_montage_sync`：21 tests OK。
- HyperFrames/混剪相关子集 149 tests OK。
