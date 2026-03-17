"""
Embedding generation for news articles.

Uses a fixed sentence-transformers model to produce semantic vectors from
the concatenation of a news item's title and content.

Model is loaded once (singleton) to avoid reloading on every call.
"""

from __future__ import annotations

import re
from functools import lru_cache

import numpy as np
from loguru import logger
from sentence_transformers import SentenceTransformer

# Pinned model – must NOT change after embeddings are stored in MongoDB,
# because embeddings produced by different models are incompatible.
EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    """Load and cache the SentenceTransformer model (loaded once per process)."""
    logger.info(f"Loading embedding model: {EMBEDDING_MODEL_NAME}")
    model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    logger.info("Embedding model loaded successfully.")
    return model


def _prepare_text(title: str, content: str) -> str:
    """
    Build the text to embed from title + content.

    Title is weighted by repeating it – a common technique to give the title
    stronger influence on the final vector.
    """
    title = (title or "").strip()
    content = (content or "").strip()

    # Collapse excessive whitespace
    content = re.sub(r"\s+", " ", content)

    # Truncate content to first 512 words to keep inference fast
    words = content.split()
    if len(words) > 512:
        content = " ".join(words[:512])

    # Title repeated twice to boost its weight
    return f"{title} {title} {content}".strip()


def embed_text(title: str, content: str) -> list[float]:
    """
    Return a unit-normalised embedding vector for one news item.

    Args:
        title:   Article title.
        content: Article body (plain text, HTML already stripped).

    Returns:
        A list[float] suitable for storing in MongoDB.
    """
    model = _get_model()
    text = _prepare_text(title, content)
    vector: np.ndarray = model.encode(text, normalize_embeddings=True, convert_to_numpy=True)
    return vector.tolist()


def embed_batch(items: list[dict]) -> list[list[float]]:
    """
    Produce embeddings for a batch of news dicts (keys: 'title', 'content').

    Batching is significantly faster than calling embed_text() in a loop.

    Args:
        items: List of dicts with 'title' and 'content' keys.

    Returns:
        List of embedding vectors in the same order as `items`.
    """
    model = _get_model()
    texts = [_prepare_text(item.get("title", ""), item.get("content", "")) for item in items]
    vectors: np.ndarray = model.encode(texts, normalize_embeddings=True, show_progress_bar=True, convert_to_numpy=True)
    return [v.tolist() for v in vectors]
