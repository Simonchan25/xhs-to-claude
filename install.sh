#!/usr/bin/env bash
# One-shot installer — copies the skill into ~/.claude/skills/share-link/
# so it's auto-discovered by Claude Code in any project.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.claude/skills/share-link"

mkdir -p "$DEST"
cp "$HERE/SKILL.md" "$HERE/fetch.py" "$DEST/"
chmod +x "$DEST/fetch.py"

echo "✓ Installed to $DEST"
echo
echo "Next steps:"
echo "  1. Install ffmpeg (required):            brew install ffmpeg"
echo "  2. Install yt-dlp (for Bilibili):        pip install yt-dlp"
echo "  3. Install mlx-whisper (optional):       pip install mlx-whisper"
echo "  4. Paste any xhs / xhslink / bilibili / b23.tv"
echo "     link into a Claude Code conversation."
