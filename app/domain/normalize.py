"""Term normalization. Deliberately simple: no stemming, no synonyms.

"Java" != "JavaScript", "C" != "C++" != "C#", "public-speaking" != "public speaking".
"""


def normalize_term(term: str) -> str:
    """Lowercase, trim, and collapse internal whitespace runs to one space."""
    return " ".join(term.strip().lower().split())


def normalize_terms(terms) -> frozenset[str]:
    """Normalize an iterable of terms into a set, dropping empties."""
    return frozenset(t for t in (normalize_term(x) for x in terms) if t)
