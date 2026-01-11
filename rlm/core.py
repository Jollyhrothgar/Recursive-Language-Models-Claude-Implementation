"""
Core RLM functionality: context management, chunking, and state.
"""

import re
import json
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path


@dataclass
class ChunkInfo:
    """Information about a document chunk."""
    index: int
    start_char: int
    end_char: int
    content: str
    token_estimate: int  # Rough estimate: ~4 chars per token

    @property
    def preview(self) -> str:
        """First 100 chars of chunk."""
        return self.content[:100] + "..." if len(self.content) > 100 else self.content


@dataclass
class RLMContext:
    """
    Manages the RLM execution context - the 'REPL environment' from the paper.

    Holds the document as a variable, tracks state, and provides
    programmatic access methods.
    """
    document: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    buffer: Dict[str, Any] = field(default_factory=dict)  # For accumulating results
    chunks: List[ChunkInfo] = field(default_factory=list)
    sub_call_results: List[Dict[str, Any]] = field(default_factory=list)

    def __post_init__(self):
        self.metadata = create_metadata(self.document)

    def search(self, pattern: str, flags: int = 0) -> List[Dict[str, Any]]:
        """Search document with regex, return matches with positions."""
        matches = []
        for m in re.finditer(pattern, self.document, flags):
            matches.append({
                "match": m.group(),
                "start": m.start(),
                "end": m.end(),
                "groups": m.groups(),
                "context": self.document[max(0, m.start()-50):m.end()+50]
            })
        return matches

    def get_section(self, start: int, end: int) -> str:
        """Extract a section of the document by character positions."""
        return self.document[start:end]

    def chunk(self,
              chunk_size: int = 50000,
              overlap: int = 500,
              strategy: str = "uniform") -> List[ChunkInfo]:
        """
        Chunk the document using specified strategy.

        Strategies:
        - uniform: Equal-sized chunks with overlap
        - paragraph: Split on paragraph boundaries
        - semantic: Split on section headers/semantic boundaries
        """
        if strategy == "uniform":
            self.chunks = chunk_document(self.document, chunk_size, overlap)
        elif strategy == "paragraph":
            self.chunks = chunk_by_paragraphs(self.document, chunk_size)
        elif strategy == "semantic":
            self.chunks = chunk_by_headers(self.document, chunk_size)
        else:
            raise ValueError(f"Unknown chunking strategy: {strategy}")

        return self.chunks

    def filter_chunks(self, predicate: Callable[[ChunkInfo], bool]) -> List[ChunkInfo]:
        """Filter chunks based on a predicate function."""
        return [c for c in self.chunks if predicate(c)]

    def store_result(self, key: str, value: Any):
        """Store a result in the buffer for later aggregation."""
        self.buffer[key] = value

    def append_result(self, key: str, value: Any):
        """Append to a list in the buffer."""
        if key not in self.buffer:
            self.buffer[key] = []
        self.buffer[key].append(value)

    def record_sub_call(self, chunk_index: int, query: str, result: str):
        """Record a sub-agent call result."""
        self.sub_call_results.append({
            "chunk_index": chunk_index,
            "query": query,
            "result": result
        })

    def get_state_summary(self) -> str:
        """Get a summary of current RLM state for the model."""
        return f"""RLM State Summary:
- Document length: {self.metadata['char_count']:,} chars (~{self.metadata['token_estimate']:,} tokens)
- Chunks created: {len(self.chunks)}
- Sub-calls made: {len(self.sub_call_results)}
- Buffer keys: {list(self.buffer.keys())}
"""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize context for passing to sub-agents."""
        return {
            "metadata": self.metadata,
            "buffer": self.buffer,
            "chunk_count": len(self.chunks),
            "sub_call_count": len(self.sub_call_results)
        }


def create_metadata(document: str) -> Dict[str, Any]:
    """Create metadata about a document for the RLM context."""
    lines = document.split('\n')

    # Detect document structure
    headers = re.findall(r'^#{1,6}\s+.+$', document, re.MULTILINE)

    return {
        "char_count": len(document),
        "token_estimate": len(document) // 4,  # Rough estimate
        "line_count": len(lines),
        "word_count": len(document.split()),
        "header_count": len(headers),
        "headers_preview": headers[:10],  # First 10 headers
        "first_500_chars": document[:500],
        "last_500_chars": document[-500:] if len(document) > 500 else document,
    }


def chunk_document(
    document: str,
    chunk_size: int = 50000,
    overlap: int = 500
) -> List[ChunkInfo]:
    """
    Split document into overlapping chunks.

    Args:
        document: The full document text
        chunk_size: Target size per chunk in characters
        overlap: Overlap between chunks to maintain context

    Returns:
        List of ChunkInfo objects
    """
    chunks = []
    start = 0
    index = 0

    while start < len(document):
        end = min(start + chunk_size, len(document))

        # Try to break at a natural boundary (newline, period)
        if end < len(document):
            # Look for newline near the boundary
            newline_pos = document.rfind('\n', end - 200, end)
            if newline_pos > start:
                end = newline_pos + 1
            else:
                # Look for period
                period_pos = document.rfind('. ', end - 200, end)
                if period_pos > start:
                    end = period_pos + 2

        chunk_content = document[start:end]
        chunks.append(ChunkInfo(
            index=index,
            start_char=start,
            end_char=end,
            content=chunk_content,
            token_estimate=len(chunk_content) // 4
        ))

        index += 1
        start = end - overlap if end < len(document) else end

    return chunks


def chunk_by_paragraphs(document: str, max_chunk_size: int = 50000) -> List[ChunkInfo]:
    """Chunk by paragraph boundaries, respecting max size."""
    paragraphs = re.split(r'\n\s*\n', document)
    chunks = []
    current_chunk = ""
    current_start = 0
    index = 0

    for para in paragraphs:
        if len(current_chunk) + len(para) > max_chunk_size and current_chunk:
            chunks.append(ChunkInfo(
                index=index,
                start_char=current_start,
                end_char=current_start + len(current_chunk),
                content=current_chunk,
                token_estimate=len(current_chunk) // 4
            ))
            index += 1
            current_start = current_start + len(current_chunk)
            current_chunk = para + "\n\n"
        else:
            current_chunk += para + "\n\n"

    if current_chunk.strip():
        chunks.append(ChunkInfo(
            index=index,
            start_char=current_start,
            end_char=current_start + len(current_chunk),
            content=current_chunk,
            token_estimate=len(current_chunk) // 4
        ))

    return chunks


def chunk_by_headers(document: str, max_chunk_size: int = 50000) -> List[ChunkInfo]:
    """Chunk by markdown headers, respecting max size."""
    # Split on headers while keeping the header with its content
    sections = re.split(r'(^#{1,6}\s+.+$)', document, flags=re.MULTILINE)

    chunks = []
    current_chunk = ""
    current_start = 0
    index = 0

    i = 0
    while i < len(sections):
        section = sections[i]
        # If this is a header, combine with next section
        if re.match(r'^#{1,6}\s+', section) and i + 1 < len(sections):
            section = section + sections[i + 1]
            i += 2
        else:
            i += 1

        if len(current_chunk) + len(section) > max_chunk_size and current_chunk:
            chunks.append(ChunkInfo(
                index=index,
                start_char=current_start,
                end_char=current_start + len(current_chunk),
                content=current_chunk,
                token_estimate=len(current_chunk) // 4
            ))
            index += 1
            current_start = current_start + len(current_chunk)
            current_chunk = section
        else:
            current_chunk += section

    if current_chunk.strip():
        chunks.append(ChunkInfo(
            index=index,
            start_char=current_start,
            end_char=current_start + len(current_chunk),
            content=current_chunk,
            token_estimate=len(current_chunk) // 4
        ))

    return chunks


def estimate_tokens(text: str) -> int:
    """Rough token count estimate (avg 4 chars per token)."""
    return len(text) // 4
