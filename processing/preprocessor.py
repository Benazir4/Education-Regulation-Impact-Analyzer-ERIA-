"""
processing/preprocessor.py
Cleans and chunks regulation text for LLM processing.
"""

import re


MAX_CHUNK_CHARS = 25000  # Gemini Flash handles ~1M tokens, but we chunk for clarity


def clean_text(text: str) -> str:
    """Remove noise characters and normalize whitespace."""
    # Remove non-printable characters
    text = re.sub(r"[^\x20-\x7E\n\t\u0900-\u097F]", " ", text)
    # Normalize whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def remove_boilerplate(text: str) -> str:
    """Remove common website/PDF boilerplate text."""
    boilerplate_patterns = [
        r"©.*?(rights reserved|reserved).*?\n",
        r"(home\s*[>|/]\s*){1,}.*?\n",
        r"skip to (main )?content.*?\n",
        r"cookie(s)? policy.*?\n",
        r"(privacy|terms).{0,30}(policy|conditions).*?\n",
        r"page \d+ of \d+",
        r"^\s*\d+\s*$",  # Standalone page numbers
    ]
    for pattern in boilerplate_patterns:
        text = re.sub(pattern, "\n", text, flags=re.IGNORECASE | re.MULTILINE)
    return text.strip()


def chunk_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """
    Split text into chunks that respect paragraph boundaries.
    Used when document is very long (>25,000 chars).
    """
    if len(text) <= max_chars:
        return [text]

    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""

    for para in paragraphs:
        if len(current_chunk) + len(para) < max_chars:
            current_chunk += para + "\n\n"
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = para + "\n\n"

    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks


def preprocess(text: str) -> dict:
    """
    Full preprocessing pipeline.
    Returns cleaned text, chunk count, and character count.
    """
    text = clean_text(text)
    text = remove_boilerplate(text)
    chunks = chunk_text(text)

    return {
        "full_text": text,
        "chunks": chunks,
        "chunk_count": len(chunks),
        "char_count": len(text),
        "is_chunked": len(chunks) > 1,
    }
