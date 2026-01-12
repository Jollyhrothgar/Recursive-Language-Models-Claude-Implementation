---
name: rlm
description: Process documents beyond context window using Recursive Language Models chunking
---

# RLM Skill - Recursive Language Models

Process massive documents that exceed context limits by chunking and parallel sub-agent processing.

## Invocation

```
/rlm <document_path> <query>
```

## Workflow

### Step 1: Load Document

Run from the RLM project directory (set during installation):

```bash
cd <RLM_PROJECT_DIR> && uv run python -c "
from rlm import RLMContext
with open('<document_path>') as f:
    ctx = RLMContext(f.read())
print(f'Size: {ctx.metadata[\"char_count\"]:,} chars')
print(f'Tokens: {ctx.metadata[\"token_estimate\"]:,}')
print(f'Headers: {ctx.metadata[\"header_count\"]}')
"
```

### Step 2: Decide Approach

- Under 100K tokens: process directly without RLM
- Over 100K tokens: proceed with RLM chunking

### Step 3: Search First (for needle queries)

```python
matches = ctx.search(r'<pattern>')
# If matches are localized, extract just those sections
```

### Step 4: Chunk

```python
# Strategies: uniform (logs), paragraph (prose), semantic (markdown)
chunks = ctx.chunk(chunk_size=40000, overlap=500, strategy='uniform')
```

### Step 5: Process Chunks in Parallel

**CRITICAL:** Launch ALL chunk tasks in a SINGLE message:

```
Task(
    subagent_type="sisyphus-junior",
    description="RLM chunk N of M",
    run_in_background=true,
    prompt="""
    Processing chunk N of M.
    TASK: <query>
    CHUNK: <content>

    Respond with:
    CONFIDENCE: HIGH/MEDIUM/LOW
    ANSWER: <findings>
    EVIDENCE: <quotes>

    Or: NOT_FOUND_IN_CHUNK
    """
)
```

### Step 6: Aggregate Results

- Collect all sub-agent responses
- Filter out NOT_FOUND_IN_CHUNK
- Prefer HIGH confidence over MEDIUM/LOW
- Synthesize final answer
- Return with `FINAL:` prefix

## Strategies Reference

| Query Type | Strategy | Chunk Size | Notes |
|------------|----------|------------|-------|
| Find specific info | uniform | 50K | Search first |
| Summarize | semantic | 40K | Hierarchical merge |
| Complex QA | semantic | 40K | Two-pass |
| Count/list | uniform | 50K | Sum results |

## Full Documentation

After installation, see the project's CLAUDE.md for complete API reference and examples.
