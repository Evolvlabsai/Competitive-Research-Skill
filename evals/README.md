# Eval suite

Cases for `claude plugin eval`, which scores the plugin's behaviour on real prompts instead of just checking that its scripts run.

```bash
claude plugin eval .
claude plugin eval . --case trigger-*        # one group
claude plugin eval competitive-research      # installed plugin, with a no-plugin baseline arm
```

## Status: draft, never executed

`claude plugin eval` is in early access and was not enabled on the account this suite was written on, so **none of these cases have been run**. The layout follows the shape documented in `claude plugin eval --help` (`evals/**/prompt.md` plus `graders/*.md`), but the exact frontmatter and grader schema are unverified.

Before trusting a result from this suite, generate a known-good template and reconcile:

```bash
claude plugin eval init --bare scratch
```

If the generated shape differs, fix these cases to match. The suite is a starting point, not a passing baseline.

`tests/test_scripts.py` is the regression net that actually runs today.

## What each case is for

| Case | What it checks |
|---|---|
| `trigger-natural-language` | The skill fires on "what should we build next?" without the word "competitive" — the description is tuned for broad triggering, and this is the failure mode that makes the plugin feel broken. |
| `trigger-quick-mode` | "quick competitive check" selects quick mode, and the run says it was a quick run. |
| `no-fabricated-evidence` | Given a repo with no reachable competitor data, the run declines to invent user quotes and source URLs. The single most damaging failure this plugin can have. |
| `respects-shipped-status` | A feature marked `shipped` in `seen-features.jsonl` does not reappear in the shortlist. |
| `first-run-change-section` | On a first run, report section 3 says there is nothing to compare against rather than inventing movement. |

## Adding a case

One behaviour per case. Prefer checks that would catch a real regression in `SKILL.md` — the workflow is prompt code, and prompt code regresses silently. Graders should assert on the presence or absence of specific claims, not on style.
