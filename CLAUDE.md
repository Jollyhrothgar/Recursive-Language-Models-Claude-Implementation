# RLM: Recursive Language Models for Claude Code

This project implements the RLM (Recursive Language Models) technique from the MIT paper, enabling Claude Code to process documents beyond its context window.

## Installation

This project uses [UV](https://docs.astral.sh/uv/) for Python environment management.

```bash
# Install dependencies and create virtual environment
uv sync

# Run the example
uv run python example_usage.py
```

## Skill Setup

The `/rlm` skill is in `skill/SKILL.md`. To enable it, symlink to Claude's skills directory:

```bash
ln -s /Users/mike/workspace/rlm_paper/skill ~/.claude/skills/rlm
```

Then invoke with `/rlm <document_path> <query>`.

## Quick Start

```python
# Use within UV environment: uv run python your_script.py
from rlm import RLMContext

# Load massive document
with open("huge_document.txt") as f:
    doc = f.read()

ctx = RLMContext(doc)
ctx.chunk(chunk_size=40000, strategy="semantic")
```

Then use Task tool to process chunks in parallel.

## /rlm Skill

When the user invokes `/rlm <document_path> <query>`, activate RLM mode:

### RLM Mode Activation

1. **Load Document as Context Variable**
   ```python
   from rlm import RLMContext
   with open(document_path) as f:
       ctx = RLMContext(f.read())
   ```

2. **Analyze Metadata First**
   - Check `ctx.metadata` for document size and structure
   - If under 100K tokens, consider processing directly
   - If over 100K tokens, proceed with RLM chunking

3. **Apply Appropriate Strategy**
   - Needle search: Use `ctx.search()` first to narrow down
   - Summarization: Chunk semantically, summarize per chunk
   - Multi-hop QA: Two-pass (identify relevant chunks, then answer)
   - Aggregation: Uniform chunks, count/collect per chunk

4. **Process Chunks with Sub-Agents**
   Use Task tool with `sisyphus-junior` agent:
   ```
   Task(
       subagent_type="sisyphus-junior",
       description="RLM chunk N",
       run_in_background=true,
       prompt="[chunk content + task]"
   )
   ```
   Call ALL chunk tasks in a SINGLE message for parallel execution.

5. **Aggregate Results**
   - Collect all sub-agent responses
   - Resolve conflicts (prefer HIGH confidence)
   - Synthesize final answer

6. **Return with FINAL: prefix**

### RLM Guidelines

- **Minimize sub-calls**: Batch when possible, each has overhead
- **Filter first**: Use regex search before full chunking
- **Verify answers**: Use sub-calls to validate uncertain responses
- **Track progress**: Store intermediate results in `ctx.buffer`
- **Parallel execution**: Always run independent chunk tasks in parallel

### Example Workflow

```
User: /rlm ./massive_log.txt "Find all error messages and their frequencies"

Claude Code:
1. Load: ctx = RLMContext(log_content)
2. Search: matches = ctx.search(r'ERROR|WARN|FATAL')
3. If many matches, chunk around them
4. Task tool (parallel): Process each chunk, count errors
5. Aggregate: Sum counts, merge error types
6. FINAL: "Found 1,247 errors: ConnectionError (45%), TimeoutError (30%)..."
```

## Project Structure

```
rlm/
├── __init__.py      # Package exports
├── core.py          # RLMContext, chunking, metadata
├── prompts.py       # System prompts for RLM mode
└── orchestrator.py  # Workflow orchestration
```

## API Reference

### RLMContext

```python
ctx = RLMContext(document: str)

ctx.metadata          # Dict with char_count, token_estimate, headers, etc.
ctx.search(pattern)   # Regex search, returns matches with positions
ctx.get_section(s, e) # Extract character range
ctx.chunk(size, overlap, strategy)  # Create chunks
ctx.filter_chunks(fn) # Filter chunks by predicate
ctx.store_result(k,v) # Store intermediate result
ctx.buffer            # Access stored results
```

### Chunking Strategies

- `uniform`: Equal-sized chunks with overlap
- `paragraph`: Split on paragraph boundaries
- `semantic`: Split on markdown headers

### Pre-built Task Strategies

- `needle_search`: Find specific information
- `summarization`: Summarize large documents
- `multi_hop_qa`: Answer complex questions
- `aggregation`: Count/list items across document
- `comparison`: Compare entities
