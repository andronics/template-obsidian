#!/bin/sh
# Template-owned: template-obsidian. The brain's checks, run by scripts/checks.sh:
# the vault (front matter, embeds, design records, actor notes), then the project's own scripts/check.sh.
set -eu
cd "$(dirname "$0")/../.."

uv run --quiet scripts/check-vault.py
sh scripts/check.sh
