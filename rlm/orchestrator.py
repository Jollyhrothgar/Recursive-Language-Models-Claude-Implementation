"""
RLM Orchestrator for Claude Code

This module provides the orchestration logic for RLM-style processing
using Claude Code's Task tool for sub-agent calls.

Usage in Claude Code:
1. Load document into RLMContext
2. Use the Task tool to spawn sub-agents for chunk processing
3. Aggregate results in main context
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from .core import RLMContext, ChunkInfo
from .prompts import format_sub_agent_prompt, format_aggregation_prompt


@dataclass
class SubAgentTask:
    """Represents a task to be executed by a sub-agent via Task tool."""
    chunk: ChunkInfo
    task_description: str
    agent_type: str = "sisyphus-junior"
    run_in_background: bool = True

    def to_task_params(self, ctx: RLMContext) -> Dict[str, Any]:
        """Generate parameters for Claude Code's Task tool."""
        prompt = format_sub_agent_prompt(
            task_description=self.task_description,
            chunk_index=self.chunk.index,
            total_chunks=len(ctx.chunks),
            start_char=self.chunk.start_char,
            end_char=self.chunk.end_char,
            total_chars=ctx.metadata["char_count"],
            chunk_content=self.chunk.content
        )
        return {
            "subagent_type": self.agent_type,
            "prompt": prompt,
            "description": f"RLM chunk {self.chunk.index}",
            "run_in_background": self.run_in_background
        }


class RLMOrchestrator:
    """
    Orchestrates RLM-style processing using Claude Code's Task tool.

    This class generates the Task tool calls needed for sub-agent processing.
    The actual Task tool invocation happens in Claude Code's context.
    """

    def __init__(self, ctx: RLMContext):
        self.ctx = ctx
        self.pending_tasks: List[SubAgentTask] = []
        self.completed_results: List[Dict[str, Any]] = []

    def create_chunk_tasks(
        self,
        task_description: str,
        agent_type: str = "sisyphus-junior",
        parallel: bool = True,
        chunk_filter: Optional[callable] = None
    ) -> List[SubAgentTask]:
        """
        Create sub-agent tasks for all chunks (or filtered chunks).

        Returns list of SubAgentTask objects that can be converted to Task tool calls.
        """
        chunks = self.ctx.chunks
        if chunk_filter:
            chunks = [c for c in chunks if chunk_filter(c)]

        tasks = [
            SubAgentTask(
                chunk=chunk,
                task_description=task_description,
                agent_type=agent_type,
                run_in_background=parallel
            )
            for chunk in chunks
        ]

        self.pending_tasks = tasks
        return tasks

    def generate_task_calls(self) -> str:
        """
        Generate the Task tool calls as instructions for Claude Code.

        Returns a string with the exact tool calls to make.
        """
        if not self.pending_tasks:
            return "No tasks to execute. Create chunks first with ctx.chunk()"

        instructions = ["# Execute these Task tool calls:\n"]

        for task in self.pending_tasks:
            params = task.to_task_params(self.ctx)
            instructions.append(f"""
Task(
    subagent_type="{params['subagent_type']}",
    description="{params['description']}",
    run_in_background={params['run_in_background']},
    prompt=\"\"\"{params['prompt'][:500]}...\"\"\"  # Truncated for display
)
""")

        if len(self.pending_tasks) > 1:
            instructions.append(
                "\n# NOTE: Call all Task tools in a SINGLE message for parallel execution"
            )

        return "\n".join(instructions)

    def create_aggregation_prompt(
        self,
        original_query: str,
        sub_responses: List[str]
    ) -> str:
        """Create the final aggregation prompt."""
        return format_aggregation_prompt(original_query, sub_responses)


def create_rlm_workflow(
    document_path: str,
    query: str,
    chunk_size: int = 40000,
    chunk_strategy: str = "semantic"
) -> str:
    """
    Generate a complete RLM workflow as instructions.

    This function outputs the step-by-step process to follow in Claude Code.
    """

    workflow = f"""
# RLM Workflow for: {query}

## Step 1: Load Document and Create Context

```python
from rlm import RLMContext

# Load the document
with open("{document_path}", "r") as f:
    document = f.read()

# Create RLM context
ctx = RLMContext(document)
print(ctx.metadata)
```

## Step 2: Analyze and Search (if applicable)

```python
# Search for relevant keywords
matches = ctx.search(r'relevant_pattern')
print(f"Found {{len(matches)}} matches")

# Or view document structure
print(ctx.metadata['headers_preview'])
```

## Step 3: Create Chunks

```python
chunks = ctx.chunk(
    chunk_size={chunk_size},
    strategy="{chunk_strategy}"
)
print(f"Created {{len(chunks)}} chunks")
```

## Step 4: Process Chunks with Sub-Agents

For each chunk, use the Task tool:

```
# Call these in PARALLEL (single message with multiple Task calls):

Task(
    subagent_type="sisyphus-junior",
    description="RLM chunk 0",
    prompt="Process this chunk for query: {query}\\n\\n[chunk 0 content]"
)

Task(
    subagent_type="sisyphus-junior",
    description="RLM chunk 1",
    prompt="Process this chunk for query: {query}\\n\\n[chunk 1 content]"
)

# ... continue for all chunks
```

## Step 5: Aggregate Results

After all sub-agents return, synthesize their responses:
- Combine findings from each chunk
- Resolve conflicts (prefer HIGH confidence)
- Produce final answer

## Step 6: Return Final Answer

FINAL: [Your synthesized answer based on all chunk results]
"""

    return workflow


# Pre-built strategies for common task types

STRATEGIES = {
    "needle_search": {
        "description": "Find specific information in a large document",
        "chunk_strategy": "uniform",
        "chunk_size": 50000,
        "approach": """
1. First, use ctx.search() with keywords from the query
2. If matches found, extract surrounding context only
3. If no matches, chunk entire document
4. Sub-agents verify if their chunk contains the answer
5. Aggregate: return first HIGH confidence match
"""
    },

    "summarization": {
        "description": "Summarize a large document",
        "chunk_strategy": "semantic",
        "chunk_size": 40000,
        "approach": """
1. Chunk by semantic boundaries (headers)
2. Sub-agents summarize each section
3. Aggregate summaries hierarchically
4. Final pass: create cohesive overall summary
"""
    },

    "multi_hop_qa": {
        "description": "Answer questions requiring multiple pieces of information",
        "chunk_strategy": "semantic",
        "chunk_size": 40000,
        "approach": """
1. Chunk semantically
2. First pass: sub-agents identify chunks with relevant info
3. Collect all relevant chunks
4. Second pass: answer query using only relevant chunks
5. Verify answer coherence
"""
    },

    "aggregation": {
        "description": "Count, list, or aggregate items across document",
        "chunk_strategy": "uniform",
        "chunk_size": 50000,
        "approach": """
1. Chunk uniformly
2. Sub-agents extract/count items in their chunk
3. Aggregate: sum counts, merge lists, deduplicate
4. Verify completeness
"""
    },

    "comparison": {
        "description": "Compare entities or concepts across document",
        "chunk_strategy": "semantic",
        "chunk_size": 30000,
        "approach": """
1. First pass: identify all entities to compare
2. Create focused chunks around each entity
3. Sub-agents extract attributes for each entity
4. Create comparison matrix
5. Synthesize findings
"""
    }
}


def get_strategy(task_type: str) -> Dict[str, Any]:
    """Get a pre-built strategy for a task type."""
    return STRATEGIES.get(task_type, STRATEGIES["needle_search"])
