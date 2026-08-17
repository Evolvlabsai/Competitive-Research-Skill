#!/usr/bin/env python3
"""
Test suite for the competitive-research helper scripts.

Run from the repo root:

    python tests/test_scripts.py

Pure stdlib (unittest + subprocess), no pytest, no network. The scripts are
the only executable code in this plugin, so this is the whole regression net.

Two kinds of test here:

1.  Calibration tests on similarity(). The thresholds in dedupe_features.py
    (0.55/0.30) and the diff scripts (0.65) are tuned to the current
    0.65-name / 0.35-full-keyword weighting. If someone retunes the weights,
    these fail loudly instead of silently degrading every future run.

2.  End-to-end CLI tests. Each script is run as a subprocess against the
    fixtures, asserting on stdout and on the always-0 exit contract.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "skills" / "competitive-research" / "scripts"
FIXTURES = Path(__file__).resolve().parent / "fixtures"

sys.path.insert(0, str(SCRIPTS))
from _textmatch import keywords, normalize, similarity  # noqa: E402


def run_script(name, *args):
    """Run a script as a subprocess. Returns (exit_code, stdout, stderr)."""
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS / name), *args],
        capture_output=True, text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


class TestNormalize(unittest.TestCase):
    def test_lowercases_and_strips_punctuation(self):
        self.assertEqual(normalize("Single Sign-On (SAML)!"), "single sign on saml")

    def test_collapses_whitespace(self):
        self.assertEqual(normalize("  bulk   CSV\timport "), "bulk csv import")

    def test_empty_string(self):
        self.assertEqual(normalize(""), "")


class TestKeywords(unittest.TestCase):
    def test_drops_stopwords_and_short_words(self):
        self.assertEqual(keywords("support for the new API"), {"api"})

    def test_keeps_content_words(self):
        self.assertEqual(keywords("Bulk CSV import"), {"bulk", "csv", "import"})


class TestSimilarityCalibration(unittest.TestCase):
    """Guards the threshold constants against silent drift."""

    LIKELY = 0.55        # dedupe_features.py --likely-threshold
    POSSIBLE = 0.30      # dedupe_features.py --possible-threshold
    SAME_FEATURE = 0.65  # diff_snapshots.py / diff_reports.py
    RENAME_HINT = 0.40   # diff_snapshots.py RENAME_HINT_THRESHOLD

    def test_identical_names_score_one(self):
        self.assertAlmostEqual(similarity("Dark mode", "", "Dark mode", ""), 1.0)

    def test_restatement_clears_likely_threshold(self):
        score = similarity("Bulk CSV import", "Upload a CSV and map columns",
                           "Bulk import", "Import many records from a spreadsheet")
        self.assertGreaterEqual(score, self.LIKELY,
                                f"'Bulk CSV import' vs 'Bulk import' scored {score:.2f}")

    def test_synonym_rename_lands_in_possible_not_likely(self):
        """Documents a known limit: 'mode' vs 'theme' share no keywords.

        The caller resolves POSSIBLE matches semantically, so this is safe —
        but it must stay above POSSIBLE, or the rename would be missed entirely.
        """
        score = similarity("Dark mode", "User-selectable dark UI theme",
                           "Dark theme support", "Dark UI theme toggle")
        self.assertGreaterEqual(score, self.POSSIBLE, f"scored {score:.2f} — would be missed")
        self.assertLess(score, self.LIKELY, f"scored {score:.2f} — thresholds may have drifted")

    def test_distinct_features_stay_below_likely(self):
        score = similarity("Real-time collaboration", "Live cursors in shared docs",
                           "Real-time sync", "Background sync across devices")
        self.assertLess(score, self.LIKELY,
                        f"distinct features scored {score:.2f} — would be wrongly merged")

    def test_unrelated_features_stay_below_possible(self):
        score = similarity("Webhook delivery retries", "Exponential backoff",
                           "Dark theme support", "Dark UI theme toggle")
        self.assertLess(score, self.POSSIBLE,
                        f"unrelated features scored {score:.2f}")

    def test_rename_falls_in_the_hint_band(self):
        """'Dark mode' -> 'Dark theme' must be flagged, not merged, not split."""
        score = similarity("Dark mode", "", "Dark theme", "")
        self.assertGreaterEqual(score, self.RENAME_HINT,
                                f"scored {score:.2f} — rename would be missed entirely")
        self.assertLess(score, self.SAME_FEATURE,
                        f"scored {score:.2f} — would merge silently and hide a real ship")

    def test_sibling_features_stay_below_the_hint_band(self):
        """Two different features sharing a word must not even be hinted."""
        self.assertLess(similarity("Webhook triggers", "", "Webhook delivery retries", ""),
                        self.RENAME_HINT)

    def test_is_symmetric(self):
        a = similarity("Bulk CSV import", "x", "Bulk import", "y")
        b = similarity("Bulk import", "y", "Bulk CSV import", "x")
        self.assertAlmostEqual(a, b)


class TestDedupeFeatures(unittest.TestCase):
    def setUp(self):
        self.code, self.out, self.err = run_script(
            "dedupe_features.py",
            "--new", str(FIXTURES / "shortlist.json"),
            "--history", str(FIXTURES / "seen-features.jsonl"),
        )

    def test_exits_zero(self):
        self.assertEqual(self.code, 0, self.err)

    def test_warns_about_malformed_jsonl_without_crashing(self):
        self.assertIn("skipping malformed JSONL", self.err)

    def test_matches_restated_feature_as_likely(self):
        self.assertRegex(self.out, r'\[LIKELY MATCH\].*Bulk CSV import.*Bulk import')

    def test_matches_synonym_rename_as_possible(self):
        self.assertRegex(self.out, r'\[POSSIBLE MATCH\].*Dark mode.*Dark theme support')

    def test_surfaces_shipped_status_and_drop_action(self):
        line = next(l for l in self.out.splitlines() if "Dark mode" in l)
        self.assertIn("[status=shipped]", line)
        self.assertIn("DROP", line)

    def test_surfaces_rejected_status_as_revisited(self):
        line = next(l for l in self.out.splitlines() if "Real-time collaboration" in l)
        self.assertIn("[status=rejected]", line)
        self.assertIn("REVISITED", line)

    def test_unseen_feature_is_new(self):
        self.assertRegex(self.out, r'\[NEW\]\s+"Single sign-on \(SAML\)"')

    def test_empty_history_marks_everything_new(self):
        with tempfile.TemporaryDirectory() as tmp:
            empty = Path(tmp) / "empty.jsonl"
            empty.write_text("", encoding="utf-8")
            code, out, _ = run_script(
                "dedupe_features.py",
                "--new", str(FIXTURES / "shortlist.json"),
                "--history", str(empty),
            )
        self.assertEqual(code, 0)
        self.assertEqual(out.count("[NEW]"), 5)

    def test_missing_input_file_exits_nonzero(self):
        code, _, err = run_script(
            "dedupe_features.py",
            "--new", str(FIXTURES / "does-not-exist.json"),
            "--history", str(FIXTURES / "seen-features.jsonl"),
        )
        self.assertEqual(code, 1)
        self.assertIn("not found", err)


class TestDiffSnapshots(unittest.TestCase):
    def setUp(self):
        self.code, self.out, self.err = run_script(
            "diff_snapshots.py",
            "--prev", str(FIXTURES / "snapshot-prev.json"),
            "--curr", str(FIXTURES / "snapshot-curr.json"),
        )

    def test_exits_zero(self):
        self.assertEqual(self.code, 0, self.err)

    def test_detects_added_feature(self):
        self.assertIn("+ ADDED    Single sign-on (SAML)", self.out)

    def test_detects_removed_feature(self):
        self.assertIn("- REMOVED  Zapier integration", self.out)

    def test_flags_likely_rename_for_semantic_review(self):
        # "Dark mode" -> "Dark theme" scores too low to merge automatically,
        # so it must be flagged rather than reported as a ship plus a drop.
        self.assertRegex(self.out, r'\? RENAME\?\s+"Dark mode" -> "Dark theme"')

    def test_does_not_hint_a_rename_between_unrelated_changes(self):
        # SSO was genuinely shipped and Zapier genuinely dropped — not a rename.
        self.assertNotRegex(self.out, r'RENAME\?.*Zapier')
        self.assertNotRegex(self.out, r'RENAME\?.*SAML')

    def test_restatement_merges_silently(self):
        # "Bulk CSV import" is unchanged in both snapshots — no noise at all.
        self.assertNotIn("Bulk CSV import", self.out.split("## NEW COMPETITOR")[0])

    def test_detects_price_increase(self):
        self.assertIn("Pro: $29/mo -> $39/mo", self.out)

    def test_detects_new_tier(self):
        self.assertIn("NEW TIER  Enterprise", self.out)

    def test_flags_new_competitor(self):
        self.assertIn("NEW COMPETITOR: Nimbus", self.out)

    def test_flags_dropped_competitor(self):
        self.assertIn("DROPPED FROM TRACKING: Legacy Co", self.out)

    def test_unchanged_competitor_is_silent(self):
        # Bolt is identical in both snapshots and must not add noise.
        self.assertNotIn("## Bolt", self.out)

    def test_missing_previous_snapshot_is_first_run_not_an_error(self):
        code, out, _ = run_script(
            "diff_snapshots.py",
            "--prev", str(FIXTURES / "no-such-snapshot.json"),
            "--curr", str(FIXTURES / "snapshot-curr.json"),
        )
        self.assertEqual(code, 0)
        self.assertIn("first tracked run", out)

    def test_identical_snapshots_report_no_change(self):
        code, out, _ = run_script(
            "diff_snapshots.py",
            "--prev", str(FIXTURES / "snapshot-curr.json"),
            "--curr", str(FIXTURES / "snapshot-curr.json"),
        )
        self.assertEqual(code, 0)
        self.assertIn("No competitor changes detected", out)


class TestDiffReports(unittest.TestCase):
    def setUp(self):
        self.code, self.out, self.err = run_script(
            "diff_reports.py",
            "--prev", str(FIXTURES / "report-prev.json"),
            "--curr", str(FIXTURES / "report-curr.json"),
        )

    def test_exits_zero(self):
        self.assertEqual(self.code, 0, self.err)

    def test_lists_entered_features(self):
        self.assertRegex(self.out, r"NEW  #2  Single sign-on \(SAML\)")

    def test_lists_departed_features(self):
        self.assertIn("GONE     Public API v2", self.out)
        self.assertIn("(was #3 last run)", self.out)

    def test_reports_upward_movement_with_delta(self):
        line = next(l for l in self.out.splitlines() if "Bulk CSV import" in l)
        self.assertIn("UP", line)
        self.assertIn("was #4", line)
        self.assertIn("(+3)", line)

    def test_reports_downward_movement(self):
        line = next(l for l in self.out.splitlines() if "Email sequences" in l)
        self.assertIn("DOWN", line)
        self.assertIn("(-2)", line)

    def test_shows_score_transitions(self):
        self.assertIn("RICE 980 -> 1240", self.out)

    def test_unchanged_score_renders_once(self):
        line = next(l for l in self.out.splitlines() if "Email sequences" in l)
        self.assertIn("RICE 1500", line)
        self.assertNotIn("1500 -> 1500", line)

    def test_warns_when_comparing_quick_against_full(self):
        with tempfile.TemporaryDirectory() as tmp:
            quick = json.loads((FIXTURES / "report-curr.json").read_text(encoding="utf-8"))
            quick["mode"] = "quick"
            quick_path = Path(tmp) / "report.json"
            quick_path.write_text(json.dumps(quick), encoding="utf-8")
            code, out, _ = run_script(
                "diff_reports.py",
                "--prev", str(FIXTURES / "report-prev.json"),
                "--curr", str(quick_path),
            )
        self.assertEqual(code, 0)
        self.assertIn("WARNING: comparing runs of different modes", out)

    def test_missing_previous_report_is_first_run(self):
        code, out, _ = run_script(
            "diff_reports.py",
            "--prev", str(FIXTURES / "no-such-report.json"),
            "--curr", str(FIXTURES / "report-curr.json"),
        )
        self.assertEqual(code, 0)
        self.assertIn("first run", out)

    def test_identical_reports_report_no_change(self):
        code, out, _ = run_script(
            "diff_reports.py",
            "--prev", str(FIXTURES / "report-curr.json"),
            "--curr", str(FIXTURES / "report-curr.json"),
        )
        self.assertEqual(code, 0)
        self.assertIn("Shortlist is unchanged", out)


class TestPluginManifests(unittest.TestCase):
    """The manifests are the install contract — a typo breaks every user."""

    def test_plugin_json_has_required_fields(self):
        manifest = json.loads(
            (REPO_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        for field in ("name", "description", "version", "author", "repository"):
            self.assertIn(field, manifest)

    def test_marketplace_lists_the_plugin(self):
        marketplace = json.loads(
            (REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        names = [p["name"] for p in marketplace["plugins"]]
        self.assertIn("competitive-research", names)

    def test_marketplace_version_matches_plugin_version(self):
        plugin = json.loads(
            (REPO_ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        marketplace = json.loads(
            (REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
        entry = next(p for p in marketplace["plugins"]
                     if p["name"] == plugin["name"])
        self.assertEqual(entry["version"], plugin["version"],
                         "marketplace.json and plugin.json versions have drifted")

    def test_every_skill_has_frontmatter_name(self):
        for skill_md in (REPO_ROOT / "skills").glob("*/SKILL.md"):
            text = skill_md.read_text(encoding="utf-8")
            self.assertTrue(text.startswith("---"),
                            f"{skill_md.name} is missing YAML frontmatter")
            self.assertIn("name:", text.split("---")[1],
                          f"{skill_md} frontmatter has no name field")

    def test_scripts_are_referenced_with_plugin_root(self):
        """Relative script paths break at runtime — Claude is cd'd into the user's repo."""
        for skill_md in (REPO_ROOT / "skills").rglob("*.md"):
            text = skill_md.read_text(encoding="utf-8")
            for line in text.splitlines():
                if "scripts/" in line and ".py" in line and "python" in line:
                    self.assertIn("${CLAUDE_PLUGIN_ROOT}", line,
                                  f"{skill_md}: script invoked without "
                                  f"${{CLAUDE_PLUGIN_ROOT}}: {line.strip()}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
