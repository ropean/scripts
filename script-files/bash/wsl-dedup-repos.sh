#!/bin/bash

# @title WSL Dedup Repos
# @description Remove duplicate directories from /mnt/d/Git that also exist in ~/git
# @author ropean, Claude Sonnet (Anthropic)
# @version 1.0.0
#
# Compares Windows-side git repos (default: /mnt/d/Git) against WSL-side repos
# (default: ~/git) and, after confirmation, deletes the Windows-side copies of
# any directory that already exists on the WSL side.
#
# @example
#   ./wsl-dedup-repos.sh
#
# @requires bash, rimraf

WSL_DIR="$HOME/git"
WIN_DIR="/mnt/d/Git"

wsl_dirs=$(ls -d "$WSL_DIR"/*/ 2>/dev/null | xargs -I{} basename {})
win_dirs=$(ls -d "$WIN_DIR"/*/ 2>/dev/null | xargs -I{} basename {})

duplicates=()
while IFS= read -r dir; do
    if echo "$wsl_dirs" | grep -qx "$dir"; then
        duplicates+=("$dir")
    fi
done <<< "$win_dirs"

if [ ${#duplicates[@]} -eq 0 ]; then
    echo "No duplicates found. Nothing to clean up."
    exit 0
fi

echo "The following directories exist in both WSL ($WSL_DIR) and Windows ($WIN_DIR):"
echo ""
for dir in "${duplicates[@]}"; do
    echo "  $WIN_DIR/$dir"
done
echo ""
echo "${#duplicates[@]} director(ies) will be removed from the Windows side."
echo ""
read -p "Confirm deletion? [Y/n] " confirm
confirm="${confirm:-Y}"

if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Aborted."
    exit 0
fi

echo ""
for dir in "${duplicates[@]}"; do
    target="$WIN_DIR/$dir"
    echo "Removing: $target"
    rimraf "$target"
done

echo ""
echo "Done."
