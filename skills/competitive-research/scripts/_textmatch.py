#!/usr/bin/env python3
"""
Shared text-matching helpers for the competitive-research scripts.

Not a CLI. Imported by dedupe_features.py, diff_snapshots.py, and
diff_reports.py, which all need the same "are these two feature strings the
same idea?" judgement so their outputs agree with each other.

Pure stdlib. The weighting in similarity() is calibrated against the
thresholds in dedupe_features.py (0.55 likely / 0.30 possible) — changing
the weights means re-checking those defaults and the fixtures in tests/.
"""

import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

# Words that are too generic to count as evidence of a match
STOPWORDS = {
    "a", "an", "the", "and", "or", "of", "in", "on", "for", "to", "with",
    "support", "feature", "ability", "functionality", "system", "tool",
    "based", "new", "advanced", "basic", "simple", "full", "custom",
}


def normalize(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def keywords(text: str) -> set:
    """Extract content words from a feature name/description."""
    return {w for w in normalize(text).split() if w not in STOPWORDS and len(w) > 2}


def similarity(a_name: str, a_desc: str, b_name: str, b_desc: str) -> float:
    """Combined similarity score for two (name, description) pairs.

    We weight name overlap more than description overlap, because product
    feature names tend to be more diagnostic of identity ("dark mode" is the
    feature, "toggle for dark UI theme" is just one way to describe it).
    """
    # Name similarity: blend of string and keyword overlap
    name_str_sim = SequenceMatcher(None, normalize(a_name), normalize(b_name)).ratio()
    name_kw_a, name_kw_b = keywords(a_name), keywords(b_name)
    if name_kw_a and name_kw_b:
        name_kw_sim = len(name_kw_a & name_kw_b) / len(name_kw_a | name_kw_b)
    else:
        name_kw_sim = 0.0
    name_sim = 0.5 * name_str_sim + 0.5 * name_kw_sim

    # Combined keyword overlap across name + description (catches paraphrases)
    full_kw_a = keywords(f"{a_name} {a_desc}")
    full_kw_b = keywords(f"{b_name} {b_desc}")
    if full_kw_a and full_kw_b:
        full_kw_sim = len(full_kw_a & full_kw_b) / len(full_kw_a | full_kw_b)
    else:
        full_kw_sim = 0.0

    # Weight name similarity higher because it's more diagnostic
    return 0.65 * name_sim + 0.35 * full_kw_sim


def best_match(needle: str, haystack: list, key=lambda x: x):
    """Find the closest entry in haystack to needle. Returns (entry, score).

    `key` maps a haystack entry to the string it should be matched on, so
    callers can pass plain strings or dicts. Returns (None, 0.0) for an
    empty haystack.
    """
    winner, winning_score = None, 0.0
    for candidate in haystack:
        score = similarity(needle, "", key(candidate), "")
        if score > winning_score:
            winner, winning_score = candidate, score
    return winner, winning_score


def load_jsonl(path: Path) -> list:
    """Load a JSONL file. Returns empty list if missing."""
    if not path.exists():
        return []
    entries = []
    for line_num, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"warning: skipping malformed JSONL on line {line_num}: {e}",
                  file=sys.stderr)
    return entries


def load_json(path: Path):
    """Load a JSON file. Errors loudly if missing or unparseable."""
    if not path.exists():
        print(f"error: {path} not found", file=sys.stderr)
        sys.exit(1)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"error: {path} is not valid JSON: {e}", file=sys.stderr)
        sys.exit(1)
