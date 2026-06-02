---
tags: [gitlab, git, git-bash, guide, beginner]
updated: 2026-06-02
---

# GitLab 新手 Git Bash 版本指南

这份文档按 Windows 上的 **Git Bash** 来写。Git Bash 是安装 Git for Windows 后自带的 Bash 终端，命令风格接近 Linux/macOS。

如果你用的是 PowerShell，也可以看另一篇：

```text
GitLab新手连接上传分支合并指南.md
```

## 0. Git Bash 路径写法

Windows 路径：

```text
C:\Users\yourname\Desktop\project
```

在 Git Bash 里写成：

```bash
/c/Users/yourname/Desktop/project
```

常见转换：

| Windows 路径 | Git Bash 路径 |
|---|---|
| `C:\Users\admin\Desktop` | `/c/Users/admin/Desktop` |
| `D:\code\project` | `/d/code/project` |
| `E:\work\repo` | `/e/work/repo` |

进入目录：

```bash
cd /c/Users/yourname/Desktop/project
```

查看当前目录：

```bash
pwd
```

查看文件：

```bash
ls
ls -la
```

## 1. 第一次使用 Git Bash 的配置

配置提交人：

```bash
git config --global user.name "Your Name"
git config --global user.email "your-email@example.com"
```

查看配置：

```bash
git config --global --list
```

建议邮箱用 GitLab 账号邮箱。

## 2. 用 Git Bash 连接 GitLab：HTTPS 方式

HTTPS 仓库地址示例：

```text
https://gitlab.example.com/group/project.git
```

克隆：

```bash
git clone https://gitlab.example.com/group/project.git
cd project
```

查看远端：

```bash
git remote -v
```

如果推送时要求密码，GitLab 可能需要 Personal Access Token，而不是网页登录密码。

token 通常在 GitLab 页面创建：

```text
头像 -> Preferences / Edit profile -> Access Tokens
```

常用权限：

```text
read_repository
write_repository
```

不要把 token 写进代码、文档、截图或聊天记录。

## 3. 用 Git Bash 连接 GitLab：SSH 方式

SSH 仓库地址示例：

```text
git@gitlab.example.com:group/project.git
```

### 3.1 生成 SSH key

```bash
ssh-keygen -t ed25519 -C "your-email@example.com"
```

一路回车后会生成：

```text
~/.ssh/id_ed25519
~/.ssh/id_ed25519.pub
```

查看 SSH 文件：

```bash
ls -la ~/.ssh
```

查看公钥：

```bash
cat ~/.ssh/id_ed25519.pub
```

在 Git Bash 里复制公钥到 Windows 剪贴板：

```bash
clip < ~/.ssh/id_ed25519.pub
```

然后打开 GitLab：

```text
头像 -> Preferences / SSH Keys -> Add new key
```

粘贴公钥并保存。

### 3.2 测试 SSH 连接

把域名替换成自己的 GitLab 域名：

```bash
ssh -T git@gitlab.example.com
```

成功时通常会看到类似欢迎信息。

如果失败：

```text
Permission denied (publickey)
```

常见原因：

- 公钥没有加到 GitLab。
- remote 地址不是 SSH 地址。
- 用错 GitLab 域名。
- 当前账号没有项目权限。

### 3.3 用 SSH clone

```bash
git clone git@gitlab.example.com:group/project.git
cd project
```

## 4. 已有本地项目时配置 GitLab remote

进入项目目录：

```bash
cd /c/Users/yourname/Desktop/project
```

查看是否已有远端：

```bash
git remote -v
```

如果没有远端：

```bash
git remote add origin https://gitlab.example.com/group/project.git
```

SSH 方式：

```bash
git remote add origin git@gitlab.example.com:group/project.git
```

如果远端地址错了：

```bash
git remote set-url origin https://gitlab.example.com/group/project.git
```

或：

```bash
git remote set-url origin git@gitlab.example.com:group/project.git
```

## 5. Git Bash 标准分支上传和 MR 流程

下面以目标分支 `test` 为例。如果你的团队使用 `main`、`master`、`develop`，把 `test` 替换成对应分支名。

### 5.1 拉取远端最新信息

```bash
git fetch origin --prune
```

切到目标分支：

```bash
git switch test
```

如果本地没有 `test`：

```bash
git switch -c test origin/test
```

更新本地目标分支：

```bash
git pull --ff-only origin test
```

### 5.2 创建工作分支

```bash
git switch -c fix/your-change-name
```

分支名建议：

```text
feature/login-page
fix/video-quality
docs/gitlab-guide
chore/update-config
```

不要用空格和中文分支名。

### 5.3 修改文件后检查状态

查看当前分支和文件状态：

```bash
git status -sb
```

查看改动：

```bash
git diff
```

只看某个文件：

```bash
git diff path/to/file.py
```

检查空白问题：

```bash
git diff --check
```

检查冲突标记：

```bash
grep -R -n -E "<<<<<<<|=======|>>>>>>>" .
```

### 5.4 暂存文件

推荐按文件暂存：

```bash
git add path/to/file1.py
git add path/to/file2.py
```

确认暂存：

```bash
git status -sb
```

查看已暂存内容：

```bash
git diff --cached
```

取消暂存：

```bash
git restore --staged path/to/file.py
```

放弃某个文件的本地修改：

```bash
git restore path/to/file.py
```

注意：`git restore path/to/file.py` 会丢掉未提交修改。

### 5.5 提交 commit

```bash
git commit -m "fix: describe your change"
```

查看最新提交：

```bash
git log -1 --oneline
```

### 5.6 推送工作分支到 GitLab

第一次推送：

```bash
git push -u origin fix/your-change-name
```

之后同一个分支继续推送：

```bash
git push
```

推送成功后，GitLab 通常会给一个创建 MR 的链接。

## 6. 在 GitLab 页面创建 MR

1. 打开 GitLab 项目页面。
2. 进入 `Merge requests`。
3. 点击 `New merge request`。
4. 选择：
   ```text
   Source branch: fix/your-change-name
   Target branch: test
   ```
5. 点击 compare。
6. 填写标题和描述。
7. 提交 MR。
8. 等 review 和 pipeline。
9. 点击 `Merge`。

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

## 7. MR 合并后在 Git Bash 同步本地

```bash
git switch test
git pull --ff-only origin test
```

确认最近提交：

```bash
git log -5 --oneline --decorate
```

确认工作分支已合并：

```bash
git branch --merged test
```

删除本地工作分支：

```bash
git branch -d fix/your-change-name
```

删除远端工作分支：

```bash
git push origin --delete fix/your-change-name
```

远端分支是否删除按团队习惯来。

## 8. Git Bash 直接合并到目标分支的流程

推荐走 MR。只有团队明确允许直接推目标分支时，才这样做。

假设你已经在工作分支提交好了：

```bash
git status -sb
```

确认干净后：

```bash
git switch test
git pull --ff-only origin test
git merge --no-ff fix/your-change-name -m "merge fix into test"
git push origin test
```

这等同于：

```text
把工作分支合并到 test，并把 test 推到 GitLab。
```

如果你当前就在工作分支，并且想直接推到远端 `test`：

```bash
git push origin HEAD:test
```

执行前必须确认：

- 团队允许直接推 `test`。
- 当前分支基于最新 `origin/test`。
- 当前分支只包含要推的提交。
- 没有秘密、临时文件、无关文件。

## 9. Git Bash 里确认远端是否已经合并

更新远端信息：

```bash
git fetch origin --prune
```

查看远端目标分支最新提交：

```bash
git log -5 --oneline --decorate origin/test
```

直接查询 GitLab 远端分支指向：

```bash
git ls-remote origin refs/heads/test
```

确认某个 commit 是否已经在远端 `test` 里：

```bash
git merge-base --is-ancestor COMMIT_HASH origin/test
echo $?
```

输出：

```text
0
```

表示已包含。

输出：

```text
1
```

表示未包含。

示例：

```bash
git merge-base --is-ancestor abc1234 origin/test
if [ $? -eq 0 ]; then
  echo "already merged"
else
  echo "not merged"
fi
```

## 10. Git Bash 冲突处理

如果 merge 或 pull 出现冲突：

```bash
git status -sb
```

打开冲突文件，会看到：

```text
<<<<<<< HEAD
当前分支内容
=======
要合入的内容
>>>>>>> other-branch
```

手动改成正确内容，删除这些标记。

然后：

```bash
git add path/to/conflict_file
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

## 11. Git Bash 常见问题

### 11.1 路径找不到

Windows 路径不能直接写成：

```bash
cd C:\Users\yourname\Desktop\project
```

Git Bash 应写成：

```bash
cd /c/Users/yourname/Desktop/project
```

如果路径里有空格，用引号：

```bash
cd "/c/Users/yourname/Desktop/My Project"
```

### 11.2 Permission denied publickey

先测试：

```bash
ssh -T git@gitlab.example.com
```

如果失败，重新复制公钥：

```bash
clip < ~/.ssh/id_ed25519.pub
```

然后到 GitLab 添加 SSH key。

### 11.3 Authentication failed

HTTPS 推送失败时，多数是密码或 token 问题。GitLab 开启双因素认证时，要用 Personal Access Token。

### 11.4 non-fast-forward

说明远端比本地新：

```bash
git fetch origin --prune
git pull --ff-only origin test
```

不要随便 `git push --force`。

### 11.5 当前有未提交修改，不能切分支

看状态：

```bash
git status -sb
```

选择一：

提交掉：

```bash
git add path/to/file
git commit -m "fix: save current work"
```

临时保存：

```bash
git stash push -m "work in progress"
```

恢复：

```bash
git stash pop
```

放弃修改：

```bash
git restore path/to/file
```

## 12. Git Bash 操作前后检查清单

开始前：

```bash
git remote -v
git status -sb
git fetch origin --prune
```

提交前：

```bash
git status -sb
git diff
git diff --check
grep -R -n -E "<<<<<<<|=======|>>>>>>>" .
```

提交后：

```bash
git log -1 --oneline
```

推送后：

```bash
git log -5 --oneline --decorate origin/test
git ls-remote origin refs/heads/test
```

安全检查：

- 不提交密码。
- 不提交 token。
- 不提交 `.env`。
- 不提交私钥。
- 不提交 cookie。
- 不提交无关日志。
- 不提交大文件，除非项目要求。

## 13. Git Bash 最短可复制流程

把 `test`、`fix/my-change`、commit message 替换成自己的。

```bash
git fetch origin --prune
git switch test
git pull --ff-only origin test
git switch -c fix/my-change
git status -sb
git diff
git add path/to/file
git commit -m "fix: my change"
git push -u origin fix/my-change
```

然后去 GitLab 网页创建 MR：

```text
Source branch: fix/my-change
Target branch: test
```

如果团队允许直接命令行合并：

```bash
git switch test
git pull --ff-only origin test
git merge --no-ff fix/my-change -m "merge my change into test"
git push origin test
```
