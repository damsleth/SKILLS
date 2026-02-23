
#!/usr/bin/env bash
set -euo pipefail

# Install symlinks for all skills in this folder into the expected skill folders

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

SKILL_SRC="$SCRIPT_DIR/cognitive-ledger"

TARGETS=(
    "$HOME/.codex/skills/"
    "$HOME/.claude/skills/"
    "$HOME/.copilot/skills/"
)

if [ ! -e "$SKILL_SRC" ]; then
    echo "Source skill folder not found: $SKILL_SRC" >&2
    exit 1
fi


# Find all subfolders in SKILL_SRC (excluding . and ..)
find "$SKILL_SRC" -mindepth 1 -maxdepth 1 -type d | while read -r skill_folder; do
    skill_name="$(basename "$skill_folder")"
    for target_base in "${TARGETS[@]}"; do
        target="$target_base/$skill_name"
        mkdir -p "$(dirname "$target")"
        if [ -L "$target" ] || [ -e "$target" ]; then
            rm -rf "$target"
        fi
        ln -s "$skill_folder" "$target"
        echo "Created symlink: $target -> $skill_folder"
    done
done

echo "All done."
