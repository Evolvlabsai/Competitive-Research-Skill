Grade whether Phase 7 outcome-status filtering was applied correctly.

Re-suggesting something the user already shipped is the fastest way to make a recurring report feel worthless. The whole point of `/competitive-research:track` is to stop it.

## Required behaviour per status

- **`shipped` ("Bulk CSV import")** — absent from the shortlist. It is fine to mention it as already-covered parity in the feature matrix; it must not appear as a recommendation.
- **`wontfix` ("Dark mode")** — absent from the shortlist. The user explicitly killed it. Silently re-proposing it ignores a stated decision.
- **`rejected` ("Public API")** — may appear, but only tagged `[REVISITED]` **and** with a specific explanation of what changed since the rejection, referencing the original `rejection_reason` ("No integration partners asked for it yet"). "Competitors have it" is not a change — that was true when it was rejected.

## Fail

- Any of the three appearing as a plain `[NEW]` recommendation.
- `Public API` returning as `[REVISITED]` with no account of what actually changed.
- Dropping all three silently with no note anywhere that they were considered and filtered.

## Note on fuzzy matching

The competitor set may name these differently ("CSV upload", "dark theme", "REST API"). Matching on exact strings only, and therefore re-recommending a renamed variant, is a fail — resolving near-matches semantically is exactly what the workflow asks the model to do on top of the dedupe script's output.
