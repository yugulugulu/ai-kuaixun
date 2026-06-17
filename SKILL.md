---
name: ai-kuaixun
description: Fetch AI briefs from the user's PostgreSQL-backed `ai_news.public.ai_briefs` dataset via SSH on the source server, classify the results into `模型`、`Agent`、`多模态`、`落地`、`风险`, and write a title-and-summary Markdown note into Obsidian. Use when the user asks to pull database AI briefs, build a daily brief candidate pool, sync AI brief titles/summaries to Obsidian, or generate the default rolling window from yesterday 10:00 to today 10:00 in Asia/Shanghai.
---

# AI快讯

## Overview

Use `scripts/fetch_ai_kuaixun.py` to fetch records from `ai_news.public.ai_briefs`, classify them into five buckets, and write a Markdown note to Obsidian.

Default behavior:

- Query window: previous day `10:00` to current day `10:00` in `Asia/Shanghai`
- Source table: `public.ai_briefs`
- Time field: `created_at`
- Note content: `标题 + 摘要` only
- Output path: `$AI_KUAIXUN_OBSIDIAN_DIR/YYYY-MM-DD AI快讯候选池.md`

## Workflow

1. Run the script without arguments for the default rolling window:

```bash
python3 ~/.codex/skills/ai-kuaixun/scripts/fetch_ai_kuaixun.py
```

2. Override the window when the user specifies dates:

```bash
python3 ~/.codex/skills/ai-kuaixun/scripts/fetch_ai_kuaixun.py \
  --start '2026-04-23 00:00:00+08' \
  --end '2026-04-24 00:00:00+08'
```

3. Override the destination note when needed:

```bash
python3 ~/.codex/skills/ai-kuaixun/scripts/fetch_ai_kuaixun.py \
  --note-path '~/obsidian workspace/AI日报/候选池/自定义笔记.md'
```

## Behavior Rules

- Prefer `title_zh` and `summary_zh`; fall back to `title` and `summary`.
- Classify by `标题 + 摘要`, not by `body`.
- Keep only items that hit at least one of the five categories.
- Write one primary category per item.
- Output each item with:
  - `序号`
  - `ID`
  - `标题`
  - `来源`
  - `发布时间`
  - `入库时间`
  - `命中标签`
  - `链接`
  - `摘要`

## Environment Setup

- Copy `.env.example` to `.env` in the skill root, or export equivalent environment variables before running.
- Required:
  - `AI_KUAIXUN_SSH_HOST`
  - `AI_KUAIXUN_SSH_USER`
  - `AI_KUAIXUN_SSH_PASSWORD` or `AI_KUAIXUN_SSH_KEY_PATH`
- Optional:
  - `AI_KUAIXUN_DB_NAME` default: `ai_news`
  - `AI_KUAIXUN_TABLE` default: `public.ai_briefs`
  - `AI_KUAIXUN_OBSIDIAN_DIR` default: `~/obsidian workspace/AI日报/候选池`
- PostgreSQL is only reachable locally on the server, so the script must SSH first and then run `sudo -u postgres psql`.

## Validation

- After updating the skill, run:

```bash
python3 ~/.codex/skills/.system/skill-creator/scripts/quick_validate.py ~/.codex/skills/ai-kuaixun
```

- Forward-test by executing the script and checking that the target note is created and grouped into the five sections.
