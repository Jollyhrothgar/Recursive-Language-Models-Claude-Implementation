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

Follow the full instructions in the project's CLAUDE.md.

### Quick Reference

1. **Load document** with RLMContext
2. **Check metadata** - if under 100K tokens, process directly
3. **Search first** for needle queries using `ctx.search()`
4. **Chunk** using appropriate strategy (uniform/paragraph/semantic)
5. **Process chunks in parallel** via Task tool with sisyphus-junior
6. **Aggregate results** preferring HIGH confidence
7. **Return with FINAL:** prefix

### Run Python Code

Use uv from the project directory:

```bash
cd /Users/mike/workspace/rlm_paper && uv run python -c "
from rlm import RLMContext
with open('<document_path>') as f:
    ctx = RLMContext(f.read())
print(f'Size: {ctx.metadata[\"char_count\"]:,} chars')
print(f'Tokens: {ctx.metadata[\"token_estimate\"]:,}')
ctx.chunk(chunk_size=40000, overlap=200, strategy='uniform')
print(f'Chunks: {len(ctx.chunks)}')
"
```

### Sub-Agent Prompt Format

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

**CRITICAL:** Launch ALL chunk tasks in a SINGLE message for parallel execution.
