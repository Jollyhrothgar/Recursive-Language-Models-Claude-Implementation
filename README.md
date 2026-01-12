# RLM: Recursive Language Models for Claude Code

**Process documents beyond Claude's context window using intelligent chunking and parallel sub-agent processing.**

This implementation is based on [Recursive Language Models](https://arxiv.org/html/2512.24601v1) by Zhang, Kraska, and Khattab (MIT CSAIL).

## What is RLM?

Large language models have a context window limit. RLM solves this by treating documents as external environment objects that can be inspected, searched, and processed in chunks. Instead of fitting everything in context, RLM:

1. **Loads metadata** about your document (size, structure, previews)
2. **Searches** for relevant sections using regex patterns
3. **Chunks** the document using smart strategies (uniform, paragraph, semantic)
4. **Delegates** chunk processing to parallel sub-agents
5. **Aggregates** results into a coherent answer

## Installation

### Prerequisites

- [Claude Code](https://claude.ai/code) CLI installed
- [UV](https://docs.astral.sh/uv/) for Python environment management

### Quick Install

```bash
git clone https://github.com/Jollyhrothgar/Recursive-Language-Models-Claude-Implementation.git
cd Recursive-Language-Models-Claude-Implementation
./install.sh
```

This will:
- Set up the Python environment with `uv sync`
- Append the `/rlm` skill configuration to `~/.claude/CLAUDE.md`

### Manual Install

```bash
# Install Python dependencies
uv sync

# Then manually add the RLM instructions from skill/SKILL.md to your ~/.claude/CLAUDE.md
```

### Uninstall

```bash
./uninstall.sh
```

## Usage

### With Claude Code (Recommended)

Once installed, use the `/rlm` command in Claude Code:

```
/rlm ./path/to/large_document.txt "What are the main findings?"
```

Claude will automatically:
- Load and analyze the document
- Choose an appropriate chunking strategy
- Process chunks in parallel
- Return an aggregated answer

### Example Queries

```
/rlm ./research_paper.pdf "Summarize the methodology section"
/rlm ./server_logs.txt "Find all error messages and their frequencies"
/rlm ./legal_contract.txt "What are the termination clauses?"
/rlm ./codebase_dump.txt "How is authentication handled?"
```

### As a Python Library

```python
from rlm import RLMContext

# Load your document
with open("large_document.txt") as f:
    ctx = RLMContext(f.read())

# Check document metadata
print(f"Size: {ctx.metadata['char_count']:,} characters")
print(f"Estimated tokens: {ctx.metadata['token_estimate']:,}")

# Search for specific patterns
matches = ctx.search(r"ERROR|WARNING")
print(f"Found {len(matches)} log entries")

# Chunk the document
chunks = ctx.chunk(chunk_size=40000, strategy="semantic")
print(f"Created {len(chunks)} chunks")
```

## How It Works

### Chunking Strategies

| Strategy | Best For | Description |
|----------|----------|-------------|
| `uniform` | Logs, raw text | Equal-sized chunks with overlap |
| `paragraph` | Articles, docs | Respects paragraph boundaries |
| `semantic` | Markdown, structured | Splits on headers/sections |

### Task Strategies

| Strategy | Use Case |
|----------|----------|
| `needle_search` | Finding specific information |
| `summarization` | Condensing large documents |
| `multi_hop_qa` | Complex questions requiring multiple facts |
| `aggregation` | Counting, listing items |
| `comparison` | Comparing entities across a document |

### Processing Flow

```
Document → Metadata Analysis → Search/Filter → Chunk → Parallel Sub-Agents → Aggregate → Answer
```

## API Reference

### RLMContext

```python
ctx = RLMContext(document: str)

# Properties
ctx.metadata          # Document metadata (size, structure, previews)
ctx.chunks            # List of ChunkInfo objects after chunking
ctx.buffer            # Storage for intermediate results

# Methods
ctx.search(pattern)              # Regex search with context
ctx.get_section(start, end)      # Extract character range
ctx.chunk(size, overlap, strategy)  # Split into chunks
ctx.filter_chunks(predicate)     # Filter chunks by condition
ctx.store_result(key, value)     # Store intermediate result
ctx.append_result(key, value)    # Append to result list
ctx.get_state_summary()          # Get processing state
```

### ChunkInfo

```python
chunk.index           # Chunk number (0-indexed)
chunk.start_char      # Starting character position
chunk.end_char        # Ending character position
chunk.content         # The chunk text
chunk.token_estimate  # Approximate token count
chunk.preview         # First 100 characters
```

## Project Structure

```
rlm-claude/
├── rlm/
│   ├── __init__.py      # Package exports
│   ├── core.py          # RLMContext, chunking logic
│   ├── prompts.py       # System prompts for RLM mode
│   └── orchestrator.py  # Workflow coordination
├── skill/
│   └── SKILL.md         # Claude Code skill definition
├── example_usage.py     # Demo script
├── install.sh           # Installation script
├── uninstall.sh         # Uninstallation script
└── CLAUDE.md            # Instructions for Claude Code
```

## Running Tests

```bash
uv run python example_usage.py
```

## Contributing

Contributions welcome! Please open an issue or PR.

## License

MIT

## References

- [Recursive Language Models Paper](https://arxiv.org/html/2512.24601v1)
- [Claude Code Documentation](https://docs.anthropic.com/claude-code)
- [UV Package Manager](https://docs.astral.sh/uv/)
