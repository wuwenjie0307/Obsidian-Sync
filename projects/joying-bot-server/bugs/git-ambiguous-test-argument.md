---
date: 2026-05-27
status: fixed
severity: low
tags: [bug, git]
---

# git ambiguous argument 'test' — 分支名与目录名冲突

## 问题描述

h20 上执行 `git format-patch test` 或引用 `test` 分支时报错：

```bash
$ git format-patch test --stdout
fatal: ambiguous argument 'test': both revision and filename
Use '--' to separate paths from revisions
```

## 原因

项目根目录下有一个名为 `test` 的文件夹，Git 无法区分用户引用的是 `test` 分支还是 `test` 目录。

## 解决方案

使用完整引用区分分支：

```bash
# 错误
git diff test

# 正确
git diff origin/test
git format-patch origin/test --stdout
```

或者使用 `--` 分隔符：

```bash
git format-patch test -- --stdout
```

## 相关文件

- `test/` 目录（项目中存在）
