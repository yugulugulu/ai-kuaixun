#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import shlex
import time as time_module
import warnings
from dataclasses import dataclass
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import paramiko
import urllib3
warnings.filterwarnings("ignore", category=urllib3.exceptions.NotOpenSSLWarning)
import requests


TZ = ZoneInfo("Asia/Shanghai")
SECTIONS = ["模型", "Agent", "多模态", "落地", "风险"]


PATTERNS = {
    "模型": [
        r"\bLLM\b",
        r"\bVLM\b",
        r"\bMoE\b",
        r"\bSOTA\b",
        r"模型",
        r"开源",
        r"推理",
        r"上下文",
        r"蒸馏",
        r"训练",
        r"后训练",
        r"reasoning",
        r"benchmark",
        r"Claude",
        r"GPT",
        r"Gemini",
        r"Qwen",
        r"DeepSeek",
        r"Kimi",
        r"GLM",
        r"通义",
        r"豆包",
        r"智谱",
        r"Gemma",
    ],
    "Agent": [
        r"\bAgent\b",
        r"智能体",
        r"\bMCP\b",
        r"浏览器",
        r"\bCLI\b",
        r"Codex",
        r"Claude Code",
        r"Copilot Agent",
        r"workspace agent",
        r"工作区代理",
        r"agentic",
        r"工具调用",
        r"多智能体",
        r"技能库",
        r"技能",
        r"自动执行",
    ],
    "多模态": [
        r"多模态",
        r"视频",
        r"图像",
        r"图片",
        r"音频",
        r"语音",
        r"音乐",
        r"3D",
        r"世界模型",
        r"数字人",
        r"\bimage\b",
        r"\bimages\b",
        r"\bvideo\b",
        r"\baudio\b",
        r"\bvoice\b",
        r"Vision",
        r"Seed3D",
    ],
    "落地": [
        r"合作",
        r"接入",
        r"部署",
        r"上线",
        r"企业",
        r"客户",
        r"解决方案",
        r"工作场所",
        r"零售",
        r"金融",
        r"医疗",
        r"汽车",
        r"制造",
        r"政府",
        r"Gemini Enterprise",
        r"Google Cloud",
        r"ServiceNow",
        r"NEC",
        r"采用",
        r"partnership",
        r"deploy",
    ],
    "风险": [
        r"风险",
        r"安全",
        r"漏洞",
        r"攻击",
        r"入侵",
        r"刑事调查",
        r"监管",
        r"版权",
        r"争议",
        r"下架",
        r"封禁",
        r"备案",
        r"滥用",
        r"隐私",
        r"safety",
        r"security",
        r"vulnerability",
        r"privacy",
    ],
}
COMPILED_PATTERNS = {
    category: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    for category, patterns in PATTERNS.items()
}
PRIORITY = ["风险", "Agent", "多模态", "模型", "落地"]
TRANSLATE_ENDPOINT = "https://translate.googleapis.com/translate_a/single"
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
ENV_FILE_CANDIDATES = [
    Path.cwd() / ".env",
    Path(__file__).resolve().parents[1] / ".env",
]


@dataclass
class Brief:
    id: str
    source: str
    title: str
    summary: str
    url: str
    published_at_local: str
    created_at_local: str
    category: str
    matched_categories: str


@dataclass
class Config:
    ssh_host: str
    ssh_user: str
    ssh_password: str | None
    ssh_key_path: str | None
    db_name: str
    table: str
    obsidian_dir: Path


def load_env_file() -> None:
    for env_path in ENV_FILE_CANDIDATES:
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'").strip('"'))
        return


def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def load_config() -> Config:
    load_env_file()
    ssh_password = os.getenv("AI_KUAIXUN_SSH_PASSWORD", "").strip() or None
    ssh_key_path = os.getenv("AI_KUAIXUN_SSH_KEY_PATH", "").strip() or None
    if not ssh_password and not ssh_key_path:
        raise SystemExit(
            "Set AI_KUAIXUN_SSH_PASSWORD or AI_KUAIXUN_SSH_KEY_PATH before running this script."
        )
    return Config(
        ssh_host=get_required_env("AI_KUAIXUN_SSH_HOST"),
        ssh_user=get_required_env("AI_KUAIXUN_SSH_USER"),
        ssh_password=ssh_password,
        ssh_key_path=ssh_key_path,
        db_name=os.getenv("AI_KUAIXUN_DB_NAME", "ai_news").strip() or "ai_news",
        table=os.getenv("AI_KUAIXUN_TABLE", "public.ai_briefs").strip() or "public.ai_briefs",
        obsidian_dir=Path(
            os.getenv(
                "AI_KUAIXUN_OBSIDIAN_DIR",
                str(Path.home() / "obsidian workspace" / "AI日报" / "候选池"),
            )
        ).expanduser(),
    )


class Translator:
    def __init__(self) -> None:
        self._cache: dict[str, str] = {}

    def to_zh(self, text: str) -> str:
        text = text.strip()
        if not text or CJK_RE.search(text):
            return text
        cached = self._cache.get(text)
        if cached is not None:
            return cached
        chunks = self._chunk_text(text)
        translated_chunks = [self._translate_chunk(chunk) for chunk in chunks]
        result = "".join(translated_chunks).strip() or text
        self._cache[text] = result
        return result

    def _chunk_text(self, text: str, max_chars: int = 800) -> list[str]:
        if len(text) <= max_chars:
            return [text]
        parts = re.split(r"(?<=[.!?;:])\s+|\n+", text)
        chunks: list[str] = []
        current = ""
        for part in parts:
            part = part.strip()
            if not part:
                continue
            candidate = f"{current} {part}".strip() if current else part
            if len(candidate) <= max_chars:
                current = candidate
                continue
            if current:
                chunks.append(current)
            if len(part) <= max_chars:
                current = part
                continue
            start = 0
            while start < len(part):
                chunks.append(part[start : start + max_chars])
                start += max_chars
            current = ""
        if current:
            chunks.append(current)
        return chunks or [text]

    def _translate_chunk(self, text: str) -> str:
        payload = None
        for attempt in range(3):
            try:
                response = requests.get(
                    TRANSLATE_ENDPOINT,
                    params={
                        "client": "gtx",
                        "sl": "auto",
                        "tl": "zh-CN",
                        "dt": "t",
                        "q": text,
                    },
                    headers={
                        "User-Agent": "Mozilla/5.0",
                        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    },
                    timeout=15,
                )
                response.raise_for_status()
                payload = response.json()
                break
            except (requests.RequestException, ValueError):
                if attempt == 2:
                    break
                time_module.sleep(1 + attempt)
        if payload is None:
            return text
        translated = "".join(
            segment[0]
            for segment in (payload[0] or [])
            if isinstance(segment, list) and segment and segment[0]
        ).strip()
        return translated or text


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch AI briefs from PostgreSQL over SSH, classify them, and write an Obsidian note."
    )
    parser.add_argument("--start", help="Inclusive start timestamp, e.g. 2026-04-23 10:00:00+08")
    parser.add_argument("--end", help="Exclusive end timestamp, e.g. 2026-04-24 10:00:00+08")
    parser.add_argument("--note-path", help="Override the output Markdown file path.")
    return parser.parse_args()


def default_window() -> tuple[datetime, datetime]:
    now = datetime.now(TZ)
    today_10 = datetime.combine(now.date(), time(10, 0), TZ)
    end = today_10
    start = end - timedelta(days=1)
    return start, end


def parse_window(args: argparse.Namespace) -> tuple[datetime, datetime]:
    if args.start and args.end:
        return datetime.fromisoformat(args.start), datetime.fromisoformat(args.end)
    if args.start or args.end:
        raise SystemExit("Both --start and --end are required together.")
    return default_window()


def shell_quote_single(text: str) -> str:
    return text.replace("'", "''")


def build_query(config: Config, start: datetime, end: datetime) -> str:
    start_s = shell_quote_single(start.isoformat(sep=" "))
    end_s = shell_quote_single(end.isoformat(sep=" "))
    return f"""
COPY (
  SELECT id,
         source,
         COALESCE(NULLIF(title_zh,''), title) AS title,
         COALESCE(NULLIF(summary_zh,''), summary) AS summary,
         url,
         published_at AT TIME ZONE 'Asia/Shanghai' AS published_at_local,
         created_at AT TIME ZONE 'Asia/Shanghai' AS created_at_local
  FROM {config.table}
  WHERE created_at >= '{start_s}'
    AND created_at < '{end_s}'
  ORDER BY created_at ASC
) TO STDOUT WITH CSV HEADER
""".strip()


def fetch_rows(config: Config, start: datetime, end: datetime) -> list[dict[str, str]]:
    query = build_query(config, start, end)
    escaped_query = query.replace('"', '\\"').replace("\n", " ")
    command = (
        f"sudo -u postgres psql -d {shlex.quote(config.db_name)} -c \"{escaped_query}\""
    )
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kwargs = {
        "hostname": config.ssh_host,
        "username": config.ssh_user,
        "timeout": 8,
        "banner_timeout": 8,
        "auth_timeout": 8,
        "look_for_keys": bool(config.ssh_key_path),
        "allow_agent": False,
    }
    if config.ssh_key_path:
        connect_kwargs["key_filename"] = config.ssh_key_path
    else:
        connect_kwargs["password"] = config.ssh_password
        connect_kwargs["look_for_keys"] = False
    client.connect(**connect_kwargs)
    try:
        _, stdout, stderr = client.exec_command(command, timeout=120)
        out = stdout.read().decode("utf-8", "replace")
        err = stderr.read().decode("utf-8", "replace")
    finally:
        client.close()
    significant_err = "\n".join(
        line for line in err.splitlines() if "could not change directory" not in line
    ).strip()
    if significant_err:
        raise SystemExit(significant_err)
    return list(csv.DictReader(io.StringIO(out)))


def classify_rows(rows: list[dict[str, str]], translator: Translator) -> dict[str, list[Brief]]:
    by_category: dict[str, list[Brief]] = {section: [] for section in SECTIONS}
    for row in rows:
        raw_title = (row.get("title") or "").strip().replace("\n", " ")
        raw_summary = (row.get("summary") or "").strip().replace("\r", " ").replace("\n", " ")
        text = f"{raw_title} {raw_summary}"
        hits = [
            category
            for category, patterns in COMPILED_PATTERNS.items()
            if any(pattern.search(text) for pattern in patterns)
        ]
        if not hits:
            continue
        category = next((item for item in PRIORITY if item in hits), hits[0])
        if category in {"模型", "Agent"} and any(
            word.lower() in text.lower()
            for word in ["合作", "接入", "部署", "企业", "客户", "solution", "partnership", "deploy"]
        ):
            category = "落地"
        title = translator.to_zh(raw_title)
        summary = translator.to_zh(raw_summary)
        brief = Brief(
            id=str(row["id"]),
            source=row["source"],
            title=title,
            summary=summary,
            url=(row.get("url") or "").strip(),
            published_at_local=(row.get("published_at_local") or "").strip(),
            created_at_local=(row.get("created_at_local") or "").strip(),
            category=category,
            matched_categories="、".join(hits),
        )
        by_category[category].append(brief)
    return by_category


def resolve_note_path(config: Config, args: argparse.Namespace, end: datetime) -> Path:
    if args.note_path:
        return Path(args.note_path).expanduser()
    return config.obsidian_dir / f"{end.astimezone(TZ).date()} AI快讯候选池.md"


def render_note(
    note_path: Path,
    start: datetime,
    end: datetime,
    rows: list[dict[str, str]],
    by_category: dict[str, list[Brief]],
) -> None:
    note_path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append(f"# {end.astimezone(TZ).date()} AI快讯候选池")
    lines.append("")
    lines.append("- 数据来源：`ai_news.public.ai_briefs`")
    lines.append(
        f"- 取数口径：`created_at >= {start.astimezone(TZ).strftime('%Y-%m-%d %H:%M:%S%z')}` 且 `< {end.astimezone(TZ).strftime('%Y-%m-%d %H:%M:%S%z')}`"
    )
    lines.append(f"- 原始快讯数：`{len(rows)}`")
    counts = " / ".join(f"`{section} {len(by_category[section])}`" for section in SECTIONS)
    lines.append(f"- 命中统计：{counts}")
    lines.append("- 说明：只保留标题与摘要；这是候选池，不是最终 5 条成稿。")
    lines.append("")
    for section in SECTIONS:
        lines.append(f"## {section}")
        lines.append("")
        items = by_category[section]
        if not items:
            lines.append("当天该分类没有命中条目。")
            lines.append("")
            continue
        for index, item in enumerate(items, 1):
            lines.append(f"### {section}-{index}")
            lines.append(f"- 序号：`{index}`")
            lines.append(f"- ID：`{item.id}`")
            lines.append(f"- 标题：{item.title}")
            lines.append(f"- 来源：`{item.source}`")
            lines.append(f"- 发布时间：`{item.published_at_local}`")
            lines.append(f"- 入库时间：`{item.created_at_local}`")
            lines.append(f"- 命中标签：`{item.matched_categories}`")
            lines.append(f"- 链接：{item.url}")
            lines.append(f"- 摘要：{item.summary or '（空）'}")
            lines.append("")
    note_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    config = load_config()
    start, end = parse_window(args)
    rows = fetch_rows(config, start, end)
    translator = Translator()
    by_category = classify_rows(rows, translator)
    note_path = resolve_note_path(config, args, end)
    render_note(note_path, start, end, rows, by_category)
    print(note_path)
    print(json.dumps({section: len(by_category[section]) for section in SECTIONS}, ensure_ascii=False))


if __name__ == "__main__":
    main()
