---
tags: [git, workflow, test, deploy]
updated: 2026-05-29
---

# Git 分支提交流程

## 当前规则

上线前只合到 `test`，不要往 `master` 推送或创建合并请求。`master` 只在真正上线前按团队流程处理。

推荐流程：

```text
origin/test -> 新工作分支 -> 提交改动 -> 推送工作分支 -> MR 到 test -> 验证 -> 上线前再处理 master
```

## 进入本地仓库

```powershell
cd C:\Users\admin\Desktop\joyingbot-new
```

查看当前状态：

```powershell
git status --short --branch
```

如果看到 `M 文件名`，说明有本地未提交改动。先确认这些改动是否需要本次提交，不要直接切分支或推送。

## 拉取远端最新代码

更新远端引用：

```powershell
git fetch origin --prune
```

切到 `test`：

```powershell
git switch test
```

如果本地没有 `test` 分支：

```powershell
git switch -c test origin/test
```

更新本地 `test` 到远端最新：

```powershell
git pull --ff-only origin test
```

如果这里不能 fast-forward，先停下来排查，不要强行 reset。

## 从 test 拉工作分支

不要直接在 `test` 上改代码。先从最新 `test` 拉新分支：

```powershell
git switch -c feature/your-change-name
```

分支名建议使用业务含义，例如：

```text
feature/voice-clone-params
fix/crm-callback-error
docs/h20-deploy-note
h20-bot-48100-gateway-test
```

避免使用空格、中文、过于个人化或无意义的分支名。

## 修改后检查差异

查看改了哪些文件：

```powershell
git status --short
```

查看具体差异：

```powershell
git diff
```

查看某个文件差异：

```powershell
git diff README.md
```

## 提交前检查

如果改了 JSON：

```powershell
python -m json.tool config/config-dev.json > $null
```

检查空白、冲突标记等问题：

```powershell
git diff --check
```

如果刚处理过冲突，再查一次冲突标记：

```powershell
rg -n "<<<<<<<|=======|>>>>>>>" .
```

## 暂存文件

优先按文件暂存，不要无脑 `git add .`：

```powershell
git add README.md
git add config/config-dev.json
git add docs/superpowers/plans/xxx.md
```

确认暂存状态：

```powershell
git status --short
```

左侧出现字母表示已暂存，例如：

```text
M  README.md
A  docs/xxx.md
```

## 提交 commit

```powershell
git commit -m "docs: update h20 bot gateway plan"
```

常用提交前缀：

| 前缀 | 用途 |
|---|---|
| `feat:` | 新功能 |
| `fix:` | 修复 bug |
| `docs:` | 文档 |
| `config:` | 配置调整 |
| `chore:` | 杂项维护 |

查看最新提交：

```powershell
git log -1 --oneline
```

## 推送工作分支

第一次推送新分支：

```powershell
git push -u origin feature/your-change-name
```

后续同一分支追加提交后：

```powershell
git push
```

## 创建 MR 到 test

在 GitLab 仓库创建合并请求：

```text
https://git.joyingai.cn/services/crm.ai.joyingbot
```

选择：

```text
Source branch: feature/your-change-name
Target branch: test
```

不要选择 `master` 作为目标分支，除非已经进入正式上线流程。

MR 描述建议包含：

```text
本次改动：
1. ...
2. ...

验证：
1. python -m json.tool config/config-dev.json > $null
2. git diff --check
3. 相关接口或页面验证结果
```

## 合并到 test

推荐通过 GitLab MR 页面点击 `Merge`。

合并后，本地同步 `test`：

```powershell
git switch test
git pull --ff-only origin test
```

如果确认工作分支已合并，可以删除本地分支：

```powershell
git branch -d feature/your-change-name
```

远端分支是否删除按团队习惯处理；不确定时不要删。

## 直接推到 test 的方式

只有在明确允许时使用。推荐仍然走 MR。

如果当前分支就是从最新 `origin/test` 拉出来的，并且只领先 `test` 一个或几个目标提交，可以直接推到远端 `test`：

```powershell
git push origin HEAD:test
```

这会更新远端 `test`。执行前必须确认：

1. 当前分支基于最新 `origin/test`。
2. `git status --short --branch` 显示工作区干净。
3. 不包含本地临时说明、账号、密码、个人偏好等不应提交的内容。
4. 没有往 `master` 推。

## 暂存本地不想提交的改动

如果有某个本地文件不想进入提交，可以单独 stash：

```powershell
git stash push -m "local note" -- AGENTS.md
```

查看 stash：

```powershell
git stash list
```

恢复最近一次 stash：

```powershell
git stash pop
```

查看某个 stash 内容：

```powershell
git stash show -p stash@{0}
```

## 冲突处理

出现冲突时，先看状态：

```powershell
git status --short
```

冲突文件里通常会出现：

```text
<<<<<<< HEAD
当前分支内容
=======
要合进来的内容
>>>>>>> branch-name
```

手动编辑成最终想保留的内容，删除冲突标记，然后：

```powershell
git add 冲突文件
```

如果是在 merge：

```powershell
git merge --continue
```

如果是在 cherry-pick：

```powershell
git cherry-pick --continue
```

如果判断这次操作不该继续：

```powershell
git merge --abort
```

或：

```powershell
git cherry-pick --abort
```

## 本次 h20 示例

本次实际做法：

1. 从 `origin/test` 拉出 `h20-bot-48100-gateway-test`。
2. 把 h20 端口方案提交移植到该分支。
3. 解决 `README.md` 冲突。
4. 确认没有带入不应提交的本地说明。
5. 执行检查：
   ```powershell
   python -m json.tool config/config-dev.json > $null
   git diff --check
   ```
6. 推送到远端 `test`：
   ```powershell
   git push origin HEAD:test
   ```

远端 `test` 当前相关提交：

```text
45b4e66d docs: update h20 bot 48100 gateway plan
```
