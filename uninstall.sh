#!/bin/bash
#
# RLM Uninstallation Script
# Removes the RLM skill from Claude Code's CLAUDE.md
#

set -e

CLAUDE_MD="$HOME/.claude/CLAUDE.md"
MARKER_START="# >>> RLM-SKILL-START >>>"
MARKER_END="# <<< RLM-SKILL-END <<<"

echo "========================================"
echo "RLM Uninstaller for Claude Code"
echo "========================================"
echo

echo "[1/2] Removing /rlm skill from CLAUDE.md..."
if [ -f "$CLAUDE_MD" ] && grep -q "$MARKER_START" "$CLAUDE_MD"; then
    # Remove the RLM section between markers
    sed -i.bak "/$MARKER_START/,/$MARKER_END/d" "$CLAUDE_MD"
    rm -f "$CLAUDE_MD.bak"

    # Remove trailing empty lines
    sed -i.bak -e :a -e '/^\n*$/{$d;N;ba' -e '}' "$CLAUDE_MD" 2>/dev/null || true
    rm -f "$CLAUDE_MD.bak"

    echo "      Removed RLM skill configuration."
else
    echo "      RLM skill not found in CLAUDE.md (already uninstalled)."
fi
echo

echo "[2/2] Cleanup options..."
echo "      Python environment preserved in project directory."
echo "      To fully remove, delete the project folder."
echo

echo "========================================"
echo "Uninstallation complete!"
echo "========================================"
echo
echo "The /rlm command has been removed from Claude Code."
echo
echo "To reinstall, run install.sh from the project directory."
echo
