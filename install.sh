#!/bin/bash
#
# RLM Installation Script
# Installs the RLM skill for Claude Code by appending to ~/.claude/CLAUDE.md
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLAUDE_DIR="$HOME/.claude"
CLAUDE_MD="$CLAUDE_DIR/CLAUDE.md"
MARKER_START="# >>> RLM-SKILL-START >>>"
MARKER_END="# <<< RLM-SKILL-END <<<"

echo "========================================"
echo "RLM Installer for Claude Code"
echo "========================================"
echo

# Check for uv
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed."
    echo "Install it from: https://docs.astral.sh/uv/"
    exit 1
fi

echo "[1/3] Setting up Python environment..."
cd "$SCRIPT_DIR"
uv sync
echo "      Done."
echo

echo "[2/3] Creating Claude Code config directory..."
mkdir -p "$CLAUDE_DIR"
echo "      Done."
echo

echo "[3/3] Installing /rlm skill to CLAUDE.md..."

# Check if already installed
if [ -f "$CLAUDE_MD" ] && grep -q "$MARKER_START" "$CLAUDE_MD"; then
    echo "      RLM skill already installed. Updating..."
    # Remove existing installation
    sed -i.bak "/$MARKER_START/,/$MARKER_END/d" "$CLAUDE_MD"
    rm -f "$CLAUDE_MD.bak"
fi

# Append RLM skill configuration
cat >> "$CLAUDE_MD" << SKILL_EOF

$MARKER_START
# RLM: Recursive Language Models

Process documents beyond context window using intelligent chunking.

## /rlm Command

When user invokes \`/rlm <document_path> <query>\`:

### Step 1: Load Document
\`\`\`bash
cd "$SCRIPT_DIR" && uv run python -c "
from rlm import RLMContext
with open('<DOCUMENT_PATH>') as f:
    ctx = RLMContext(f.read())
print(f'Chars: {ctx.metadata[\"char_count\"]:,}')
print(f'Tokens: {ctx.metadata[\"token_estimate\"]:,}')
print(f'Headers: {ctx.metadata[\"header_count\"]}')
"
\`\`\`

### Step 2: Decide Approach
- Under 100K tokens: process directly
- Over 100K tokens: use RLM chunking

### Step 3: Search First (optional)
\`\`\`bash
cd "$SCRIPT_DIR" && uv run python -c "
from rlm import RLMContext
with open('<DOCUMENT_PATH>') as f:
    ctx = RLMContext(f.read())
matches = ctx.search(r'<PATTERN>')
print(f'Found {len(matches)} matches')
for m in matches[:5]:
    print(f'  {m[\"start\"]}: {m[\"match\"][:50]}')
"
\`\`\`

### Step 4: Chunk
\`\`\`bash
cd "$SCRIPT_DIR" && uv run python -c "
from rlm import RLMContext
with open('<DOCUMENT_PATH>') as f:
    ctx = RLMContext(f.read())
# Strategies: uniform, paragraph, semantic
chunks = ctx.chunk(chunk_size=40000, overlap=500, strategy='uniform')
print(f'Created {len(chunks)} chunks')
for c in chunks:
    print(f'Chunk {c.index}: {c.token_estimate} tokens')
"
\`\`\`

### Step 5: Process Chunks in Parallel
Launch ALL chunk tasks in a SINGLE message:
\`\`\`
Task(
    subagent_type="sisyphus-junior",
    description="RLM chunk N of M",
    run_in_background=true,
    prompt="TASK: <query>\nCHUNK N of M:\n<content>\n\nRespond: CONFIDENCE: HIGH/MEDIUM/LOW\nANSWER: <findings or NOT_FOUND_IN_CHUNK>\nEVIDENCE: <quote>"
)
\`\`\`

### Step 6: Aggregate
- Collect responses, filter NOT_FOUND
- Prefer HIGH confidence
- Return: \`FINAL: <synthesized answer>\`

## Strategies
| Query Type | Strategy | Chunk Size |
|------------|----------|------------|
| Find specific info | uniform | 50K |
| Summarize | semantic | 40K |
| Complex QA | semantic | 40K |
| Count/list | uniform | 50K |

## Full Documentation
See: $SCRIPT_DIR/CLAUDE.md
$MARKER_END
SKILL_EOF

echo "      Done."
echo

echo "========================================"
echo "Installation complete!"
echo "========================================"
echo
echo "The /rlm command is now available in Claude Code."
echo
echo "Usage:"
echo "  /rlm <document_path> <query>"
echo
echo "Example:"
echo "  /rlm ./large_file.txt \"Summarize the main points\""
echo
echo "To uninstall, run:"
echo "  $SCRIPT_DIR/uninstall.sh"
echo
