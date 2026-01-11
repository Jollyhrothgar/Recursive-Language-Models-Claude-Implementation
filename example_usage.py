#!/usr/bin/env python3
"""
RLM Example Usage

This script demonstrates how to use the RLM implementation.
Run with: uv run example_usage.py
"""

from rlm import RLMContext, chunk_document, create_metadata
from rlm.orchestrator import RLMOrchestrator, get_strategy, STRATEGIES
from rlm.prompts import format_sub_agent_prompt


def demo_rlm_context():
    """Demonstrate RLMContext functionality."""
    print("=" * 60)
    print("RLM Context Demo")
    print("=" * 60)

    # Simulate a large document
    sample_doc = """
# Introduction

This is a sample document to demonstrate RLM processing.
The document contains multiple sections with various content.

# Section 1: Overview

Lorem ipsum dolor sit amet, consectetur adipiscing elit.
This section provides an overview of the main concepts.

Key points:
- Point A: Important finding about X
- Point B: Critical observation regarding Y
- Point C: Notable pattern in Z

# Section 2: Methodology

The methodology involves several steps:
1. Data collection from multiple sources
2. Preprocessing and normalization
3. Analysis using advanced techniques
4. Validation through cross-reference

# Section 3: Results

The results show significant improvements:
- Metric A improved by 25%
- Metric B showed 3x improvement
- Overall efficiency increased by 40%

# Section 4: Conclusion

In conclusion, this demonstrates the key capabilities.
Further work is needed to explore edge cases.
""" * 100  # Multiply to simulate larger document

    # Create RLM context
    ctx = RLMContext(sample_doc)

    print(f"\n1. Document Metadata:")
    print(f"   - Characters: {ctx.metadata['char_count']:,}")
    print(f"   - Estimated tokens: {ctx.metadata['token_estimate']:,}")
    print(f"   - Lines: {ctx.metadata['line_count']:,}")
    print(f"   - Headers found: {ctx.metadata['header_count']}")

    print(f"\n2. Search for 'Metric':")
    matches = ctx.search(r'Metric \w+')
    for m in matches[:3]:
        print(f"   - Found: '{m['match']}' at position {m['start']}")

    print(f"\n3. Chunking (semantic strategy):")
    chunks = ctx.chunk(chunk_size=5000, strategy="semantic")
    print(f"   Created {len(chunks)} chunks")
    for c in chunks[:3]:
        print(f"   - Chunk {c.index}: {c.token_estimate} tokens, preview: {c.preview[:50]}...")

    print(f"\n4. State summary:")
    print(ctx.get_state_summary())

    return ctx


def demo_orchestrator(ctx: RLMContext):
    """Demonstrate the orchestrator workflow."""
    print("\n" + "=" * 60)
    print("RLM Orchestrator Demo")
    print("=" * 60)

    orch = RLMOrchestrator(ctx)

    # Create tasks for chunks
    tasks = orch.create_chunk_tasks(
        task_description="Find all mentions of 'Metric' improvements and summarize them",
        agent_type="sisyphus-junior",
        parallel=True
    )

    print(f"\n1. Created {len(tasks)} sub-agent tasks")

    print("\n2. Sample Task tool call (what Claude Code would execute):")
    if tasks:
        params = tasks[0].to_task_params(ctx)
        print(f"""
   Task(
       subagent_type="{params['subagent_type']}",
       description="{params['description']}",
       run_in_background={params['run_in_background']},
       prompt="[{len(params['prompt'])} chars]"
   )
""")

    print("\n3. Available strategies:")
    for name, strategy in STRATEGIES.items():
        print(f"   - {name}: {strategy['description']}")


def demo_sub_agent_prompt():
    """Show what a sub-agent receives."""
    print("\n" + "=" * 60)
    print("Sub-Agent Prompt Demo")
    print("=" * 60)

    prompt = format_sub_agent_prompt(
        task_description="Find all performance metrics mentioned",
        chunk_index=2,
        total_chunks=5,
        start_char=10000,
        end_char=20000,
        total_chars=50000,
        chunk_content="[Sample chunk content would go here...]"
    )

    print("\nFormatted sub-agent prompt:")
    print("-" * 40)
    print(prompt[:800] + "...")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("RECURSIVE LANGUAGE MODELS (RLM)")
    print("Implementation for Claude Code")
    print("=" * 60)

    # Run demos
    ctx = demo_rlm_context()
    demo_orchestrator(ctx)
    demo_sub_agent_prompt()

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)
    print("""
To use RLM in Claude Code:

1. Load your document:
   ctx = RLMContext(document_text)

2. Analyze and chunk:
   ctx.chunk(chunk_size=40000, strategy="semantic")

3. Use Task tool to process chunks in parallel

4. Aggregate results

See rlm/orchestrator.py for detailed workflows.
""")
