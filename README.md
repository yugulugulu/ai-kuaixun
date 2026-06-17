# ai-kuaixun

这是一个 Codex Skill，用于通过 SSH 从 PostgreSQL 中抓取 AI 快讯，将内容归类到 `模型` / `Agent` / `多模态` / `落地` / `风险` 五个栏目，并把候选池写入 Obsidian Markdown 笔记。

## 仓库内容

- `SKILL.md`：Codex 读取的 Skill 说明
- `agents/openai.yaml`：Skill 的界面元信息
- `scripts/fetch_ai_kuaixun.py`：抓取、分类、渲染笔记的主脚本
- `install.sh`：把 Skill 安装到 `~/.codex/skills/ai-kuaixun`
- `.env.example`：运行时配置模板

## 快速开始

```bash
git clone https://github.com/yugulugulu/ai-kuaixun.git
cd ai-kuaixun
./install.sh
```

然后填写 `~/.codex/skills/ai-kuaixun/.env`：

```bash
AI_KUAIXUN_SSH_HOST=your-server-host
AI_KUAIXUN_SSH_USER=root
AI_KUAIXUN_SSH_PASSWORD=your-password
AI_KUAIXUN_DB_NAME=ai_news
AI_KUAIXUN_TABLE=public.ai_briefs
AI_KUAIXUN_OBSIDIAN_DIR=~/obsidian workspace/AI日报/候选池
```

执行脚本：

```bash
python3 ~/.codex/skills/ai-kuaixun/scripts/fetch_ai_kuaixun.py
```

如果需要自定义时间窗口：

```bash
python3 ~/.codex/skills/ai-kuaixun/scripts/fetch_ai_kuaixun.py \
  --start '2026-04-23 00:00:00+08' \
  --end '2026-04-24 00:00:00+08'
```

## 说明

- 脚本要求至少提供 `AI_KUAIXUN_SSH_PASSWORD` 或 `AI_KUAIXUN_SSH_KEY_PATH` 其中之一。
- 目标 PostgreSQL 必须能在 SSH 服务器本机通过 `sudo -u postgres psql` 访问。
- `.env` 已加入 `.gitignore`，不会被提交到仓库。
