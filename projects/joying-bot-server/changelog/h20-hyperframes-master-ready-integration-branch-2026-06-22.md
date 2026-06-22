---
date: "2026-06-22"
project: "joying-bot-server"
type: changelog
tags: [changelog, h20, hyperframes, git, merge, test]
aliases: ["h20-hyperframes-master-ready-integration-branch-2026-06-22"]
---

# h20-hyperframes-master-ready-integration-branch-2026-06-22

## Graph Links

- Project: [[projects/joying-bot-server/00-项目概览|joying-bot-server]]
- Index: [[projects/joying-bot-server/changelog/00-changelog-index|changelog index]]
- Related doc: [[projects/joying-bot-server/docs/h20-master-release-merge-risk-2026-06-22|h20-master-release-merge-risk-2026-06-22]]

## Change Type

- [ ] Feature
- [ ] Bug fix
- [ ] Refactor
- [x] Branch integration
- [x] Documentation

## Summary

- Created the unified integration branch from `origin/master`:
  - `feature/ai_v6.3.3_vibevideo_master_ready`
- Merged `origin/feature/ai_v6.3.1_video_new` into the integration branch.
- Merged `origin/feature/ai_v6.3.3_vibevideo` into the integration branch.
- Original feature branches were not modified:
  - `feature/ai_v6.3.1_video_new`
  - `feature/ai_v6.3.3_vibevideo`
- Main development worktree was switched to the integration branch:
  - `C:\Users\admin\Desktop\joyingbot-new-h20-hyperframes-dev`
- The integration branch was pushed to GitLab.

## Preserved Behavior

- From v6.3.1 branch:
  - HeyGem 30-minute timeout handling.
  - Retryable busy/timeout error detection.
  - Scheduler performance logs.
  - Existing old video route and montage compatibility.
  - Preassigned model-config release fallback.
- From v6.3.3 branch:
  - HyperFrames routing for science-guide and video-diary templates.
  - Semantic subtitle segmentation and balanced render-time line breaking.
  - Subtitle translation reuse.
  - Simplified Chinese normalization.
  - Script-text based ASR near-miss repair.
  - DB quarantine for busy model instances.

## Impact

- Future H20 HyperFrames / vibe-video work should continue on:
  - `feature/ai_v6.3.3_vibevideo_master_ready`
- Recommended release flow:
  - integration branch -> `test` validation -> same integration branch -> `master`
- Do not merge `test` back into the integration branch only for conflict checking, because `test` contains many unrelated test-stage commits.

## Verification

- Latest integration commit:
  - `439c1912 Merge feature ai_v6.3.3 vibevideo into master-ready branch`
- Prior merge commit:
  - `32e20089 Merge remote-tracking branch 'origin/feature/ai_v6.3.1_video_new' into feature/ai_v6.3.3_vibevideo_master_ready`
- Remote sync check:
  - `origin/feature/ai_v6.3.3_vibevideo_master_ready...HEAD = 0 0`
- Pre-commit checks:
  - `git diff --check --cached` passed.
  - Conflict marker scan passed.
  - Key Python files passed `py_compile`.
  - Relevant unittest suite passed: 159 tests OK.

## Test Merge Preflight

- Command:
  - `git merge-tree --write-tree origin/test origin/feature/ai_v6.3.3_vibevideo_master_ready`
- Result:
  - Conflict found. No direct merge to `test` was performed.
- Conflict file:
  - `scheduler/collect_scheduler.py`
- Branch distance:
  - `origin/test...origin/feature/ai_v6.3.3_vibevideo_master_ready = 932 / 7`
- Interpretation:
  - `test` has many unrelated commits.
  - Next step should be a target-side temporary merge branch from `origin/test`, resolve `scheduler/collect_scheduler.py` there, run tests, then ask for explicit confirmation before updating shared `test`.

## Related Files

- `scheduler/collect_scheduler.py`
- `router/crm_server.py`
- `router/service/video_server2/video_work.py`
- `router/service/video_server2/template_route.py`
- `router/service/video_server2/hyperframes_cli.py`
- `router/service/video_server2/hyperframes_subtitle_translation.py`
- `hyperframes-postprocess/templates/universal.html`
- `hyperframes-postprocess/reference_styled_subtitles.js`
- `test/test_video_model_busy_retry.py`
- `test/test_hyperframes_postprocess.py`
- `test/test_template_route.py`
- `test/test_production_baseline_alignment.py`

## Related Notes

- [[projects/joying-bot-server/changelog/h20-hyperframes-science-guide-translation-simplified-fix-2026-06-18|h20-hyperframes-science-guide-translation-simplified-fix-2026-06-18]]
- [[projects/joying-bot-server/changelog/h20-hyperframes-test-merge-template3-sourcehan-2026-06-18|h20-hyperframes-test-merge-template3-sourcehan-2026-06-18]]
- [[projects/joying-bot-server/docs/h20-master-release-merge-risk-2026-06-22|h20-master-release-merge-risk-2026-06-22]]

## Related Commits

- `439c1912`
- `32e20089`
## Test-Side Merge Branch Result

- Created target-side branch from `origin/test`:
  - `codex/merge-vibevideo-master-ready-to-test`
- Worktree path:
  - `C:\Users\admin\Desktop\joyingbot-new-h20-hyperframes-dev\.codex-worktrees\merge-vibevideo-master-ready-to-test`
- Merged source branch:
  - `origin/feature/ai_v6.3.3_vibevideo_master_ready`
- Conflict resolved:
  - `scheduler/collect_scheduler.py`
- Resolution choice:
  - Kept `test` baseline wrapper/state behavior.
  - Kept integration branch model-pool behavior: busy errors set pending retry state and call `_quarantine_comfyui_config`, so bad model instances are removed from scheduling through DB `is_active=0` instead of in-memory cooldown.
- Verification after conflict resolution:
  - `git diff --check --cached` passed.
  - Conflict marker scan passed.
  - Key Python files passed `py_compile`.
  - Relevant unittest suite passed: 159 tests OK.
- Merge commit on temporary branch:
  - `27469a84 Merge vibevideo master-ready branch into test baseline`
- Pushed branch:
  - `origin/codex/merge-vibevideo-master-ready-to-test`
- Shared `test` branch status:
  - Not updated yet. Direct update to `test` still needs explicit confirmation.
## Shared Test Branch Update

- User confirmation received:
  - `确认合入`
- Final pre-push safety checks:
  - `git fetch origin --prune` completed.
  - `origin/test` was confirmed as an ancestor of `HEAD`.
  - `origin/test...HEAD = 0 / 8`, so updating `test` was a fast-forward push.
- Fresh pre-push verification:
  - `git diff --check origin/test..HEAD` passed.
  - Conflict marker scan passed.
  - Key Python files passed `py_compile`.
  - Relevant unittest suite passed: 159 tests OK.
- Shared branch update:
  - `git push origin HEAD:test`
  - Remote `test` moved from `83f8bcbe` to `27469a84`.
- Post-push confirmation:
  - `origin/test` now points to `27469a84 Merge vibevideo master-ready branch into test baseline`.
- Follow-up:
  - Test server should be deployed/restarted from `test` before real video-chain validation.
