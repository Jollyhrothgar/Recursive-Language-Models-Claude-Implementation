"""
Recursive Language Models (RLM) Implementation for Claude Code

Based on: "Recursive Language Models" by Zhang, Kraska, and Khattab (MIT CSAIL)
Paper: https://arxiv.org/html/2512.24601v1

This implementation uses Claude Code's Task tool for sub-LM calls,
enabling processing of documents beyond the context window limit.
"""

from .core import RLMContext, chunk_document, create_metadata
from .prompts import RLM_SYSTEM_PROMPT, SUB_AGENT_PROMPT

__version__ = "0.1.0"
__all__ = [
    "RLMContext",
    "chunk_document",
    "create_metadata",
    "RLM_SYSTEM_PROMPT",
    "SUB_AGENT_PROMPT",
]
