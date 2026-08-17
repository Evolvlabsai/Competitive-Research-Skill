#!/usr/bin/env python3
"""
Dedupe new feature recommendations against the history file.

Usage:
    python dedupe_features.py --new shortlist.json --history seen-features.jsonl

The script does conservative string-based matching to surface candidate matches.
The skill's caller (Claude) makes the final semantic call — "dark mode" and
"dark theme support" are the same idea even though only some words overlap.

Input formats:

shortlist.json (the new run's shortlisted features):
[
    {"name": "Bulk CSV import", "description": "..."},
    {"name": "Dark mode", "description": "..."},
    ...
]

seen-features.jsonl (one JSON object per line). The optional `status` field is
written by /competitive-research:track:
{"date": "2026-04-17", "name": "...", "description": "...", "scores": {...}, "status": "shipped"}
{"date": "2026-04-17", "name": "...", "description": "...", "scores": {...}}
...

Output: prints to stdout a list of likely matches, one per line. Matches carry
the history entry's outcome status and the action it implies, so the caller
doesn't have to cross-reference the history file by hand:

    [LIKELY MATCH]   new: "Bulk CSV import" <-> history: "Bulk import" (2026-04-03) [score=0.56] [status=unmarked] -> tag RECURRING if the match is real
    [POSSIBLE MATCH] new: "Dark mode"       <-> history: "Dark theme support" (2026-04-10) [score=0.36] [status=shipped] -> DROP if the match is real
    [NEW]            "Workflow automation"

Note that a pure synonym rename ("mode" vs "theme") lands in POSSIBLE, not
LIKELY — shared-word overlap collapses even though the meaning is identical.
That is why POSSIBLE matches must be read, not skipped.

Exit code is always 0. The skill caller is expected to read this output
and make a final semantic decision per match — the `-> action` hint assumes
the string match is a real semantic match, which only the caller can confirm.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _textmatch import load_json, load_jsonl, similarity  # noqa: E402

# Status values that mean "never put this in front of the user again".
SUPPRESSED_STATUSES = {"shipped", "wontfix", "in-progress"}


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--new", required=True,
                        help="JSON file with new shortlisted features")
    parser.add_argument("--history", required=True,
                        help="JSONL file with previously suggested features")
    parser.add_argument("--likely-threshold", type=float, default=0.55,
                        help="Similarity above this is flagged [LIKELY MATCH] (default: 0.55)")
    parser.add_argument("--possible-threshold", type=float, default=0.30,
                        help="Similarity above this is flagged [POSSIBLE MATCH] (default: 0.30)")
    args = parser.parse_args()

    new_features = load_json(Path(args.new))
    history = load_jsonl(Path(args.history))

    if not history:
        print(f"# History file is empty or missing -- all {len(new_features)} features are NEW.\n")
        for feat in new_features:
            print(f'[NEW]            "{feat["name"]}"')
        return

    print(f"# Comparing {len(new_features)} new features against {len(history)} historical entries.\n")

    for new_feat in new_features:
        best_match = None
        best_score = 0.0
        for hist_feat in history:
            score = similarity(
                new_feat["name"], new_feat.get("description", ""),
                hist_feat["name"], hist_feat.get("description", ""),
            )
            if score > best_score:
                best_score = score
                best_match = hist_feat

        if best_score >= args.likely_threshold:
            label = "[LIKELY MATCH]  "
        elif best_score >= args.possible_threshold:
            label = "[POSSIBLE MATCH]"
        else:
            print(f'[NEW]            "{new_feat["name"]}"')
            continue

        status = best_match.get("status") or "unmarked"
        action = ("DROP if the match is real" if status in SUPPRESSED_STATUSES
                  else "tag REVISITED if the match is real" if status == "rejected"
                  else "tag RECURRING if the match is real")
        print(f'{label} new: "{new_feat["name"]}"  '
              f'<->  history: "{best_match["name"]}" '
              f'({best_match.get("date", "unknown date")}) '
              f'[score={best_score:.2f}] [status={status}] -> {action}')

    print("\n# Notes:")
    print("# - LIKELY MATCH and POSSIBLE MATCH need a final semantic call from you.")
    print("# - 'Dark mode' vs 'Dark theme support' = same idea (tag as RECURRING).")
    print("# - 'Real-time sync' vs 'Real-time collaboration' = different ideas (keep as NEW).")
    print("# - The '-> action' hint assumes the match is real. If you judge it a")
    print("#   false match, ignore the hint and treat the feature as NEW.")


if __name__ == "__main__":
    main()
