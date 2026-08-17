---
name: competitive-research
description: Run a thorough weekly competitive feature analysis on the current codebase and produce a ranked, evidence-backed list of features the product is missing. Use this skill whenever the user asks for competitive research, competitor analysis, feature ideas, gap analysis, product roadmap input, "what are competitors doing," "what should we build next," "what features are we missing," weekly product strategy review, or anything similar — even when the user doesn't explicitly say the word "competitive." Also use it for tasks framed as "look at competitors and tell me what to build" or "help me figure out what to add to my product." Auto-discovers product identity, JTBDs, features, and constraints from the codebase, so it works zero-config.
---

# Competitive Research

A recurring product-management workflow that combines codebase introspection, web research, and structured frameworks (Jobs-to-be-Done, Kano, RICE) to produce a ranked list of features the product is missing.

This skill is intended to be run periodically — typically weekly. It maintains state in `./competitive-research/` so each run dedupes against prior ones and surfaces what's genuinely new since last time.

## How to use

The user just runs the skill. There is no required configuration. Auto-discover everything from the codebase. Only ask the user for input if a prior run wrote a `competitive-research/overrides.yaml` and they want to update it.

If the user wants to provide hints (target user, known competitors, strategic constraints, etc.) before running, point them at `/competitive-research:setup` — a sibling skill that walks them through the override questions interactively and writes the YAML file. They can also edit `./competitive-research/overrides.yaml` directly.

If the user wants to override auto-discovery, look for `./competitive-research/overrides.yaml` with any of these optional fields:

```yaml
product_name_override: ""
product_url_override: ""
target_user_override: ""
extra_known_competitors: []
strategic_constraints_override: ""
monorepo_scope: ""
```

Anything not in the file gets auto-discovered. This is the right default — pushing config files on the user defeats the point of the skill.

## Run modes

Two modes. Default to **full** unless the user's phrasing clearly asks for speed.

| | **full** (default) | **quick** |
|---|---|---|
| Trigger | anything else | "quick", "fast", "short", "just a check", "what changed" |
| Competitors (Phase 2) | 8–15, re-expanded via web search | top 5 from existing `competitors.yaml`, no re-expansion |
| Deep dive (Phase 3) | all 6 sub-sections | positioning, features, pricing, recent moves only — **skip voice-of-customer and integrations** |
| Scoring (Phase 6) | full candidate set | top 15 candidates only |
| Shortlist (Phase 8) | 10 | 5 |
| Runtime | 10–20 min | 3–5 min |

Quick mode is for the mid-week "did anything move?" check, not for roadmap planning. Two rules keep it honest:

- **Write `"mode": "quick"` into `report.json`.** `diff_reports.py` warns when comparing across modes, because a shorter shortlist makes features look like they dropped when they were never scored.
- **Say so in the report.** Open the executive summary with *"Quick run — 5 competitors, no user-review mining. Re-run in full before making roadmap decisions."* A quick run that reads like a full one is worse than no run.

Never skip Phase 0 in quick mode. Wrong product understanding invalidates everything downstream, and it is the cheapest phase.

## Persona

Act as a senior product manager + competitive intelligence analyst + product marketer rolled into one. Be specific, be skeptical, avoid consultant-speak. Every recommendation should pass the test: *"would a sharp PM find this specific and actionable, or roll their eyes?"*

The frameworks to apply (Christensen's Jobs-to-be-Done, Moore's positioning, Kano classification, Ulwick's outcome-driven innovation, RICE scoring) are detailed in `references/frameworks.md`. Read that file before scoring features in Phase 5.

## The workflow

The workflow has 8 phases. Print a one-paragraph plan first, then execute end-to-end without stopping for approval. Don't ask clarifying questions — the codebase is the source of truth.

### Phase 0 — Discover the product from the codebase

This is the single most important phase. Skipping it or doing it shallowly causes every later phase to fail. The detailed signal-by-signal guide is in `references/codebase-discovery.md`. Read that file before starting Phase 0 — it lists exact files to check, shell commands to run, and fallback rules for when signals are missing.

**Reuse check first.** Find the newest `./competitive-research/runs/*/product-dossier.md` and apply this rule by age:

- **Written today** — reuse silently. It is almost certainly from a `/competitive-research:preview` run minutes ago.
- **1–7 days old** — reuse, but say which run it came from and offer the alternative in one line: *"Reusing the product dossier from 2026-08-12 (5 days old). Say 'refresh the dossier' if the product has changed since."* Then continue without waiting.
- **Older than 7 days, or the codebase has moved a lot since** — regenerate. Products drift; a stale dossier quietly poisons every later phase.

Check `git log --oneline --since=<dossier date> | wc -l` as the drift signal. Dozens of commits since the dossier was written means regenerate regardless of age.

Same rule for `./competitive-research/competitors.yaml`. The preview skill exists so users can sanity-check Phase 0 + Phase 2 cheaply before the full analysis; honoring its output makes the round-trip fast.

The output of Phase 0 is `./competitive-research/runs/YYYY-MM-DD/product-dossier.md` containing:

- **Product name, one-liner, public URL, target user, pricing model**
- **Core JTBDs** (2–4 statements in Christensen form: *"When [situation], I want to [motivation], so I can [outcome]"*)
- **Canonical feature list** (granular bullets — not "import" but "bulk CSV import with column mapping")
- **Inferred strategic constraints** (3–6 bullets, each tagged with its evidence source)
- **Competitors mentioned in-repo**

### Phase 1 — Setup folders and load history

Create if missing:

```
./competitive-research/
  ├── runs/YYYY-MM-DD/
  │   ├── raw-notes/
  │   ├── evidence.md
  │   ├── product-dossier.md         # written in Phase 0
  │   ├── competitor-snapshot.json   # written in Phase 3
  │   ├── report.md
  │   └── report.json
  ├── history/
  │   ├── seen-features.jsonl  # append-only dedupe log
  │   ├── outcomes.jsonl       # status audit trail (written by :track)
  │   └── exports.jsonl        # export audit trail (written by :export)
  └── competitors.yaml         # persistent competitor list
```

Load `history/seen-features.jsonl` and `competitors.yaml` if they exist.

**Also locate the previous run.** Find the most recent `runs/*/` directory that is not today's. Record its path — Phase 3 and Phase 7 diff against it. If there isn't one, this is the first run: say so in the report rather than silently omitting the change sections.

### Phase 2 — Expand the competitive set

Start from the in-repo competitors (Phase 0). Then find more via web search. A competitor is anything the target user might hire instead — including indirect substitutes like spreadsheets or doing nothing.

Categories to find:
- **Direct** — same category, same buyer
- **Adjacent** — overlapping JTBD from a different angle
- **Indirect / substitutes** — what people use today instead
- **Emerging** — YC batches, Product Hunt launches in the last 6–12 months, recently funded startups

Search G2, Capterra, Product Hunt, "<category> alternatives to <biggest player>" queries, Reddit ("what do you use for X"), Hacker News "Show HN" archives, the YC company directory.

For each, capture: name, URL, one-liner, funding stage, rough pricing, approximate team/company size. Aim for 8–15 total. Save to `competitors.yaml`.

### Phase 3 — Deep dive per competitor

For each competitor, write a scratch file in `raw-notes/` covering:

1. **Positioning** — one-sentence self-description; who they explicitly target
2. **Feature inventory** — granular bullets, scraped from features/pricing/changelog pages
3. **Pricing & packaging** — tiers, prices, what's gated, trial terms, limits
4. **Recent moves** — last 3–6 months of changelog/blog/launches
5. **Voice of customer** — 10–20 review snippets from G2/Capterra/Reddit/X, tagged `[PRAISE]` or `[COMPLAINT]` with theme. Complaints are gold — they're the gaps to fill.
6. **Integrations & ecosystem** — what they plug into

Cite URLs for every claim. If a page is paywalled or signup-walled, skip rather than fabricate.

In quick mode, capture 1–4 and 6 only; skip voice-of-customer (5).

**Then write the snapshot.** After the raw notes, distill every competitor into `./competitive-research/runs/YYYY-MM-DD/competitor-snapshot.json`:

```json
{
  "run_date": "YYYY-MM-DD",
  "competitors": [
    {
      "name": "Acme",
      "url": "https://acme.com",
      "one_liner": "...",
      "positioning": "...",
      "features": ["Bulk CSV import", "Single sign-on (SAML)"],
      "pricing_tiers": [{"name": "Pro", "price_usd_month": 29, "notes": "per seat"}]
    }
  ]
}
```

Keep feature names **stable across runs** — reuse last run's exact wording when the feature is unchanged. The diff matches on these strings, so gratuitous rewording invents fake ships and fake drops.

**Then diff against the previous run's snapshot:**

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/competitive-research/scripts/diff_snapshots.py" \
  --prev ./competitive-research/runs/PREV-DATE/competitor-snapshot.json \
  --curr ./competitive-research/runs/YYYY-MM-DD/competitor-snapshot.json
```

This is the highest-value signal in the whole workflow: *a competitor shipping something this week* beats *a competitor having something*. Feed the output into Phase 5 classification and into report section 3.1.

Resolve every `? RENAME?` line yourself before reporting. If it is a rename, drop both the ADDED and REMOVED lines — reporting a rename as a new ship is the most likely way this diff misleads a reader. Treat `- REMOVED` with the same suspicion: a moved marketing page looks identical to a deprecation. Verify before calling it a retreat.

### Phase 4 — Build the feature matrix

One markdown table:
- Rows = every distinct feature across competitors + our product
- Columns = our product, then each competitor
- Cells = ✅ (present) / ❌ (absent) / 🟡 (partial, with one-line note)

Save in `report.md`.

### Phase 5 — Classify the gaps

Extract every feature we lack that at least one competitor has. Classify each through multiple lenses (full definitions in `references/frameworks.md`):

1. **Kano** — Must-Have / Performance / Delighter / Indifferent / Reverse
2. **JTBD fit** — which of our JTBDs does it advance? If none, be skeptical
3. **Buyer vs. user value** — payer, user, or both?
4. **Differentiation type** — (a) parity, (b) leapfrog on a dimension we lead, (c) new axis
5. **Moat** — copyable in a weekend? Or defensible via data/integrations/workflow lock-in?
6. **Buildability given our constraints** — cross-reference inferred strategic constraints and infrastructure shape

### Phase 6 — Score and rank

**RICE** (Reach × Impact × Confidence ÷ Effort) with explicit numbers and a one-line justification per dimension.

**Strategic Fit (1–10)** based on alignment with inferred constraints, whether it reinforces or dilutes positioning, and red-ocean (everyone shipping) vs. blue-ocean (everyone missing) dynamics.

Rank by RICE, then re-sort the top 15 by Strategic Fit for the final shortlist.

### Phase 7 — Dedupe and diff against prior runs

Two jobs: suppress what's already been suggested, and surface what moved.

If `history/seen-features.jsonl` has prior entries, run the dedupe script:

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/competitive-research/scripts/dedupe_features.py" \
  --new ./competitive-research/runs/YYYY-MM-DD/shortlist.json \
  --history ./competitive-research/history/seen-features.jsonl
```

Write `shortlist.json` first (the Phase 6 ranked features as the JSON array shape documented in the script's docstring), then invoke. `${CLAUDE_PLUGIN_ROOT}` resolves to this plugin's install directory regardless of where the user installed it from.

The script does string-level matching and outputs likely matches, each annotated with the history entry's `status` and the action that status implies. For each candidate match, make a final semantic call yourself ("dark mode" and "dark theme support" are the same; "real-time sync" and "real-time collaboration" are not). The script's `-> action` hint assumes the match is real — if you judge it a false match, ignore the hint and treat the feature as `[NEW]`.

Read the `[POSSIBLE MATCH]` lines, don't skim past them. A pure synonym rename scores below the `[LIKELY MATCH]` threshold because the shared words collapse, so the most important matches often land in POSSIBLE.

**Apply outcome status filtering.** For every match against a historical entry, look up that entry's `status` field in `seen-features.jsonl`. Apply these rules before tagging:

- `status: shipped` or `status: wontfix` → **drop** the new candidate from the shortlist entirely. Don't re-suggest things the user already shipped or explicitly killed. Note in a comment why it was dropped.
- `status: in-progress` → **drop** from the shortlist; mention in the report's "Already in flight" sub-section: *"X is in progress (since [date]) — competitors [Y, Z] also have it now."*
- `status: rejected` → keep on the shortlist, tag `[REVISITED]`, and explain *what specifically changed* since the rejection (new competitor adoption, new user evidence, changed strategic constraint). Reference the original `rejection_reason` from the history entry.
- `status: unmarked` or absent → use the time-based logic below.

For unmarked matches:
- **`[NEW]`** — first time recommended (no historical match)
- **`[RECURRING — first suggested YYYY-MM-DD]`** — proposed before; note what's changed (e.g., "now 3 competitors ship it, up from 1")
- **`[REVISITED]`** — previously dismissed but circumstances changed; explain why

Append every newly shortlisted feature to `seen-features.jsonl` with date, name, normalized description, and scores. Do not set a `status` field — the user marks status via `/competitive-research:track`.

**Then diff the shortlist against last run's.** Write this run's `report.json` shortlist first (Phase 8 shape), then:

```bash
python "${CLAUDE_PLUGIN_ROOT}/skills/competitive-research/scripts/diff_reports.py" \
  --prev ./competitive-research/runs/PREV-DATE/report.json \
  --curr ./competitive-research/runs/YYYY-MM-DD/report.json
```

This produces report section 3.2. Every `GONE` line needs an explanation — a feature marked `shipped` or `wontfix` left on purpose, but anything else falling off the shortlist means the scoring moved, and the reader deserves to know why. "It dropped out" with no reason reads as inconsistency and costs trust in the whole report.

If the diff reports the shortlist unchanged, say which it is: a genuinely quiet week, or an analysis that isn't picking up new signal. Don't let an unchanged shortlist pass without comment.

### Phase 8 — Write the report

Write `./competitive-research/runs/YYYY-MM-DD/report.md` using the template in `references/report-template.md`.

The report has 9 sections; the template specifies what goes in each. Do not invent your own structure — the consistent format makes weekly reports comparable.

Section 3 ("What changed since the last run") is built from the two diffs: competitor movement from Phase 3's `diff_snapshots.py`, shortlist movement from Phase 7's `diff_reports.py`. On a first run, say so in one line and move on.

**Also write `report.json` alongside `report.md`.** The structured shortlist enables tooling integrations (`/competitive-research:export`, dashboards, longitudinal analysis). The JSON schema is documented at the bottom of `references/report-template.md`. Mirror the markdown shortlist exactly — same ranking, same scores, same evidence. JSON is the machine-readable view of the same content; never let them diverge. Set `"mode"` to `"full"` or `"quick"` to match how this run was executed.

## Quality bar (self-audit before delivering)

Before printing the TL;DR, check the report against this list. If any check fails, revise.

- [ ] Phase 0 dossier is grounded in actual file reads, not generic descriptions. Every claim about our product can be traced to a file or shell command.
- [ ] Every competitor claim has a source URL.
- [ ] Every feature recommendation has specific evidence — not "competitors generally have this."
- [ ] Top 10 is genuinely ranked. #1 is meaningfully better than #10, not a coin flip.
- [ ] At least 2 recommendations are non-obvious. Obvious suggestions are cheap; the value is in finding what the user would miss.
- [ ] "Don't build" section has at least 3 items. If everything looks worth building, you haven't been critical enough.
- [ ] No feature is recommended purely because a competitor has it. Each has an independent reason tied to JTBDs or positioning.
- [ ] Each top-10 entry references concrete files/modules in our codebase where the implementation would land. This is the unique value of running this from inside the repo.
- [ ] Section 3 is grounded in the two diff scripts, not in recollection. Every "competitor X shipped Y" traces to a `+ ADDED` line, and every `? RENAME?` was resolved before it reached the report.
- [ ] Every feature that left the shortlist has a stated reason.
- [ ] `report.json` `mode` matches how the run was actually executed, and a quick run says so in its first line.
- [ ] Writing is tight. Hedge words cut.

## Final output

Print to the chat:
1. The path to `report.md`
2. A 5-bullet TL;DR — lead with what changed since the last run, not with the highest-ranked feature. The rank is in the report; the change is why they ran it again.
3. Any overrides the user should consider setting in `./competitive-research/overrides.yaml` before next week's run (e.g., "I inferred your target user is solo founders on Shopify — confirm or correct in `target_user_override`")
4. One line pointing at the next step: *"Run `/competitive-research:export` to turn the shortlist into GitHub issues, or `/competitive-research:track` to mark what you decided."*
