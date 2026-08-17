# Competitive Research Skill for Claude Code

A weekly competitive analysis workflow that auto-discovers your product from
its codebase, researches competitors on the web, and produces a ranked,
evidence-backed list of features you're missing — scored with PM frameworks
(Jobs-to-be-Done, Kano, RICE) and deduped against prior weeks.

Zero-config: drop the skill in, run it from your repo, get a report. No
filling out forms.

---

## What you get

Every run produces a `report.md` with:

1. **Executive summary** — the 3–5 most important findings
2. **Product dossier** — what the skill inferred about your product (so you can correct it if wrong)
3. **What changed since the last run** — which competitors shipped what this week, which recommendations entered or left your shortlist, and why
4. **Feature matrix** — a ✅/❌/🟡 table across you and 8–15 competitors
5. **Top 10 feature recommendations** — each with RICE scoring, evidence quotes from real users, and specific files/modules in *your* codebase where the work would land
6. **"Don't build" list** — features competitors have that you should deliberately skip
7. **Non-feature observations** — pricing, positioning, and messaging shifts
8. **Sources** — every claim traceable to a URL

State persists across runs in `./competitive-research/`, so each week dedupes against the last and surfaces what's genuinely new.

---

## Prerequisites

- **Claude Code** installed and working — see [the official installation guide](https://docs.claude.com/en/docs/claude-code/overview) if you don't have it yet
- **Python 3.7+** for the dedupe and diff scripts (almost certainly already installed)
- **`gh` CLI** (optional but recommended) for richer git/issue/PR signals, and required for `/competitive-research:export` to create GitHub issues — [install instructions](https://cli.github.com/)
- **`tokei` or `cloc`** (optional) for repo size metrics

---

## Installation

This is a **Claude Code plugin**. Install it via the marketplace flow or directly from a local clone.

### Option A — Install from this GitHub repo (recommended)

Inside Claude Code:

```
/plugin marketplace add Evolvlabsai/Competitive-Research-Skill
/plugin install competitive-research@Competitive-Research-Skill
```

The first command registers this repo as a marketplace; the second installs the plugin from it. Claude Code resolves the plugin name (`competitive-research`) from `.claude-plugin/plugin.json`.

### Option B — Local development install

If you cloned this repo and want to test or hack on it locally:

```bash
git clone https://github.com/Evolvlabsai/Competitive-Research-Skill.git
cd Competitive-Research-Skill
```

Then in Claude Code:

```
/plugin marketplace add ./
/plugin install competitive-research@Competitive-Research-Skill
```

Edits to `skills/competitive-research/SKILL.md` and the references take effect on the next skill invocation — no reinstall needed.

### Verify the plugin loaded

```
/plugin
```

You should see `competitive-research` in the installed plugins list.

### What's in the plugin

Five skills, each invokable inside any project repo:

| Invocation | Purpose |
|---|---|
| *natural language* ("run the competitive research") or `/competitive-research:competitive-research` | The full 8-phase weekly analysis. The main event. |
| `/competitive-research:preview` | 1–2 minute sanity check — runs only Phase 0 (dossier) + Phase 2 (competitor list), then asks before doing the full deep dive. |
| `/competitive-research:setup` | Interactive walkthrough of the optional override questions (target user, known competitors, strategic constraints, monorepo scope). Writes `overrides.yaml`. |
| `/competitive-research:track` | Mark past recommendations as shipped / in-progress / rejected / wontfix. Future runs filter accordingly so you don't see the same suggestion next week. |
| `/competitive-research:export` | Turn the shortlist into GitHub issues, a Markdown checklist, or CSV. Skips anything already exported. |

The four slash-only skills (`preview`, `setup`, `track`, `export`) only fire on explicit invocation — they won't auto-trigger from natural language. The main analysis skill triggers broadly so you can ask for it conversationally.

### Full run vs. quick run

The analysis has two modes. Just ask for what you want:

| | **full** (default) | **quick** |
|---|---|---|
| Ask for it with | "run the competitive research" | "quick competitive check", "what changed this week?" |
| Competitors | 8–15, re-researched | top 5 from your existing list |
| User-review mining | yes | skipped |
| Shortlist length | 10 | 5 |
| Runtime | 10–20 min | 3–5 min |

Quick runs are for the mid-week "did anything move?" check. They mark themselves as quick in the report so you don't mistake one for a full analysis, and so the following week's diff knows not to compare them like-for-like.

---

## Usage

### First run

1. `cd` into your product's repo (or a monorepo subdirectory if scope C).
2. Open Claude Code.
3. Say something like:

   > Run the competitive research

   Or any of these — the skill is set to trigger broadly:
   - "What features are competitors shipping that we're not?"
   - "Do a gap analysis on my product"
   - "What should I build next quarter?"
   - "Run the weekly competitive review"

The first run takes the longest (typically 10–20 minutes of work) because it's discovering everything from scratch — your product identity, your features, your competitors. Subsequent runs are faster because state persists.

**Tip — preview before committing to a full run.** If you want to sanity-check the inferred product identity and competitor list before spending 15 minutes, run `/competitive-research:preview` first. It does only Phase 0 (dossier) and Phase 2 (competitor list), prints them, and asks before continuing. The full analysis afterwards reuses the dossier rather than redoing it.

### Weekly cadence

The skill is designed to run weekly. Each run:

- Re-discovers your codebase (catches new features you've shipped)
- Re-checks competitor changelogs and websites
- **Diffs against last week** — what competitors shipped, what moved on your shortlist
- Tags recommendations as `[NEW]`, `[RECURRING]`, or `[REVISITED]` based on prior runs
- Saves a fresh report under `./competitive-research/runs/YYYY-MM-DD/`

The second run is where this starts paying off. The first run has nothing to compare against, so section 3 of the report is empty by definition — from run two onward it leads with what actually changed.

You can run it manually each Monday morning, or automate it. A simple cron job:

```bash
# Run every Monday at 9am, write output to a log file
0 9 * * 1 cd /path/to/your/repo && claude -p "run the competitive research" > ~/competitive-research-$(date +%Y%m%d).log 2>&1
```

(Adjust the `claude -p` invocation to match your Claude Code version and shell. The point is: it's a regular CLI command, schedule it however you like.)

### What gets created in your repo

After the first run, you'll find:

```
your-repo/
└── competitive-research/                    # all skill output, gitignored by default
    ├── runs/
    │   └── 2026-04-24/
    │       ├── product-dossier.md           # what the skill thinks your product is
    │       ├── raw-notes/                   # one file per competitor, full notes
    │       ├── evidence.md                  # quotes, screenshots, pricing snapshots
    │       ├── competitor-snapshot.json     # this week's competitor state, diffed next week
    │       ├── report.md                    # ← the human deliverable
    │       └── report.json                  # structured shortlist for tooling integrations
    ├── history/
    │   ├── seen-features.jsonl              # dedupe log + outcome status (shipped/rejected/etc)
    │   ├── outcomes.jsonl                   # append-only audit log of status changes
    │   └── exports.jsonl                    # append-only log of what was exported where
    ├── competitors.yaml                     # persistent competitor list
    └── overrides.yaml                       # optional, only if you want to override discovery
```

You probably want to add `competitive-research/` to your `.gitignore` unless you specifically want this committed.

---

## Optional: overriding auto-discovery

If a run got something wrong about your product (e.g., it inferred the wrong target user), or if you want to seed the next run with hints up front, you have two ways to set overrides.

### Option 1 — Interactive setup (recommended)

Inside Claude Code, in your project repo:

```
/competitive-research:setup
```

This walks you through the optional questions one at a time (product name, URL, target user, extra competitors, strategic constraints, monorepo scope), shows you the diff before writing, and saves to `./competitive-research/overrides.yaml`. Skip any question to leave that field on auto-discovery. The setup skill only fires on this explicit slash invocation — it won't auto-trigger.

### Option 2 — Edit the YAML directly

Create or edit `./competitive-research/overrides.yaml`:

```yaml
# Anything blank gets auto-discovered. Only fill in what's wrong.
product_name_override: ""
product_url_override: ""
target_user_override: "solo founders running Shopify stores doing $10k–$100k/mo"
extra_known_competitors:
  - "Klaviyo — https://klaviyo.com"
  - "Postscript — https://postscript.io"
strategic_constraints_override: |
  - We're a 2-person team, no enterprise features
  - AI features are a Q2 priority
monorepo_scope: ""
```

The analysis skill checks for this file every run. The end of each report flags inferences that the user might want to override, so you only fill in fields that the skill got wrong.

---

## Customization

The plugin is just files. Fork the repo (or clone it for local install per Option B above) and edit:

- **`skills/competitive-research/SKILL.md`** — change the workflow itself (e.g., add a phase, change the report format)
- **`skills/competitive-research/references/frameworks.md`** — adjust which PM frameworks get applied or how they're scored
- **`skills/competitive-research/references/codebase-discovery.md`** — add signals specific to your stack (e.g., "also check our `feature-flags.json`")
- **`skills/competitive-research/references/report-template.md`** — change the report structure
- **`skills/competitive-research/scripts/dedupe_features.py`** — tune the similarity thresholds for the dedupe pass
- **`skills/competitive-research/scripts/diff_snapshots.py`** — tune how competitor feature changes are detected between runs
- **`.claude-plugin/plugin.json`** — bump `version` when you publish a change

Run the test suite after editing any script:

```bash
python tests/test_scripts.py
```

It covers the three scripts end to end plus the similarity thresholds they share. The thresholds are calibrated against real fixtures — if you retune the weighting in `scripts/_textmatch.py`, these tests tell you what you broke.

If you customize, keep `SKILL.md` under ~500 lines — Claude Code uses progressive disclosure, where SKILL.md is always loaded but reference files only get read when the workflow points to them. Pushing detail into references keeps the skill efficient.

---

## Troubleshooting

**Plugin doesn't show up in `/plugin` list:**
- Make sure you ran both commands — `marketplace add` registers the source, `install` adds the plugin from it.
- Restart Claude Code if the marketplace was just added.
- Check `~/.claude/plugins/` for the install. If the marketplace add succeeded but install failed, look for errors in the Claude Code log.

**Skill triggers but immediately produces a generic answer:**
- Claude Code answered without consulting the skill body. Try a more specific phrase like "use the competitive-research skill to..." or invoke it explicitly with `/competitive-research:competitive-research`.
- Skills undertrigger on simple-sounding requests. Phrasing the ask as multi-step ("do a full competitive analysis and gap report") helps.

**Phase 0 produces a wrong product description:**
- Open the latest `runs/YYYY-MM-DD/product-dossier.md` to see exactly what was inferred and from which sources.
- Set the relevant override in `./competitive-research/overrides.yaml` and rerun.

**Web research is shallow / few competitors found:**
- This usually means the product category was hard to identify from the codebase alone. Set `extra_known_competitors` in `overrides.yaml` to seed the search with 2–3 competitors you know about.

**Section 3 says a competitor "shipped" something they've always had:**
- Almost always a wording change in `competitor-snapshot.json` between runs, not a real ship. The diff matches on feature strings, so renaming "Bulk CSV import" to "CSV bulk importing" looks like a drop plus a ship.
- The script flags these as `? RENAME?` for Claude to resolve. If one slipped through, open the two `competitor-snapshot.json` files and compare the `features` arrays directly.

**Recommendations feel obvious / repetitive across weeks:**
- Check `history/seen-features.jsonl` — make sure entries from prior runs are actually being saved. The dedupe step relies on this file.
- The skill enforces "at least 2 non-obvious recommendations per report" as a quality check. If you're consistently getting obvious ones, the issue is usually that the inferred strategic constraints are too vague — add specific constraints via override.

**Dedupe script errors:**
- Run it manually to see the actual error. Find the install path with `ls ~/.claude/plugins/` and run:
  ```bash
  python ~/.claude/plugins/<install-dir>/skills/competitive-research/scripts/dedupe_features.py \
    --new shortlist.json \
    --history ./competitive-research/history/seen-features.jsonl
  ```
- Common cause: malformed JSONL line in the history file. Open it and remove the bad line.

---

## How it works (under the hood)

The plugin wraps a single skill that uses Claude Code's progressive disclosure pattern:

- **`skills/competitive-research/SKILL.md`** is loaded into context whenever the skill is triggered. It's a workflow skeleton with pointers.
- **`skills/competitive-research/references/*.md`** are loaded only when the workflow needs them — frameworks for scoring, the report template for writing, the codebase-discovery guide for Phase 0.
- **`skills/competitive-research/scripts/*.py`** run as subprocesses (via `${CLAUDE_PLUGIN_ROOT}`) for the deterministic steps: `dedupe_features.py` matches this week's shortlist against history, `diff_snapshots.py` finds what competitors shipped since last run, and `diff_reports.py` finds what moved on the shortlist. They share the matching logic in `_textmatch.py`.

The scripts are deliberately conservative. They surface candidates and flag ambiguous cases (`? RENAME?`, `[POSSIBLE MATCH]`) rather than guessing — Claude makes the semantic call, because a wrong automatic merge silently hides a competitor shipping something.

This keeps the always-on context small while making the deeper detail available when needed.

---

## Uninstalling

Inside Claude Code:

```
/plugin uninstall competitive-research
/plugin marketplace remove Competitive-Research-Skill
```

The plugin's runtime output (`./competitive-research/` in your project repos) is separate and is not removed by uninstalling. Delete it manually if you want.

---

## License & feedback

Use it however you want. If a phase consistently produces bad output, the most useful thing is to capture a real example (the prompt + the output you got + what you wanted) and edit the relevant `references/*.md` file directly. Skills are designed to be edited.
