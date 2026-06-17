# ai-kuaixun

A Codex skill that fetches AI briefs from PostgreSQL over SSH, classifies them into `模型` / `Agent` / `多模态` / `落地` / `风险`, and writes a Markdown candidate pool note to Obsidian.

## What this repo contains

- `SKILL.md`: skill instructions for Codex
- `agents/openai.yaml`: skill UI metadata
- `scripts/fetch_ai_kuaixun.py`: fetch + classify + render script
- `install.sh`: installs this skill into `~/.codex/skills/ai-kuaixun`
- `.env.example`: runtime configuration template

## Quick start

```bash
git clone https://github.com/yugulugulu/ai-kuaixun.git
cd ai-kuaixun
./install.sh
```

Then fill in `~/.codex/skills/ai-kuaixun/.env`:

```bash
AI_KUAIXUN_SSH_HOST=your-server-host
AI_KUAIXUN_SSH_USER=root
AI_KUAIXUN_SSH_PASSWORD=your-password
AI_KUAIXUN_DB_NAME=ai_news
AI_KUAIXUN_TABLE=public.ai_briefs
AI_KUAIXUN_OBSIDIAN_DIR=~/obsidian workspace/AI日报/候选池
```

Run the script:

```bash
python3 ~/.codex/skills/ai-kuaixun/scripts/fetch_ai_kuaixun.py
```

Override the time window if needed:

```bash
python3 ~/.codex/skills/ai-kuaixun/scripts/fetch_ai_kuaixun.py \
  --start '2026-04-23 00:00:00+08' \
  --end '2026-04-24 00:00:00+08'
```

## Notes

- The script requires either `AI_KUAIXUN_SSH_PASSWORD` or `AI_KUAIXUN_SSH_KEY_PATH`.
- The target PostgreSQL instance must be reachable from the SSH host via local `sudo -u postgres psql`.
- `.env` is intentionally gitignored.
