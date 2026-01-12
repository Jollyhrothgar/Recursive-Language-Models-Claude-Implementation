# RLM: Recursive Language Models for Claude Code

This project enables processing of documents that exceed Claude's context window using intelligent chunking and parallel sub-agent processing.

**Note:** Run all `uv run` commands from the RLM project directory. The install script embeds the correct path.

## Quick Reference

| Command | Description |
|---------|-------------|
| `/rlm <path> <query>` | Process a large document with RLM |
| `uv run python example_usage.py` | Run the demo script |
| `./install.sh` | Install RLM skill to Claude Code |
| `./uninstall.sh` | Remove RLM skill from Claude Code |

## When to Use RLM

Use RLM when:
- Document exceeds ~100K tokens (400K+ characters)
- You need to search, summarize, or query very large files
- User invokes `/rlm <document_path> <query>`

Do NOT use RLM when:
- Document fits comfortably in context
- Simple file operations suffice

---

## /rlm Skill Workflow

When the user invokes `/rlm <document_path> <query>`:

### Step 1: Load and Analyze

```bash
uv run python -c "
from rlm import RLMContext
with open('<DOCUMENT_PATH>') as f:
    ctx = RLMContext(f.read())
print('=== Document Metadata ===')
print(f'Characters: {ctx.metadata[\"char_count\"]:,}')
print(f'Tokens (est): {ctx.metadata[\"token_estimate\"]:,}')
print(f'Lines: {ctx.metadata[\"line_count\"]:,}')
print(f'Headers: {ctx.metadata[\"header_count\"]}')
if ctx.metadata['headers_preview']:
    print('Structure:', ctx.metadata['headers_preview'][:5])
"
```

**Decision Point:**
- Under 100K tokens → Consider processing directly without RLM
- Over 100K tokens → Proceed with RLM chunking

### Step 2: Choose Strategy

| Query Type | Strategy | Chunk Size | Approach |
|------------|----------|------------|----------|
| Find specific info | `needle_search` | 50K | Search first, then verify |
| Summarize document | `summarization` | 40K | Semantic chunks, hierarchical merge |
| Complex question | `multi_hop_qa` | 40K | Two-pass: identify then answer |
| Count/list items | `aggregation` | 50K | Uniform chunks, sum results |
| Compare entities | `comparison` | 30K | Entity-focused chunks |

### Step 3: Search First (for needle queries)

```bash
uv run python -c "
from rlm import RLMContext
with open('<DOCUMENT_PATH>') as f:
    ctx = RLMContext(f.read())
matches = ctx.search(r'<SEARCH_PATTERN>')
print(f'Found {len(matches)} matches')
for m in matches[:10]:
    print(f'  Position {m[\"start\"]}: {m[\"match\"][:50]}...')
"
```

If matches are found and localized, extract just those sections.

### Step 4: Chunk the Document

```bash
uv run python -c "
from rlm import RLMContext
import json
with open('<DOCUMENT_PATH>') as f:
    ctx = RLMContext(f.read())
chunks = ctx.chunk(chunk_size=40000, overlap=500, strategy='<STRATEGY>')
print(f'Created {len(chunks)} chunks')
for c in chunks:
    print(f'Chunk {c.index}: chars {c.start_char}-{c.end_char} ({c.token_estimate} tokens)')
"
```

### Step 5: Process Chunks with Sub-Agents

**CRITICAL: Launch ALL chunk tasks in a SINGLE message for parallel execution.**

For each chunk, use the Task tool:

```
Task(
    subagent_type="sisyphus-junior",
    description="RLM chunk N of M",
    run_in_background=true,
    prompt="""
You are processing chunk N of M from a larger document.

TASK: <user's query>

CHUNK CONTENT (characters X to Y of Z total):
---
<chunk content here>
---

Respond EXACTLY in this format:
CONFIDENCE: HIGH | MEDIUM | LOW
ANSWER: <your findings, or NOT_FOUND_IN_CHUNK if not relevant>
EVIDENCE: <brief quote from the chunk supporting your answer>
"""
)
```

### Step 6: Aggregate Results

After all sub-agents return:

1. Collect all responses
2. Filter out `NOT_FOUND_IN_CHUNK` responses
3. Resolve conflicts (prefer HIGH confidence over MEDIUM/LOW)
4. Synthesize a coherent final answer
5. Return with `FINAL:` prefix

```
FINAL: <synthesized answer based on all chunk results>
```

---

## RLMContext API

### Properties

| Property | Type | Description |
|----------|------|-------------|
| `document` | str | The full document text |
| `metadata` | dict | Document analysis (size, structure) |
| `chunks` | list | ChunkInfo objects after chunking |
| `buffer` | dict | Storage for intermediate results |
| `sub_call_results` | list | Recorded sub-agent responses |

### Metadata Fields

```python
ctx.metadata = {
    "char_count": int,        # Total characters
    "token_estimate": int,    # Approximate tokens (chars / 4)
    "line_count": int,        # Number of lines
    "word_count": int,        # Number of words
    "header_count": int,      # Markdown headers found
    "headers_preview": list,  # First 10 headers
    "first_500_chars": str,   # Document start preview
    "last_500_chars": str,    # Document end preview
}
```

### Methods

```python
# Search with regex
matches = ctx.search(r'pattern')
# Returns: [{"match": str, "start": int, "end": int, "context": str}, ...]

# Extract section
section = ctx.get_section(start_char, end_char)

# Chunk document
chunks = ctx.chunk(
    chunk_size=50000,      # Target chars per chunk
    overlap=500,           # Overlap between chunks
    strategy="uniform"     # uniform | paragraph | semantic
)

# Filter chunks
relevant = ctx.filter_chunks(lambda c: "keyword" in c.content)

# Store results
ctx.store_result("key", value)
ctx.append_result("list_key", item)

# Get state
print(ctx.get_state_summary())
```

---

## Chunking Strategies

### uniform
- Equal-sized chunks with configurable overlap
- Tries to break at natural boundaries (newlines, periods)
- Best for: logs, raw text, unstructured data

### paragraph
- Respects paragraph boundaries (`\n\n`)
- Keeps paragraphs together up to max size
- Best for: articles, prose, documentation

### semantic
- Splits on markdown headers (`#`, `##`, etc.)
- Keeps sections together up to max size
- Best for: markdown docs, structured content

---

## Task Strategies

### needle_search
1. Search with `ctx.search()` using query keywords
2. If matches found, extract surrounding context only
3. If no matches, chunk entire document
4. Sub-agents verify if chunk contains answer
5. Return first HIGH confidence match

### summarization
1. Chunk by semantic boundaries
2. Sub-agents summarize each section
3. Aggregate summaries hierarchically
4. Final pass: create cohesive overall summary

### multi_hop_qa
1. Chunk semantically
2. First pass: identify chunks with relevant info
3. Collect relevant chunks
4. Second pass: answer using only relevant chunks
5. Verify answer coherence

### aggregation
1. Chunk uniformly
2. Sub-agents extract/count items per chunk
3. Sum counts, merge lists, deduplicate
4. Verify completeness

### comparison
1. First pass: identify all entities to compare
2. Create focused chunks around each entity
3. Sub-agents extract attributes
4. Create comparison matrix
5. Synthesize findings

---

## Guidelines

### Efficiency
- **Search before chunking** - Use `ctx.search()` to narrow scope
- **Batch sub-agents** - Launch ALL in one message for parallel execution
- **Filter chunks** - Skip obviously irrelevant chunks
- **Right-size chunks** - Larger chunks = fewer sub-agents = less overhead

### Accuracy
- **Track confidence** - Prefer HIGH over MEDIUM/LOW
- **Verify answers** - If uncertain, spawn verification sub-agent
- **Handle NOT_FOUND** - Don't force answers from irrelevant chunks
- **Cross-reference** - If multiple chunks have answers, compare them

### Response Format
- Always return final answer with `FINAL:` prefix
- Include confidence level
- Note if parts of query couldn't be answered

---

## Example Workflows

### Log Analysis
```
/rlm ./server.log "Find all errors and count by type"

1. Load: ctx = RLMContext(log_content)
2. Search: ctx.search(r'ERROR|FATAL|Exception')
3. Chunk: uniform, 50K chars
4. Sub-agents: Count error types per chunk
5. Aggregate: Sum counts across chunks
6. FINAL: "Found 1,247 errors: ConnectionError (45%), TimeoutError (30%)..."
```

### Document Summarization
```
/rlm ./research_paper.pdf "Summarize the key findings"

1. Load: ctx = RLMContext(paper_text)
2. Analyze: Check headers for structure
3. Chunk: semantic (by sections)
4. Sub-agents: Summarize each section
5. Aggregate: Combine into coherent summary
6. FINAL: "The paper presents three key findings..."
```

### Information Retrieval
```
/rlm ./contract.txt "What is the termination clause?"

1. Load: ctx = RLMContext(contract_text)
2. Search: ctx.search(r'terminat|cancel|end.?of.?agreement')
3. Extract: Get sections around matches
4. Sub-agents: Verify and extract clause details
5. FINAL: "The termination clause (Section 8.2) states..."
```

---

## Troubleshooting

### Document Too Large
If even metadata extraction fails:
1. Use shell tools to get file size first
2. Consider preprocessing (extract relevant sections)
3. Use streaming approach if available

### No Matches Found
If `NOT_FOUND_IN_CHUNK` from all sub-agents:
1. Verify the query is answerable from the document
2. Try broader search patterns
3. Consider full document chunking without pre-filtering

### Conflicting Answers
If sub-agents give different answers:
1. Check confidence levels
2. Look at evidence/quotes
3. May indicate ambiguity in source document
4. Report all findings with context

---

## Project Structure

```
rlm/
├── __init__.py      # Package exports: RLMContext, chunk_document, prompts
├── core.py          # RLMContext class, chunking algorithms
├── prompts.py       # System prompts for RLM mode and sub-agents
└── orchestrator.py  # RLMOrchestrator, pre-built strategies

skill/
└── SKILL.md         # Claude Code skill definition for /rlm command
```
