#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${CODEX_HOME:-$HOME/.codex}/skills/ai-kuaixun"

mkdir -p "$(dirname "$TARGET_DIR")"
rm -rf "$TARGET_DIR"
cp -R "$REPO_DIR" "$TARGET_DIR"

if [[ ! -f "$TARGET_DIR/.env" && -f "$TARGET_DIR/.env.example" ]]; then
  cp "$TARGET_DIR/.env.example" "$TARGET_DIR/.env"
fi

python3 -m pip install -r "$TARGET_DIR/requirements.txt"

echo "Installed to $TARGET_DIR"
echo "Next:"
echo "1. Edit $TARGET_DIR/.env"
echo "2. Run: python3 $TARGET_DIR/scripts/fetch_ai_kuaixun.py"
