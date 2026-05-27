---
date: 2026-05-27
tags: [changelog]
---

# h20 新仓库部署 + git 工作流

## 改动类型

- [x] 新功能
- [ ] Bug 修复
- [ ] 重构
- [x] 配置变更

## 改动内容

1. 在 h20（hgx19）上部署新仓库 `git.joyingai.cn/services/crm.ai.joyingbot`
   - 部署路径：`/data/projects/joyingbot-new/`
   - Python 环境：conda `joyingbot`（Python 3.10.13）
   - 启动方式：`conda activate joyingbot && python api_server/main.py --port 8100`

2. 将 VoxCPM API 服务（`api_server/main.py`）合并进项目仓库
   - 从 `/root/api_server/main.py`（原"野代码"）复制到 `api_server/main.py`
   - 作为独立 FastAPI 服务运行（非 Flask Blueprint，因为 VoxCPM 模型加载需要 async）

3. 修复 `requirements.txt`
   - 移除 `pywin32==306`、`pypiwin32==223`（Windows 专属，Linux 无法安装）
   - `dashscope` 版本：`1.20.4` → `>=1.25.0`（新版支持 `qwen_tts_realtime`）
   - 新增：`fastapi`、`librosa`、`soundfile`、`uvicorn`、`voxcpm`

4. torch/torchaudio 降级适配 CUDA 12.4
   ```bash
   pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cu124
   pip install torchaudio==2.5.1 --index-url https://download.pytorch.org/whl/cu124
   ```

## Git 工作流

### 仓库信息
- 仓库：`git.joyingai.cn/services/crm.ai.joyingbot`
- 分支规范：`master`（主干）→ `test`（测试）→ `feature/ai_vX_功能`（开发）
- 流程：个人分支 → 合并到 test → 验证通过 → 提 MR 到 master

### 本次操作步骤

```bash
# 1. 本地 clone
git clone https://git.joyingai.cn/services/crm.ai.joyingbot.git

# 2. 切换到 test 分支
git checkout test

# 3. 从 test 创建开发分支
git checkout -b feature/ai_v1_api_merge

# 4. 修改代码...

# 5. 配置 git 用户信息（首次需要）
git config user.email "wuwenjie@joyingai.cn"
git config user.name "伍文杰"

# 6. 提交
git add api_server/ requirements.txt
git commit -m "feat: 添加 VoxCPM API 服务"

# 7. 推送
git push origin feature/ai_v1_api_merge
```

### h20 网络限制

h20 无法直连 `git.joyingai.cn`（DNS 解析为 NXDOMAIN），需要用跳板中转：
- **代码上传**：本地 Windows → SCP → 222.71.55.27 → SCP → h20
- **代码推送**：在本地 Windows clone + push（不在 h20 上 push）
- **后续优化**：找程伟/晋良要 `git.joyingai.cn` 内网 IP，加到 h20 `/etc/hosts`

## 影响范围

- 新仓库 `joyingbot` 已在 h20 测试服务器部署就绪
- VoxCPM API 代码已纳入版本控制，不再以"野代码"形式存在
- `requirements.txt` 修复后适配 Linux 环境

## 相关 Commit

- `feature/ai_v1_api_merge` 分支，已推送到 git.joyingai.cn
