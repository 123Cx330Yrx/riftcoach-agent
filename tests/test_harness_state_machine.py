import unittest

from app.harness.models import HarnessConfig, RunManifest, RunStatus
from app.harness.state_machine import (
    IllegalTransitionError,
    StaleAttemptError,
    advance,
)


class HarnessStateMachineTests(unittest.TestCase):
    def setUp(self):
        self.manifest = RunManifest.new(
            run_id="review_state_machine",
            config=HarnessConfig(),
        )

    def test_happy_path_reaches_published_and_records_transitions(self):
        path = [
            RunStatus.FACTS_READY,
            RunStatus.KNOWLEDGE_READY,
            RunStatus.DRAFT_READY,
            RunStatus.EVALUATING,
            RunStatus.PASSED,
            RunStatus.PUBLISHED,
        ]

        for target in path:
            advance(self.manifest, target)

        self.assertEqual(RunStatus.PUBLISHED, self.manifest.status)
        self.assertEqual(len(path), len(self.manifest.transitions))
        self.assertEqual("created", self.manifest.transitions[0]["from"])
        self.assertEqual("facts_ready", self.manifest.transitions[0]["to"])
        self.assertEqual("published", self.manifest.transitions[-1]["to"])

    def test_illegal_jump_is_rejected_without_mutating_manifest(self):
        original_updated_at = self.manifest.updated_at

        with self.assertRaises(IllegalTransitionError):
            advance(self.manifest, RunStatus.PUBLISHED)

        self.assertEqual(RunStatus.CREATED, self.manifest.status)
        self.assertEqual([], self.manifest.transitions)
        self.assertEqual(original_updated_at, self.manifest.updated_at)

    def test_terminal_state_cannot_change(self):
        advance(self.manifest, RunStatus.REJECTED, reason="invalid summary")

        with self.assertRaises(IllegalTransitionError):
            advance(self.manifest, RunStatus.CREATED)

        self.assertEqual(RunStatus.REJECTED, self.manifest.status)
        self.assertEqual(1, len(self.manifest.transitions))

    def test_revision_starts_a_new_attempt_and_rejects_old_results(self):
        for target in (
            RunStatus.FACTS_READY,
            RunStatus.KNOWLEDGE_READY,
            RunStatus.DRAFT_READY,
            RunStatus.EVALUATING,
            RunStatus.NEEDS_REVISION,
        ):
            advance(self.manifest, target)

        advance(self.manifest, RunStatus.REVISING, attempt_id=0)

        self.assertEqual(1, self.manifest.attempt_id)
        self.assertEqual(1, self.manifest.revision_count)

        with self.assertRaises(StaleAttemptError):
            advance(
                self.manifest,
                RunStatus.RE_EVALUATING,
                attempt_id=0,
            )

        self.assertEqual(RunStatus.REVISING, self.manifest.status)
        self.assertEqual(6, len(self.manifest.transitions))

        advance(
            self.manifest,
            RunStatus.RE_EVALUATING,
            attempt_id=1,
        )
        self.assertEqual(RunStatus.RE_EVALUATING, self.manifest.status)

    def test_degraded_is_available_only_after_deterministic_facts_exist(self):
        with self.assertRaises(IllegalTransitionError):
            advance(self.manifest, RunStatus.DEGRADED)

        advance(self.manifest, RunStatus.FACTS_READY)
        advance(self.manifest, RunStatus.DEGRADED, reason="generator unavailable")

        self.assertEqual(RunStatus.DEGRADED, self.manifest.status)


if __name__ == "__main__":
    unittest.main()
