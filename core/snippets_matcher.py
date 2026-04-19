"""Replace snippet triggers in transcribed text by their expansions.

Matching rules (to balance precision and naturalness):
  - Case-insensitive.
  - Trigger must be at word boundary (\b).
  - Longer triggers win (sorted by length desc so "firma larga" beats "firma").
  - Usage count incremented for matched snippets (drives Hub sort order).
"""
import re
from db.snippets import SnippetsDB


_cached_db: SnippetsDB | None = None


def _db() -> SnippetsDB:
    global _cached_db
    if _cached_db is None:
        _cached_db = SnippetsDB()
    return _cached_db


def apply(text: str) -> str:
    if not text:
        return text
    snippets = _db().list_all()
    if not snippets:
        return text

    # Sort by trigger length desc so "firma larga" is tried before "firma"
    snippets.sort(key=lambda s: -len(s["trigger"]))

    out = text
    matched_ids: list[int] = []
    for s in snippets:
        trig = s["trigger"]
        if not trig:
            continue
        pat = re.compile(r"\b" + re.escape(trig) + r"\b", re.IGNORECASE)
        new, n_subs = pat.subn(s["expansion"], out)
        if n_subs > 0:
            out = new
            matched_ids.append(s["id"])

    for sid in matched_ids:
        try:
            _db().increment_usage(sid)
        except Exception:
            pass

    return out
