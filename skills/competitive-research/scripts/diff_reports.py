#!/usr/bin/env python3
"""
Diff two report.json files to show how the recommendation shortlist moved.

Usage:
    python diff_reports.py --prev PREV/report.json --curr CURR/report.json

Answers the question a weekly reader actually has: "what is different from
last week?" — which features entered the shortlist, which fell off, which
climbed, and whose scores moved.

Input: two report.json files as documented in references/report-template.md.
Only `shortlist[]` (with `rank`, `name`, and optionally `scores` and `tag`)
and the top-level `run_date` / `mode` keys are read.

Output on stdout:

    # Shortlist movement: 2026-08-10 (full) -> 2026-08-17 (full)

    ## Entered the shortlist
      NEW  #3  Single sign-on (SAML)          RICE 1420  Fit 8

    ## Left the shortlist
      GONE     Public API v2                  (was #7 last run)

    ## Moved
      UP   #2  Bulk CSV import   was #6   (+4)   RICE 980 -> 1240   Fit 7 -> 8
      DOWN #9  Dark mode         was #4   (-5)   RICE 640 -> 610    Fit 6 -> 5

Comparing a quick-mode run against a full-mode run is called out in the
header, because a shorter shortlist makes items look like they "left" when
they were simply never scored. Exit code is always 0.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _textmatch import load_json, similarity  # noqa: E402

SAME_FEATURE_THRESHOLD = 0.65


def index_shortlist(report: dict) -> list:
    """Return shortlist entries as (rank, name, rice, fit, tag) tuples."""
    rows = []
    for item in report.get("shortlist", []):
        name = item.get("name")
        if not name:
            print("warning: skipping shortlist entry with no name", file=sys.stderr)
            continue
        scores = item.get("scores") or {}
        rows.append({
            "rank": item.get("rank"),
            "name": name,
            "rice": scores.get("rice"),
            "fit": scores.get("strategic_fit"),
            "tag": item.get("tag"),
        })
    return rows


def pair_up(prev_rows: list, curr_rows: list, threshold: float):
    """Match current entries to previous entries by fuzzy name.

    Returns (pairs, entered, left) where pairs is a list of (curr, prev).
    """
    matched_prev = set()
    pairs, entered = [], []

    for curr in curr_rows:
        winner_idx, winning_score = None, 0.0
        for idx, prev in enumerate(prev_rows):
            if idx in matched_prev:
                continue
            score = similarity(curr["name"], "", prev["name"], "")
            if score > winning_score:
                winner_idx, winning_score = idx, score
        if winning_score >= threshold:
            matched_prev.add(winner_idx)
            pairs.append((curr, prev_rows[winner_idx]))
        else:
            entered.append(curr)

    left = [p for idx, p in enumerate(prev_rows) if idx not in matched_prev]
    return pairs, entered, left


def fmt_score(prev_val, curr_val, label: str) -> str:
    """Render a score transition, or a single value when unchanged/missing."""
    if prev_val is None and curr_val is None:
        return ""
    if prev_val is None or prev_val == curr_val:
        return f"{label} {curr_val}"
    return f"{label} {prev_val} -> {curr_val}"


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--prev", required=True, help="Previous run's report.json")
    parser.add_argument("--curr", required=True, help="This run's report.json")
    parser.add_argument("--threshold", type=float, default=SAME_FEATURE_THRESHOLD,
                        help=f"Same-feature similarity cutoff (default: {SAME_FEATURE_THRESHOLD})")
    args = parser.parse_args()

    prev_path = Path(args.prev)
    curr = load_json(Path(args.curr))

    if not prev_path.exists():
        n = len(curr.get("shortlist", []))
        print(f"# No previous report at {prev_path} -- this is the first run.")
        print(f"# All {n} shortlisted features are new by definition.")
        return

    prev = load_json(prev_path)

    prev_mode = prev.get("mode", "full")
    curr_mode = curr.get("mode", "full")
    print(f"# Shortlist movement: {prev.get('run_date', 'unknown')} ({prev_mode})"
          f" -> {curr.get('run_date', 'unknown')} ({curr_mode})\n")
    if prev_mode != curr_mode:
        print("# WARNING: comparing runs of different modes. A quick run scores fewer")
        print("#          features, so 'Left the shortlist' below overstates real drops.")
        print("#          Treat rank moves as indicative only.\n")

    prev_rows = index_shortlist(prev)
    curr_rows = index_shortlist(curr)
    pairs, entered, left = pair_up(prev_rows, curr_rows, args.threshold)

    if entered:
        print("## Entered the shortlist")
        for row in sorted(entered, key=lambda r: r["rank"] or 999):
            scores = "  ".join(x for x in [fmt_score(None, row["rice"], "RICE"),
                                           fmt_score(None, row["fit"], "Fit")] if x)
            print(f"  NEW  #{row['rank']}  {row['name']}   {scores}")
        print()

    if left:
        print("## Left the shortlist")
        for row in sorted(left, key=lambda r: r["rank"] or 999):
            print(f"  GONE     {row['name']}   (was #{row['rank']} last run)")
        print("  ^ Check each against seen-features.jsonl: a feature marked shipped or")
        print("    wontfix left on purpose. Anything else leaving needs an explanation.")
        print()

    moved, held = [], []
    for curr_row, prev_row in pairs:
        ranks_known = curr_row["rank"] is not None and prev_row["rank"] is not None
        if ranks_known and curr_row["rank"] != prev_row["rank"]:
            moved.append((curr_row, prev_row))
        else:
            held.append((curr_row, prev_row))

    if moved:
        print("## Moved")
        for curr_row, prev_row in sorted(moved, key=lambda t: t[0]["rank"]):
            delta = prev_row["rank"] - curr_row["rank"]
            direction = "UP  " if delta > 0 else "DOWN"
            scores = "   ".join(x for x in [
                fmt_score(prev_row["rice"], curr_row["rice"], "RICE"),
                fmt_score(prev_row["fit"], curr_row["fit"], "Fit"),
            ] if x)
            print(f"  {direction} #{curr_row['rank']}  {curr_row['name']}   "
                  f"was #{prev_row['rank']}   ({delta:+d})   {scores}")
        print()

    if held:
        print("## Held rank")
        for curr_row, _ in sorted(held, key=lambda t: t[0]["rank"] or 999):
            print(f"  ==   #{curr_row['rank']}  {curr_row['name']}")
        print()

    if not (entered or left or moved):
        print("# Shortlist is unchanged from the previous run.")
        print("# That is itself a finding: either the market is quiet, or the analysis")
        print("# is not picking up new signal. Say which one in the report.")


if __name__ == "__main__":
    main()
