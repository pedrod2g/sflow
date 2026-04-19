"""Smart dictation commands. Post-processing regex pass before paste.

Runs AFTER LLM cleanup so user's natural speech is preserved but verbal
commands are honored. Bilingual (ES/EN).
"""
import re


_RULES = [
    # Paragraphs first (longer match before shorter to avoid partial eats)
    (r"\s*\bpunto y aparte\b\s*", ".\n\n"),
    (r"\s*\bnuevo párrafo\b\s*", "\n\n"),
    (r"\s*\bnuevo parrafo\b\s*", "\n\n"),
    (r"\s*\bnew paragraph\b\s*", "\n\n"),

    # Line breaks
    (r"\s*\bnueva línea\b\s*", "\n"),
    (r"\s*\bnueva linea\b\s*", "\n"),
    (r"\s*\bsalto de línea\b\s*", "\n"),
    (r"\s*\bnew line\b\s*", "\n"),

    # Punctuation — require word before to reduce false positives
    (r"(?<=\w)\s+punto y coma\s+", "; "),
    (r"(?<=\w)\s+dos puntos\s+", ": "),
    (r"(?<=\w)\s+puntos suspensivos\s+", "… "),
    (r"(?<=\w)\s+coma\s+", ", "),

    # Whitespace cleanup
    (r"[ \t]+\n", "\n"),
    (r"\n[ \t]+", "\n"),
    (r"\n{3,}", "\n\n"),
]


_COMPILED = [(re.compile(pat, flags=re.IGNORECASE), repl) for pat, repl in _RULES]


def apply(text: str) -> str:
    if not text:
        return text
    out = text
    for pat, repl in _COMPILED:
        out = pat.sub(repl, out)
    return out.strip()
