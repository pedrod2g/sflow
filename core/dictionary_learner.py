"""Detect dictionary candidates from user corrections.

When the user edits a transcription, we diff the word-sets to find tokens
that appeared in the edited version but NOT in the original — likely proper
nouns or jargon that Whisper misheard. Filters out common words by length
and heuristics, then surfaces candidates to the user for approval.
"""
import os
import re
from config import DICTIONARY_PATH


# Very short or very common words — not worth adding to the vocabulary hint.
_STOPWORDS_ES = {
    "el", "la", "los", "las", "un", "una", "unos", "unas", "de", "del", "al",
    "y", "o", "u", "e", "a", "en", "por", "para", "con", "sin", "sobre", "bajo",
    "que", "qué", "como", "cómo", "cuando", "cuándo", "donde", "dónde",
    "pero", "sino", "si", "sí", "no", "mi", "tu", "su", "mis", "tus", "sus",
    "le", "les", "lo", "me", "te", "se", "nos", "os",
    "es", "son", "era", "eran", "fue", "fueron", "ha", "han", "he", "haber",
    "esto", "eso", "aquello", "esta", "este", "ese", "aquel",
    "muy", "más", "mas", "menos", "todo", "todos", "toda", "todas",
    "ya", "aún", "aun", "aunque", "porque", "mientras", "entonces",
}

_STOPWORDS_EN = {
    "the", "a", "an", "of", "to", "in", "on", "at", "by", "for", "with",
    "and", "or", "but", "not", "if", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "this", "that", "these", "those",
    "i", "you", "he", "she", "it", "we", "they", "my", "your", "his", "her",
    "its", "our", "their", "me", "him", "us", "them",
    "as", "so", "just", "very", "too", "also", "only", "all",
}

_ALL_STOP = _STOPWORDS_ES | _STOPWORDS_EN


def _tokenize(text: str) -> list[str]:
    # Extract word-like sequences, keep accented letters
    return re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ][A-Za-zÁÉÍÓÚÜÑáéíóúüñ\-']+", text or "")


def diff_candidates(original: str, edited: str) -> list[str]:
    """Words that appear in `edited` but not in `original`, filtered.

    Heuristics to filter noise:
      - skip length < 4
      - skip stopwords (ES + EN)
      - skip pure-lowercase common-looking words (keep capitalized = likely proper noun)
      - dedupe preserving order
    """
    orig_tokens = set(t.lower() for t in _tokenize(original))
    edited_tokens = _tokenize(edited)

    seen = set()
    candidates: list[str] = []
    for t in edited_tokens:
        lo = t.lower()
        if lo in orig_tokens:
            continue
        if lo in _ALL_STOP:
            continue
        if len(t) < 4:
            continue
        # Prefer capitalized words (proper nouns) or tokens with hyphen/apostrophe
        is_proper = t[0].isupper()
        has_special = "-" in t or "'" in t
        if not (is_proper or has_special):
            continue
        if lo in seen:
            continue
        seen.add(lo)
        candidates.append(t)
    return candidates


def add_to_dictionary(terms: list[str]):
    """Append terms to dictionary.txt, deduping against existing entries."""
    if not terms:
        return
    os.makedirs(os.path.dirname(DICTIONARY_PATH), exist_ok=True)
    existing: set[str] = set()
    if os.path.exists(DICTIONARY_PATH):
        with open(DICTIONARY_PATH) as f:
            for line in f:
                s = line.strip()
                if s and not s.startswith("#"):
                    existing.add(s.lower())
    new_terms = [t for t in terms if t.lower() not in existing]
    if not new_terms:
        return
    with open(DICTIONARY_PATH, "a") as f:
        if os.path.getsize(DICTIONARY_PATH) and not open(DICTIONARY_PATH).read().endswith("\n"):
            f.write("\n")
        for t in new_terms:
            f.write(t + "\n")
