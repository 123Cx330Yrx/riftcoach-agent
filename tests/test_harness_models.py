import unittest

from app.harness.models import (
    ArtifactKind,
    HarnessConfig,
    RunManifest,
    RunStatus,
)


class HarnessModelTests(unittest.TestCase):
    def test_terminal_statuses_are_explicit(self):
        self.assertTrue(RunStatus.PUBLISHED.is_terminal)
        self.assertTrue(RunStatus.DEGRADED.is_terminal)
        self.assertTrue(RunStatus.REJECTED.is_terminal)
        self.assertFalse(RunStatus.CREATED.is_terminal)
        self.assertFalse(RunStatus.EVALUATING.is_terminal)

    def test_artifact_kinds_cover_the_stage_two_pipeline(self):
        self.assertEqual("player_summary", ArtifactKind.PLAYER_SUMMARY.value)
        self.assertEqual("retrieval_evidence", ArtifactKind.RETRIEVAL_EVIDENCE.value)
        self.assertEqual("final_report", ArtifactKind.FINAL_REPORT.value)
        self.assertEqual("run_manifest", ArtifactKind.RUN_MANIFEST.value)

    def test_config_has_safe_bounded_defaults(self):
        config = HarnessConfig()

        self.assertEqual(85, config.publish_score_threshold)
        self.assertEqual(1, config.max_revisions)
        self.assertTrue(config.allow_deterministic_fallback)

    def test_config_rejects_unbounded_or_invalid_values(self):
        with self.assertRaises(ValueError):
            HarnessConfig(publish_score_threshold=101)

        with self.assertRaises(ValueError):
            HarnessConfig(max_revisions=-1)

        with self.assertRaises(ValueError):
            HarnessConfig(max_revisions=4)

    def test_new_manifest_starts_in_created_state(self):
        manifest = RunManifest.new(
            run_id="review_20260722_example",
            config=HarnessConfig(),
        )

        self.assertEqual("review_20260722_example", manifest.run_id)
        self.assertEqual(RunStatus.CREATED, manifest.status)
        self.assertEqual(0, manifest.revision_count)
        self.assertEqual(0, manifest.attempt_id)
        self.assertEqual([], manifest.artifacts)
        self.assertEqual([], manifest.transitions)


if __name__ == "__main__":
    unittest.main()
