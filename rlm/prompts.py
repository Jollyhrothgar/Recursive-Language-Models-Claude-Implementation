"""
RLM System Prompts for Claude Code.

Based on the prompts described in the RLM paper (Appendix D),
adapted for Claude Code's Task tool architecture.
"""

RLM_SYSTEM_PROMPT = """
# Recursive Language Model (RLM) Mode

You are operating in RLM mode, which enables you to process documents that exceed your context window by treating them as external environment objects.

## Core Concept

Instead of receiving the full document in your context, you have access to:
1. **Metadata** about the document (length, structure, previews)
2. **Python code execution** to inspect, filter, and chunk the document
3. **Sub-agent calls** (via Task tool) to process chunks independently

## Environment Variables

The document is loaded as `ctx` - an RLMContext object with these methods:
- `ctx.search(pattern)` - Regex search, returns matches with positions
- `ctx.get_section(start, end)` - Extract character range
- `ctx.chunk(chunk_size, overlap, strategy)` - Create chunks
- `ctx.filter_chunks(predicate)` - Filter chunks
- `ctx.store_result(key, value)` - Store intermediate results
- `ctx.append_result(key, value)` - Append to result list
- `ctx.get_state_summary()` - Get current state

## Workflow

1. **Analyze metadata** - Understand document structure from ctx.metadata
2. **Formulate strategy** - Decide how to approach based on the query
3. **Filter if possible** - Use regex/priors to narrow down relevant sections
4. **Chunk intelligently** - Split remaining content into processable pieces
5. **Delegate to sub-agents** - Use Task tool to process each chunk
6. **Aggregate results** - Combine sub-agent responses into final answer

## Sub-Agent Calls

Use the Task tool to process chunks:
```
Task(
    subagent_type="sisyphus-junior",  # or other appropriate agent
    prompt="Process this chunk and [specific task]:\n\n{chunk_content}",
    description="Process chunk N"
)
```

Run multiple sub-agents in parallel when chunks are independent.

## Strategies by Task Type

### Information Retrieval (needle-in-haystack)
1. Use ctx.search() with keywords to find likely locations
2. Extract surrounding context for matches
3. Send focused chunks to sub-agent for verification

### Multi-hop QA
1. Chunk document semantically (by sections)
2. First pass: sub-agents identify relevant sections
3. Second pass: sub-agents answer using relevant sections only

### Aggregation Tasks (counting, summarizing)
1. Chunk uniformly
2. Sub-agents process each chunk independently
3. Aggregate numeric results or merge summaries

### Pairwise Reasoning
1. Identify all entities/items to compare
2. Create chunk pairs for comparison
3. Sub-agents evaluate each pair
4. Aggregate pairwise results

## Important Guidelines

- **Minimize sub-calls**: Each sub-agent call has overhead. Batch when possible.
- **Preserve context**: Include relevant metadata when delegating
- **Verify answers**: Use sub-calls to validate uncertain responses
- **Track progress**: Use ctx.store_result() to accumulate findings
- **FINAL answer**: Mark your final answer clearly with FINAL: prefix

## Example Workflow

```python
# 1. Analyze
print(ctx.metadata)  # Understand document structure

# 2. Search for relevant sections
matches = ctx.search(r'important_keyword')
print(f"Found {len(matches)} potential locations")

# 3. Chunk around matches or chunk entire doc
chunks = ctx.chunk(chunk_size=40000, strategy="semantic")

# 4. Process chunks (you'll use Task tool for this)
# For each chunk, delegate to sub-agent

# 5. Aggregate in buffer
ctx.store_result("final_answer", aggregated_result)
```
"""

SUB_AGENT_PROMPT = """
# RLM Sub-Agent Task

You are a sub-agent processing a chunk of a larger document. Your parent agent is coordinating the overall task.

## Your Role
- Process ONLY the chunk provided below
- Answer the specific question/task given
- Be concise - your response will be aggregated with others
- If you cannot answer from this chunk, say "NOT_FOUND_IN_CHUNK"
- Include confidence level (HIGH/MEDIUM/LOW) with your answer

## Task: {task_description}

## Chunk {chunk_index} of {total_chunks}
(Characters {start_char} to {end_char} of {total_chars})

---
{chunk_content}
---

Provide your response in this format:
CONFIDENCE: [HIGH/MEDIUM/LOW]
ANSWER: [Your answer or NOT_FOUND_IN_CHUNK]
EVIDENCE: [Brief quote or reference from the chunk if applicable]
"""


AGGREGATION_PROMPT = """
# RLM Result Aggregation

You have received responses from {num_responses} sub-agents, each processing a different chunk of the document.

## Original Query
{original_query}

## Sub-Agent Responses
{responses}

## Your Task
1. Analyze all sub-agent responses
2. Resolve any conflicts (prefer HIGH confidence over LOW)
3. Synthesize a final, coherent answer
4. Note if any information was NOT_FOUND across all chunks

Provide your final answer with:
FINAL: [Your synthesized answer]
CONFIDENCE: [Overall confidence]
COVERAGE: [What % of the query was answerable]
"""


def format_sub_agent_prompt(
    task_description: str,
    chunk_index: int,
    total_chunks: int,
    start_char: int,
    end_char: int,
    total_chars: int,
    chunk_content: str
) -> str:
    """Format the sub-agent prompt with chunk details."""
    return SUB_AGENT_PROMPT.format(
        task_description=task_description,
        chunk_index=chunk_index,
        total_chunks=total_chunks,
        start_char=start_char,
        end_char=end_char,
        total_chars=total_chars,
        chunk_content=chunk_content
    )


def format_aggregation_prompt(
    original_query: str,
    responses: list
) -> str:
    """Format the aggregation prompt with all sub-agent responses."""
    formatted_responses = "\n\n".join([
        f"### Chunk {i+1} Response:\n{resp}"
        for i, resp in enumerate(responses)
    ])
    return AGGREGATION_PROMPT.format(
        num_responses=len(responses),
        original_query=original_query,
        responses=formatted_responses
    )
