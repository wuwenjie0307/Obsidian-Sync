---
tags: [gitlab, git, guide, beginner, workflow]
updated: 2026-06-02
---

# GitLab 新手连接、上传分支、合并指南

这是一份通用流程，不绑定任何单个项目。把示例里的仓库地址、分支名、文件名替换成自己的即可。

## 0. 先理解几个概念

| 名词 | 含义 |
|---|---|
| Git | 本地代码版本管理工具 |
| GitLab | 远端代码托管平台，类似 GitHub |
| repository / repo | 一个代码仓库 |
| remote | 本地 Git 记录的远端仓库地址，常见名字是 `origin` |
| branch | 分支，例如 `main`、`master`、`develop`、`test`、`feature/login` |
| commit | 一次代码提交记录 |
| push | 把本地提交上传到 GitLab |
| fetch | 从 GitLab 拉取远端分支信息，但不改本地文件 |
| pull | 拉取远端代码并合入当前本地分支 |
| merge request / MR | GitLab 里的合并请求，把一个分支合到另一个分支 |
| target branch | MR 要合进去的目标分支，例如 `test`、`main` |
| source branch | MR 的来源分支，例如 `feature/video-quality` |

推荐团队流程：

```text
目标分支最新代码 -> 新建工作分支 -> 修改代码 -> 提交 commit -> push 工作分支 -> GitLab 创建 MR -> 合并到目标分支
```

不要一上来就在 `main`、`master`、`test` 这类公共分支直接改，除非团队明确允许。

## 1. 第一次使用 Git 前的本地配置

安装 Git 后，先配置提交人信息：

```bash
git config --global user.name "Your Name"
git config --global user.email "your-email@example.com"
```

查看配置：

```bash
git config --global --list
```

这两个值会出现在 commit 记录里，建议使用公司 GitLab 账号对应的邮箱。

## 2. 连接 GitLab 的两种方式

GitLab 常见连接方式有两种：HTTPS 和 SSH。任选一种即可。

### 方式 A：HTTPS

仓库地址通常长这样：

```text
https://gitlab.example.com/group/project.git
```

克隆代码：

```bash
git clone https://gitlab.example.com/group/project.git
cd project
```

如果 GitLab 开启了双因素认证，推送时通常不能用网页登录密码，需要用 Personal Access Token。

创建 token 的通用路径：

```text
GitLab 右上角头像 -> Preferences / Edit profile -> Access Tokens
```

常用权限：

```text
read_repository
write_repository
```

注意：不要把 token 写进代码、文档、截图或聊天记录。

### 方式 B：SSH

SSH 仓库地址通常长这样：

```text
git@gitlab.example.com:group/project.git
```

先生成 SSH key：

```bash
ssh-keygen -t ed25519 -C "your-email@example.com"
```

一路回车会生成：

```text
~/.ssh/id_ed25519
~/.ssh/id_ed25519.pub
```

查看公钥内容：

```bash
cat ~/.ssh/id_ed25519.pub
```

Windows PowerShell 可以用：

```powershell
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub
```

把 `.pub` 公钥复制到 GitLab：

```text
GitLab 右上角头像 -> Preferences / SSH Keys -> Add new key
```

测试连接：

```bash
ssh -T git@gitlab.example.com
```

看到欢迎信息或认证成功提示，就可以 clone：

```bash
git clone git@gitlab.example.com:group/project.git
cd project
```

## 3. 检查当前仓库连接的是哪个 GitLab

进入本地仓库目录：

```bash
cd path/to/project
```

查看远端地址：

```bash
git remote -v
```

常见输出：

```text
origin  https://gitlab.example.com/group/project.git (fetch)
origin  https://gitlab.example.com/group/project.git (push)
```

如果没有远端，可以添加：

```bash
git remote add origin https://gitlab.example.com/group/project.git
```

如果远端地址错了，可以修改：

```bash
git remote set-url origin https://gitlab.example.com/group/project.git
```

SSH 方式则改成：

```bash
git remote set-url origin git@gitlab.example.com:group/project.git
```

## 4. 查看本地当前状态

任何操作前，先看状态：

```bash
git status --short --branch
```

示例：

```text
## feature/demo...origin/feature/demo
 M app.py
?? notes.md
```

含义：

| 标记 | 含义 |
|---|---|
| `M file` | 文件被修改了 |
| `A file` | 新文件已暂存 |
| `?? file` | 新文件未被 Git 跟踪 |
| `## branch...origin/branch` | 当前分支和远端分支的关系 |
| `ahead 1` | 本地比远端多 1 个提交，还没 push |
| `behind 1` | 远端比本地多 1 个提交，需要 pull |

## 5. 从目标分支拉最新代码

假设团队要求合到 `test`。如果你的团队用 `main`、`master`、`develop`，把命令里的 `test` 替换掉即可。

先更新远端分支信息：

```bash
git fetch origin --prune
```

切到目标分支：

```bash
git switch test
```

如果本地没有这个分支：

```bash
git switch -c test origin/test
```

把本地目标分支更新到远端最新：

```bash
git pull --ff-only origin test
```

如果 `--ff-only` 失败，说明本地和远端历史不一致。不要直接强推，先找同事或负责人确认。

## 6. 从目标分支创建自己的工作分支

不要直接在公共目标分支上改。先创建工作分支：

```bash
git switch -c feature/your-change-name
```

分支命名建议：

```text
feature/login-page
fix/video-quality
docs/gitlab-guide
chore/update-dependencies
```

命名规则建议：

- 用英文、小写、短横线。
- 不用空格。
- 不用个人名字当主要含义。
- 分支名体现业务内容。

## 7. 修改代码后检查差异

查看哪些文件变了：

```bash
git status --short
```

查看具体改动：

```bash
git diff
```

只看某个文件：

```bash
git diff path/to/file.py
```

检查是否有冲突标记：

```bash
rg -n "<<<<<<<|=======|>>>>>>>" .
```

如果没有 `rg`，用：

```bash
grep -R -n "<<<<<<<\\|=======\\|>>>>>>>" .
```

检查空白问题：

```bash
git diff --check
```

## 8. 暂存要提交的文件

推荐按文件添加，不要无脑 `git add .`：

```bash
git add path/to/file1.py
git add path/to/file2.py
```

如果确实确认所有改动都要提交：

```bash
git add .
```

查看暂存状态：

```bash
git status --short
```

左侧有字母表示已经暂存：

```text
M  path/to/file1.py
A  path/to/new_file.py
```

取消暂存某个文件：

```bash
git restore --staged path/to/file.py
```

放弃某个文件的本地修改：

```bash
git restore path/to/file.py
```

注意：`git restore path/to/file.py` 会丢掉这个文件未提交的修改，执行前要确认。

## 9. 提交 commit

提交：

```bash
git commit -m "fix: preserve video quality"
```

常用 commit 前缀：

| 前缀 | 用途 |
|---|---|
| `feat:` | 新功能 |
| `fix:` | 修 bug |
| `docs:` | 文档 |
| `test:` | 测试 |
| `refactor:` | 重构 |
| `chore:` | 杂项维护 |
| `config:` | 配置调整 |

查看最新提交：

```bash
git log -1 --oneline
```

## 10. 推送工作分支到 GitLab

第一次推送新分支：

```bash
git push -u origin feature/your-change-name
```

`-u` 的意思是建立本地分支和远端分支的跟踪关系。之后同一个分支再推送，只需要：

```bash
git push
```

如果你看到类似提示：

```text
To create a merge request for feature/your-change-name, visit:
https://gitlab.example.com/group/project/-/merge_requests/new?...
```

说明分支已经推到 GitLab 了，可以去页面创建 MR。

## 11. 在 GitLab 页面创建 Merge Request

打开 GitLab 项目页面：

```text
https://gitlab.example.com/group/project
```

进入：

```text
Merge requests -> New merge request
```

选择：

```text
Source branch: feature/your-change-name
Target branch: test
```

如果你的团队目标分支是 `main`、`master`、`develop`，就选择对应目标分支。

MR 标题建议：

```text
fix: preserve video quality
```

MR 描述模板：

```text
## 本次改动
1. ...
2. ...

## 验证
1. ...
2. ...

## 风险
1. ...
```

提交 MR 后，让同事 review。通过后点击 GitLab 页面上的 `Merge`。

## 12. 合并后同步本地目标分支

MR 合并后，本地也要更新：

```bash
git switch test
git pull --ff-only origin test
```

确认最新提交：

```bash
git log -5 --oneline --decorate
```

确认自己的提交已经在目标分支里：

```bash
git merge-base --is-ancestor feature/your-change-name test
```

这个命令不输出内容。如果退出码是 `0`，说明工作分支已经被目标分支包含。

更直观的检查：

```bash
git branch --merged test
```

如果列表里有你的工作分支，说明它已经合进 `test`。

## 13. 删除已合并分支

删除本地工作分支：

```bash
git branch -d feature/your-change-name
```

删除远端工作分支：

```bash
git push origin --delete feature/your-change-name
```

是否删除远端分支按团队习惯来。不确定时先保留。

## 14. 不走 MR，直接推到目标分支的方式

推荐走 MR。直接推公共分支只适合团队明确允许、改动较小、你确认目标分支是最新的情况。

先确认当前分支基于最新目标分支：

```bash
git fetch origin --prune
git switch test
git pull --ff-only origin test
```

如果你在工作分支上已经提交好，可以本地合并到目标分支：

```bash
git switch test
git merge --no-ff feature/your-change-name -m "merge feature into test"
```

推送目标分支：

```bash
git push origin test
```

也可以把当前分支直接推到远端目标分支：

```bash
git push origin HEAD:test
```

执行前必须确认：

- 当前分支只包含你要推的提交。
- `git status --short --branch` 是干净的。
- 目标分支是最新的。
- 团队允许直接推目标分支。
- 没有把密码、token、本地临时文件、个人配置提交进去。

## 15. 我这次操作抽象成通用流程

这次实际采用的是“工作分支 -> 本地合并到目标分支 -> push 目标分支”的方式。抽象成通用命令如下：

```bash
git fetch origin --prune
git switch target-branch
git pull --ff-only origin target-branch
git switch -c fix/some-problem
```

修改代码并验证后：

```bash
git status --short
git diff
git add path/to/changed_file
git commit -m "fix: describe the fix"
```

合并回目标分支：

```bash
git switch target-branch
git merge --no-ff fix/some-problem -m "merge some problem fix into target branch"
```

推送：

```bash
git push origin target-branch
```

确认远端目标分支：

```bash
git ls-remote origin refs/heads/target-branch
git log -5 --oneline --decorate origin/target-branch
```

如果团队要求必须走 GitLab MR，则不要本地 merge 和直接 push 目标分支，而是：

```bash
git push -u origin fix/some-problem
```

然后去 GitLab 页面创建 MR，目标分支选择 `target-branch`。

## 16. 处理冲突

如果 pull、merge、rebase 时出现冲突，先看状态：

```bash
git status --short
```

冲突文件里会出现：

```text
<<<<<<< HEAD
当前分支内容
=======
要合入的内容
>>>>>>> other-branch
```

手动编辑文件，保留正确内容，删除冲突标记。

解决后：

```bash
git add path/to/conflict_file
```

如果是在 merge：

```bash
git merge --continue
```

如果是在 rebase：

```bash
git rebase --continue
```

如果不想继续：

```bash
git merge --abort
```

或：

```bash
git rebase --abort
```

## 17. 常见错误

### Permission denied publickey

现象：

```text
Permission denied (publickey)
```

原因通常是 SSH key 没加到 GitLab，或者 remote 用的是 SSH 地址但本机没有可用 key。

解决：

```bash
ssh -T git@gitlab.example.com
```

如果失败，重新按“方式 B：SSH”添加公钥。或者把 remote 改成 HTTPS：

```bash
git remote set-url origin https://gitlab.example.com/group/project.git
```

### Authentication failed

HTTPS 推送失败时，通常是用户名、密码或 token 不对。GitLab 开启双因素认证时，要用 Personal Access Token，不要用网页登录密码。

### non-fast-forward

现象：

```text
Updates were rejected because the remote contains work that you do not have locally.
```

说明远端分支比你本地新。

解决：

```bash
git fetch origin --prune
git pull --ff-only origin current-branch
```

如果不能 fast-forward，说明有分叉。不要强推，先确认怎么合并。

### src refspec does not match any

常见原因：

- 分支名写错。
- 当前分支还没有 commit。
- 推送命令里的分支不存在。

检查：

```bash
git branch
git status --short --branch
git log -1 --oneline
```

### 本地没有跟踪远端分支

第一次推新分支时用：

```bash
git push -u origin branch-name
```

以后再推：

```bash
git push
```

### 分支名和文件夹名冲突

如果项目里有 `test/` 文件夹，同时也有 `test` 分支，有时命令会歧义。

更明确地写远端分支：

```bash
git diff origin/test
git switch -c test origin/test
```

必要时用 `--` 分隔路径：

```bash
git diff origin/test -- test/some_file.py
```

## 18. 安全检查清单

推送或创建 MR 前，至少检查：

```bash
git status --short --branch
git diff --check
rg -n "<<<<<<<|=======|>>>>>>>" .
```

再按项目类型跑测试，例如：

```bash
npm test
pytest
python -m unittest
mvn test
go test ./...
```

确认没有提交：

- 密码
- token
- cookie
- 私钥
- `.env`
- 本地日志
- 临时文件
- 大型无关文件

查看将要提交的文件：

```bash
git status --short
```

查看提交内容：

```bash
git diff --cached
```

## 19. 内网 GitLab 网页操作版

上面的流程主要是终端 Git 命令。网页操作也可以达到同等结果：在 GitLab 远端生成 commit、创建分支、创建 MR、合并到目标分支。

网页操作适合：

- 新手不熟悉命令行。
- 只改少量文件。
- 只上传一两个文件。
- 想直接在 GitLab 页面创建 MR。

网页操作不太适合：

- 一次改很多文件。
- 需要跑本地测试。
- 需要处理复杂冲突。
- 需要上传大目录或大量二进制文件。

这种情况仍推荐用终端 Git 或 IDE。

### 19.1 先连到内网 GitLab

每家公司 GitLab 地址不同，常见形式：

```text
https://gitlab.example.com
https://git.company.local
http://git.company-internal.example
```

如果 GitLab 是内网服务，先确认自己在内网环境里：

1. 在公司网络内，或先连接公司 VPN。
2. 打开浏览器访问 GitLab 地址。
3. 能看到登录页说明网络通了。
4. 登录自己的 GitLab 账号。

如果打不开：

| 现象 | 可能原因 |
|---|---|
| 页面无法访问 | 没连 VPN / 不在内网 |
| DNS 解析失败 | 内网 DNS 没生效 |
| 证书报错 | 公司内网证书未信任 |
| 403 / 无权限 | 账号没项目权限 |
| 登录后看不到项目 | 没加入项目或 group |

网页操作前至少需要：

- 能打开 GitLab 项目页面。
- 对项目有 Developer 或更高权限，才能 push 分支。
- 对目标分支有 merge 权限，才能合并 MR。
- 如果目标分支受保护，普通成员通常不能直接改目标分支，只能提 MR。

### 19.2 在 GitLab 网页上找到项目

登录后可以从这些地方进入项目：

```text
Projects -> Your projects
Groups -> 选择 group -> 选择 project
搜索框输入项目名
直接打开项目 URL
```

项目页面通常会看到：

```text
Repository
Branches
Commits
Merge requests
Pipelines
Settings
```

如果看不到 `Repository` 或文件列表，说明权限不足。

### 19.3 网页上创建新分支

等同于终端：

```bash
git fetch origin --prune
git switch target-branch
git pull --ff-only origin target-branch
git switch -c feature/your-change-name
```

网页操作：

1. 进入项目页面。
2. 点击 `Repository` -> `Branches`。
3. 点击 `New branch`。
4. 填写新分支名，例如：
   ```text
   feature/login-page
   fix/video-quality
   docs/gitlab-guide
   ```
5. `Create from` 选择目标分支，例如：
   ```text
   test
   main
   master
   develop
   ```
6. 点击创建。

关键点：

- `Create from` 必须选对。你要最终合到哪个分支，就从哪个分支创建。
- 不要从一个很旧的分支创建，否则后面容易冲突。
- 不要直接在 `main`、`master`、`test` 上改，除非团队允许。

### 19.4 网页上编辑单个文件

等同于终端：

```bash
git switch feature/your-change-name
修改文件
git add path/to/file
git commit -m "fix: update file"
git push
```

网页操作：

1. 进入项目页面。
2. 点击 `Repository` -> `Files`。
3. 左上角分支下拉框选择你的工作分支。
4. 找到要改的文件。
5. 点击文件进入详情页。
6. 点击 `Edit`。
7. 修改内容。
8. 页面底部填写 commit message，例如：
   ```text
   fix: update video quality settings
   ```
9. 确认提交到你的工作分支，而不是目标分支。
10. 点击 `Commit changes`。

提交后 GitLab 会在远端分支上生成一个 commit。这个结果等同于你在本地 commit 后 push 到 GitLab。

### 19.5 网页上上传新文件

等同于终端：

```bash
git add new_file.md
git commit -m "docs: add guide"
git push
```

网页操作：

1. 进入项目页面。
2. 点击 `Repository` -> `Files`。
3. 分支下拉框选择你的工作分支。
4. 进入要放文件的目录。
5. 点击 `+` 或 `New file` / `Upload file`。
6. 上传文件或新建文件。
7. 填写 commit message。
8. 确认提交到工作分支。
9. 点击 `Commit changes`。

注意：

- 网页上传适合少量文件。
- 大量文件、整个目录、复杂工程改动，推荐用终端或 IDE。
- 上传前确认没有 `.env`、私钥、token、日志等敏感文件。

### 19.6 使用 GitLab Web IDE 改多个文件

Web IDE 适合一次改多个文本文件。

操作：

1. 进入项目页面。
2. 点击 `Web IDE` 或 `Open in Web IDE`。
3. 确认当前分支是你的工作分支。
4. 修改多个文件。
5. 左侧查看 changed files。
6. 填写 commit message。
7. 提交到当前工作分支。

如果 GitLab 提示要创建新分支，按提示创建一个工作分支，不要直接提交到受保护目标分支。

Web IDE 的结果也是远端生成 commit，等同于本地 commit + push。

### 19.7 网页上创建 Merge Request

等同于终端里已经 `git push -u origin feature/your-change-name` 后，在 GitLab 上发起合并请求。

操作：

1. 进入项目页面。
2. 点击 `Merge requests`。
3. 点击 `New merge request`。
4. 选择：
   ```text
   Source branch: 你的工作分支
   Target branch: 要合入的目标分支
   ```
5. 点击 `Compare branches and continue`。
6. 填写标题，例如：
   ```text
   fix: preserve video quality
   ```
7. 填写描述：
   ```text
   ## 本次改动
   1. ...
   2. ...

   ## 验证
   1. ...
   2. ...

   ## 风险
   1. ...
   ```
8. 选择 reviewer / assignee。
9. 点击 `Create merge request`。

创建 MR 后，GitLab 通常会显示：

- 改了哪些文件。
- commit 列表。
- 是否有冲突。
- pipeline 是否通过。
- 是否可以 merge。

### 19.8 网页上合并 MR

等同于终端：

```bash
git switch target-branch
git merge feature/your-change-name
git push origin target-branch
```

网页操作：

1. 打开 MR 页面。
2. 确认 `Source branch` 和 `Target branch` 没选错。
3. 查看 changed files。
4. 确认 reviewer 已同意。
5. 确认 pipeline 通过。
6. 如果页面显示 `Merge` 按钮可用，点击 `Merge`。

合并后，工作分支的 commit 会进入目标分支。

如果页面提示冲突：

- 简单冲突可以用 GitLab 页面提示解决。
- 复杂冲突建议拉到本地用终端或 IDE 解决。

### 19.9 网页上确认是否合并成功

方法 1：看 MR 状态。

```text
Merge requests -> 找到你的 MR -> 状态应为 Merged
```

方法 2：看目标分支提交记录。

```text
Repository -> Commits -> 分支选择 target branch
```

确认能看到你的 commit 或 merge commit。

方法 3：看目标分支文件内容。

```text
Repository -> Files -> 分支选择 target branch -> 打开文件
```

确认文件内容已经变成新版本。

方法 4：看 Branches。

```text
Repository -> Branches -> 搜索 target branch
```

确认目标分支最新 commit 时间和提交信息。

### 19.10 网页操作和终端操作的对应关系

| 目标 | 终端命令 | GitLab 网页操作 |
|---|---|---|
| 连接 GitLab | `git clone <url>` | 浏览器打开 GitLab 项目页面 |
| 查看分支 | `git branch -a` | Repository -> Branches |
| 创建分支 | `git switch -c feature/x origin/test` | Branches -> New branch |
| 修改文件 | 本地编辑器改文件 | Repository -> Files -> Edit |
| 新增文件 | `git add new_file` | Repository -> Files -> New file / Upload file |
| 提交 | `git commit -m "..."` | 页面底部填写 commit message -> Commit changes |
| 上传分支 | `git push -u origin feature/x` | 网页提交时 commit 已经直接在远端分支上 |
| 创建 MR | GitLab 页面操作 | Merge requests -> New merge request |
| 合并 | `git merge` + `git push` | MR 页面点击 Merge |
| 验证远端结果 | `git log origin/test` | Repository -> Commits / Files |

### 19.11 网页操作的安全检查

网页 commit 前检查：

- 当前分支是不是自己的工作分支。
- 目标分支是不是团队要求的分支。
- 文件内容没有密码、token、cookie、私钥。
- 没有上传无关大文件。
- commit message 清楚说明改动。

创建 MR 前检查：

- Source branch 是你的工作分支。
- Target branch 是目标分支。
- Changed files 里没有无关文件。
- 描述里写清楚验证结果。

点击 Merge 前检查：

- reviewer 已同意。
- pipeline 通过。
- 没有冲突。
- MR 目标分支正确。

## 20. 最常用命令速查

```bash
git clone https://gitlab.example.com/group/project.git
git remote -v
git fetch origin --prune
git switch target-branch
git pull --ff-only origin target-branch
git switch -c feature/my-change
git status --short --branch
git diff
git add path/to/file
git commit -m "fix: my change"
git push -u origin feature/my-change
git switch target-branch
git pull --ff-only origin target-branch
git merge --no-ff feature/my-change -m "merge my change into target"
git push origin target-branch
git branch -d feature/my-change
```

如果团队使用 MR，把最后的本地 merge 和 `git push origin target-branch` 换成：

```bash
git push -u origin feature/my-change
```

然后去 GitLab 页面创建 Merge Request。
