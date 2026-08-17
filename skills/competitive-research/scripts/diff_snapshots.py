#!/usr/bin/env python3
"""
Diff two competitor snapshots to find what competitors shipped between runs.

Usage:
    python diff_snapshots.py --prev PREV/competitor-snapshot.json \
                             --curr CURR/competitor-snapshot.json

This is what makes the weekly cadence worth keeping. A single run tells you
what the market looks like; two runs tell you where it is moving. "Acme
shipped SSO this week" is a stronger roadmap signal than "Acme has SSO".

Input format (both files) — written by Phase 3:

{
  "run_date": "2026-08-17",
  "competitors": [
    {
      "name": "Acme",
      "url": "https://acme.com",
      "one_liner": "...",
      "positioning": "...",
      "features": ["Bulk CSV import", "Dark mode", "..."],
      "pricing_tiers": [
        {"name": "Pro", "price_usd_month": 29, "notes": "per seat"}
      ]
    }
  ]
}

Only `name` and `features` are required per competitor; everything else is
optional and simply skipped in the diff when absent.

Output: a human-readable delta report on stdout, grouped by competitor:

    ## Acme  (https://acme.com)
      + ADDED    Single sign-on (SAML)
      + ADDED    Dark theme
      - REMOVED  Zapier integration
      - REMOVED  Dark mode
      ~ PRICING  Pro: $29/mo -> $39/mo
      ? RENAME?  "Dark mode" -> "Dark theme" [score=0.46] — same feature
                 renamed, or a real drop plus a real ship?

    ## NEW COMPETITOR: Bolt  (https://bolt.dev)
      12 features tracked for the first time

Feature matching is fuzzy (see _textmatch.similarity), so restatements like
"Bulk CSV import" / "Bulk CSV importing" merge silently. Pure synonym renames
("mode" -> "theme") score too low to merge automatically, so they surface as
a RENAME? hint instead — the caller resolves those, the same way it resolves
dedupe_features.py matches. Automatic merging was rejected here because a
false merge silently hides a competitor shipping something.

Exit code is always 0 — a missing previous snapshot means "first run", not
an error.
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _textmatch import load_json, similarity  # noqa: E402

# Above this, two feature strings are treated as the same feature. Set higher
# than dedupe's 0.55 because here a false merge silently hides a real ship.
SAME_FEATURE_THRESHOLD = 0.65

# Between this and SAME_FEATURE_THRESHOLD, an added/removed pair is too close
# to be coincidence but too far to merge automatically — a pure synonym rename
# ("Dark mode" -> "Dark theme") lands here, because the shared-word overlap
# collapses even though the meaning is identical. Rather than silently merging
# (hiding a real ship) or silently splitting (inventing one), flag it and let
# the caller make the semantic call. Same division of labour as dedupe.
RENAME_HINT_THRESHOLD = 0.40


def competitors_by_name(snapshot: dict) -> dict:
    """Map normalized competitor name -> competitor dict."""
    out = {}
    for comp in snapshot.get("competitors", []):
        name = comp.get("name")
        if not name:
            print("warning: skipping competitor entry with no name", file=sys.stderr)
            continue
        out[name.strip().lower()] = comp
    return out


def diff_features(prev_features: list, curr_features: list,
                  threshold: float = SAME_FEATURE_THRESHOLD):
    """Return (added, removed) feature name lists, fuzzy-matched."""
    matched_prev = set()
    added = []
    for feat in curr_features:
        winner_idx, winning_score = None, 0.0
        for idx, prev_feat in enumerate(prev_features):
            if idx in matched_prev:
                continue
            score = similarity(feat, "", prev_feat, "")
            if score > winning_score:
                winner_idx, winning_score = idx, score
        if winning_score >= threshold:
            matched_prev.add(winner_idx)
        else:
            added.append(feat)

    removed = [f for idx, f in enumerate(prev_features) if idx not in matched_prev]
    return added, removed


def find_rename_hints(added: list, removed: list,
                      low: float = RENAME_HINT_THRESHOLD,
                      high: float = SAME_FEATURE_THRESHOLD):
    """Pair added/removed entries that look like renames rather than real moves.

    Returns a list of (removed_name, added_name, score). Each name appears in
    at most one hint, best score first, so a competitor renaming two features
    doesn't produce a cross-product of guesses.
    """
    candidates = []
    for old in removed:
        for new in added:
            score = similarity(old, "", new, "")
            if low <= score < high:
                candidates.append((score, old, new))

    candidates.sort(reverse=True)
    used_old, used_new, hints = set(), set(), []
    for score, old, new in candidates:
        if old in used_old or new in used_new:
            continue
        used_old.add(old)
        used_new.add(new)
        hints.append((old, new, score))
    return hints


def diff_pricing(prev_tiers: list, curr_tiers: list):
    """Return a list of human-readable pricing change strings."""
    def by_name(tiers):
        return {t.get("name", "").strip().lower(): t for t in tiers if t.get("name")}

    prev_by_name, curr_by_name = by_name(prev_tiers), by_name(curr_tiers)
    changes = []

    for name, curr_tier in curr_by_name.items():
        label = curr_tier.get("name", name)
        if name not in prev_by_name:
            changes.append(f"NEW TIER  {label}: {fmt_price(curr_tier)}")
            continue
        prev_price = prev_by_name[name].get("price_usd_month")
        curr_price = curr_tier.get("price_usd_month")
        if prev_price != curr_price:
            changes.append(
                f"PRICING   {label}: {fmt_price(prev_by_name[name])} -> {fmt_price(curr_tier)}"
            )

    for name, prev_tier in prev_by_name.items():
        if name not in curr_by_name:
            changes.append(f"DROPPED TIER  {prev_tier.get('name', name)}")

    return changes


def fmt_price(tier: dict) -> str:
    price = tier.get("price_usd_month")
    if price is None:
        return "unlisted"
    return f"${price}/mo"


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--prev", required=True,
                        help="Previous run's competitor-snapshot.json")
    parser.add_argument("--curr", required=True,
                        help="This run's competitor-snapshot.json")
    parser.add_argument("--threshold", type=float, default=SAME_FEATURE_THRESHOLD,
                        help=f"Same-feature similarity cutoff (default: {SAME_FEATURE_THRESHOLD})")
    args = parser.parse_args()

    prev_path = Path(args.prev)
    curr = load_json(Path(args.curr))

    if not prev_path.exists():
        n = len(curr.get("competitors", []))
        print(f"# No previous snapshot at {prev_path} -- this is the first tracked run.")
        print(f"# {n} competitors captured as the baseline. Nothing to diff yet.")
        return

    prev = load_json(prev_path)
    prev_comps = competitors_by_name(prev)
    curr_comps = competitors_by_name(curr)

    print(f"# Competitor movement: {prev.get('run_date', 'unknown')} "
          f"-> {curr.get('run_date', 'unknown')}\n")

    any_change = False

    for key, comp in curr_comps.items():
        name = comp.get("name")
        url = comp.get("url", "")
        header = f"## {name}" + (f"  ({url})" if url else "")

        if key not in prev_comps:
            any_change = True
            print(header.replace("## ", "## NEW COMPETITOR: "))
            print(f"  {len(comp.get('features', []))} features tracked for the first time\n")
            continue

        prev_comp = prev_comps[key]
        added, removed = diff_features(prev_comp.get("features", []),
                                       comp.get("features", []),
                                       threshold=args.threshold)
        pricing = diff_pricing(prev_comp.get("pricing_tiers", []),
                               comp.get("pricing_tiers", []))

        if not (added or removed or pricing):
            continue

        any_change = True
        print(header)
        for feat in added:
            print(f"  + ADDED    {feat}")
        for feat in removed:
            print(f"  - REMOVED  {feat}")
        for change in pricing:
            print(f"  ~ {change}")
        for old, new, score in find_rename_hints(added, removed,
                                                 high=args.threshold):
            print(f'  ? RENAME?  "{old}" -> "{new}" [score={score:.2f}] '
                  f"-- same feature renamed, or a real drop plus a real ship?")
        print()

    for key, comp in prev_comps.items():
        if key not in curr_comps:
            any_change = True
            print(f"## DROPPED FROM TRACKING: {comp.get('name')}")
            print("  Not in this run's competitor set -- confirm this was "
                  "intentional, not an oversight.\n")

    if not any_change:
        print("# No competitor changes detected since the previous snapshot.")

    print("\n# Notes:")
    print("# - ADDED is the highest-signal line here. A competitor shipping something")
    print("#   is stronger evidence than a competitor merely having it.")
    print("# - REMOVED often means a page moved or scraping failed, not a real")
    print("#   deprecation. Verify before reporting a removal as a strategic retreat.")
    print("# - RENAME? needs your semantic call. If it is a rename, drop BOTH the")
    print("#   ADDED and REMOVED lines above -- reporting a rename as a new ship is")
    print("#   the most likely way this diff misleads a reader.")


if __name__ == "__main__":
    main()
