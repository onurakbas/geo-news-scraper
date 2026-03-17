"""
Text cleaning utilities used by spiders and the NLP pipeline.

clean_text()     – strips HTML tags, collapses whitespace, removes boilerplate.
clean_html()     – strips tags only, keeps normalised plain text.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

# Boilerplate patterns common on Turkish news sites
_BOILERPLATE_PATTERNS: list[re.Pattern] = [
    re.compile(r"(haber(i)?\s+için\s+tıklayın.*)", re.IGNORECASE),
    re.compile(r"(bu\s+haberi\s+paylaş.*)", re.IGNORECASE),
    re.compile(r"(yorumlar.*)", re.IGNORECASE | re.DOTALL),
    re.compile(r"\s{2,}", re.UNICODE),  # collapse multiple spaces
]


def clean_html(html: str) -> str:
    """Strip HTML tags and return plain text."""
    soup = BeautifulSoup(html, "lxml")
    # Remove script, style, nav, footer noise
    for tag in soup(["script", "style", "nav", "footer", "aside", "form"]):
        tag.decompose()
    return soup.get_text(separator=" ")


def clean_text(text: str) -> str:
    """Normalise plain text: strip HTML if present, collapse whitespace."""
    if not text:
        return ""

    # Strip any residual HTML
    if "<" in text and ">" in text:
        text = clean_html(text)

    # Apply boilerplate removals (all except the last which is a substitution)
    for pattern in _BOILERPLATE_PATTERNS[:-1]:
        text = pattern.sub("", text)

    # Collapse whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()
