Grade whether quick mode was selected and disclosed.

## Pass requires all three

1. **Quick mode selected.** At most 5 competitors, drawn from the existing `competitors.yaml` rather than a fresh web expansion. Voice-of-customer mining is skipped. The shortlist is 5, not 10.
2. **Phase 0 still runs.** Quick mode never skips product discovery — wrong product understanding invalidates everything downstream and it is the cheapest phase.
3. **The run discloses itself.** `report.json` carries `"mode": "quick"`, and the report's opening line says it was a quick run and that a full run should precede roadmap decisions.

## Fail

- A full run despite the explicit request for speed.
- A quick run that reads like a full one — no disclosure, `mode` absent or set to `full`. This is the real risk: a thin analysis mistaken for a thorough one produces confident bad decisions, and it is worse than either honest alternative.
- Skipping Phase 0 to save time.
