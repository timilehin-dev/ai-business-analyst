"""
Lexical retrieval (BM25).

Deliberately not vector-based: BM25 needs no embedding model, so retrieval
keeps working in air-gap mode, costs nothing, stays deterministic across
runs, and is reproducible in tests. Vector search can be layered on later
for semantic recall without changing this interface.
"""
import math
import re
from collections import Counter
from typing import Callable, List, Sequence, Tuple, TypeVar

T = TypeVar("T")

_TOKEN_RE = re.compile(r"[a-z0-9_]+")

_STOPWORDS = frozenset(
    """
    a an and any are as at be been being but by can could did do does for from
    had has have how i if in into is it its me my of on or our so than that the
    their them then there these they this to was we were what when where which
    who why will with would you your
    """.split()
)

# BM25 free parameters. k1 controls term-frequency saturation, b controls
# how strongly document length normalises the score.
_K1 = 1.5
_B = 0.75


def tokenize(text: str) -> List[str]:
    """Lowercase alphanumeric tokens with stopwords removed."""
    return [t for t in _TOKEN_RE.findall((text or "").lower()) if t not in _STOPWORDS]


def score_documents(
    query: str,
    documents: Sequence[T],
    key: Callable[[T], str],
    limit: int = 5,
    min_score: float = 0.0,
) -> List[Tuple[T, float]]:
    """
    Rank documents against a query using BM25.

    Args:
        query: the search text
        documents: candidate objects
        key: extracts the searchable text from a candidate
        limit: maximum results returned
        min_score: drop results at or below this score

    Returns:
        (document, score) pairs sorted by descending score.
    """
    query_terms = set(tokenize(query))
    if not query_terms or not documents:
        return []

    tokenized = [tokenize(key(doc)) for doc in documents]
    lengths = [len(tokens) for tokens in tokenized]
    total_docs = len(documents)
    avg_length = (sum(lengths) / total_docs) if total_docs else 0.0
    if avg_length == 0:
        return []

    doc_frequency = Counter()
    for tokens in tokenized:
        for term in query_terms.intersection(tokens):
            doc_frequency[term] += 1

    scored: List[Tuple[T, float]] = []
    for doc, tokens, length in zip(documents, tokenized, lengths):
        if not tokens:
            continue
        counts = Counter(tokens)
        score = 0.0
        for term in query_terms:
            term_freq = counts.get(term, 0)
            if not term_freq:
                continue
            # Robertson/Sparck-Jones IDF with the +1 shift that keeps it
            # non-negative for terms appearing in most documents.
            idf = math.log(
                1 + (total_docs - doc_frequency[term] + 0.5) / (doc_frequency[term] + 0.5)
            )
            denominator = term_freq + _K1 * (1 - _B + _B * length / avg_length)
            score += idf * (term_freq * (_K1 + 1)) / denominator
        if score > min_score:
            scored.append((doc, score))

    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:limit]


def snippet(text: str, query: str, width: int = 600) -> str:
    """
    Return the window of `text` most dense in query terms.

    Keeps prompt payloads small while preserving the part of a long
    document that actually matches the question.
    """
    text = text or ""
    if len(text) <= width:
        return text

    terms = set(tokenize(query))
    if not terms:
        return text[:width]

    best_start, best_hits = 0, -1
    step = max(width // 4, 1)
    for start in range(0, max(len(text) - width, 0) + 1, step):
        window_hits = sum(1 for t in tokenize(text[start : start + width]) if t in terms)
        if window_hits > best_hits:
            best_start, best_hits = start, window_hits

    prefix = "…" if best_start > 0 else ""
    suffix = "…" if best_start + width < len(text) else ""
    return f"{prefix}{text[best_start : best_start + width]}{suffix}"
