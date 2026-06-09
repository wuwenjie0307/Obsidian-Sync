---
date: "2026-06-09"
tags: [changelog, h20, hyperframes, video, template]
---

# h20-hyperframes-template-visual-phase-2026-06-09

## 改动类型

- [x] 新功能
- [ ] Bug 修复
- [x] 重构
- [x] 配置变更

## 改动内容

完成 H20 HyperFrames / 网感视频后端阶段 06：模板视觉实现。

新增 `hyperframes-postprocess/DESIGN.md`：
- 固化 `science_guide` 的 `template-7 + wanggan` 视觉身份：首帧背景、半透标题带、毛笔黄字标题、人物前景层、成对网感字幕、黄字 emphasis。
- 固化 `video_diary` 的 diary 视觉身份：REC、日期、Day/Diary、人物叠层、低位字幕与动作 cue。
- 记录两个模板的字体、颜色和禁止项，避免把原型默认角标/样本文案写死进 H20。

新增 `hyperframes-postprocess/index.js`：
- 读取 Phase 05 `manifest.json`，校验必填字段。
- 解析 `templates_style_id/template_id`，`1=science_guide`、`2=video_diary`，`3=minimal` 直接失败并保持旧链路边界。
- 增加模板字段冲突校验，避免直接调用 Node 后处理时静默选错模板。
- 读取 `whisper_timeline.json` 与 `hyperframes_analysis.json`，生成 `subtitle_timeline.json`。
- 每条字幕最多写入一个 emphasis span，关键词来自结构化分析，时间来自 Whisper。
- 将 Push/Zoom 写为可渲染 action cue，动作时间仍绑定 Whisper segment。
- 生成 `composition/index.html`，包含 HyperFrames `data-composition-id="main"`、视频/音频 track、开场模板、字幕和动作层。
- 生成 1080x1920（或 manifest 指定尺寸）的本地 `cover.png`。
- 默认调用 `npx hyperframes render`；测试/联调可用 `HF_POSTPROCESS_RENDER_CMD` 替换真实渲染命令。
- 写出 `result.json` 的 `success/final_video_path/cover_path/subtitle_timeline_path/render_ms/error`。

新增 `test/test_hyperframes_postprocess.py`：
- 覆盖 `science_guide` 生成 wanggan composition、subtitle timeline、cover PNG、result 成功产物。
- 覆盖 `video_diary` 生成 diary composition、REC/date/Day/Diary 元素和动作 cue。
- 覆盖 `minimal` 直接调用 Node 后处理时明确失败。
- 覆盖 `templates_style_id` 与 `template_id` 冲突时失败，防止绕过 Python 路由。

Apidoc 核对：
- 本阶段不新增 CRM/CSM 外部接口字段，不修改回调 payload。
- `crm` 项目 699/701 创建接口仍包含 `templates_style_id`。

## 影响范围

- `hyperframes-postprocess/DESIGN.md`
- `hyperframes-postprocess/index.js`
- `test/test_hyperframes_postprocess.py`

验证结果：
- `python -m unittest test.test_hyperframes_postprocess -v` 通过。
- `node --check hyperframes-postprocess\index.js` 通过。
- `python -m unittest test.test_hyperframes_cli -v` 通过。
- `python -m unittest test.test_hyperframes_analysis -v` 通过。
- `python -m unittest test.test_template_route -v` 通过。
- `python -m unittest test.test_hyperframes_postprocess test.test_whisper_timeline test.test_scheduled_video_voice_params test.test_production_baseline_alignment -v` 通过。
- `python -m py_compile router/service/video_server2/hyperframes_cli.py router/service/video_server2/hyperframes_analysis.py router/service/video_server2/whisper_timeline.py router/service/video_server2/video_work.py scheduler/collect_scheduler.py pojo/models.py` 通过。
- `git diff --check` 通过，仅有工作区 LF/CRLF 提示。

遗留事项：
- 当前环境未执行真实 `npx hyperframes render` / Chromium / FFmpeg 渲染，只通过 fake renderer 验证 Node postprocess 合同。
- `cover.png` 当前保证尺寸和路径，真实首帧/人物抠像封面效果需要阶段 08 在 H20 环境抽帧验收。
- 阶段 07 仍需实现最终视频/封面上传、URL 字段和成功/失败回调。
