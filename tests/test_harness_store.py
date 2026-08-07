import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from app.harness.models import ArtifactKind, HarnessConfig, RunManifest
from app.harness.store import ArtifactIntegrityError, FileRunStore


class FileRunStoreTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary_directory.cleanup)
        self.runs_root = Path(self.temporary_directory.name)
        self.manifest = RunManifest.new(
            run_id="review_example",
            config=HarnessConfig(),
        )
        self.store = FileRunStore(self.runs_root, self.manifest.run_id)

    def test_create_run_writes_a_readable_manifest(self):
        self.store.create_run(self.manifest)

        loaded = self.store.read_manifest()

        self.assertEqual(self.manifest.run_id, loaded.run_id)
        self.assertEqual(self.manifest.status, loaded.status)
        self.assertEqual(self.manifest.config, loaded.config)
        self.assertTrue((self.runs_root / "review_example" / "manifest.json").is_file())

    def test_write_artifact_registers_sha256_and_can_be_verified(self):
        self.store.create_run(self.manifest)
        content = '{"games_analyzed": 10}\n'

        record = self.store.write_artifact(
            kind=ArtifactKind.PLAYER_SUMMARY,
            relative_path="inputs/player_summary.json",
            content=content,
            schema_version="1.0",
            producer="facts",
        )

        expected_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
        self.assertEqual(expected_hash, record["sha256"])
        self.assertEqual(content.encode("utf-8"), self.store.read_artifact(record))

        loaded = self.store.read_manifest()
        self.assertEqual([record], loaded.artifacts)

    def test_read_artifact_rejects_content_changed_after_registration(self):
        self.store.create_run(self.manifest)
        record = self.store.write_artifact(
            kind=ArtifactKind.COACH_DRAFT,
            relative_path="drafts/coach_draft.md",
            content="original",
            schema_version="1.0",
            producer="generator",
        )
        artifact_path = self.store.run_directory / record["path"]
        artifact_path.write_text("tampered", encoding="utf-8")

        with self.assertRaises(ArtifactIntegrityError):
            self.store.read_artifact(record)

    def test_paths_cannot_escape_the_run_directory(self):
        self.store.create_run(self.manifest)

        for unsafe_path in ("../outside.txt", str(self.runs_root / "absolute.txt")):
            with self.subTest(path=unsafe_path):
                with self.assertRaises(ValueError):
                    self.store.write_artifact(
                        kind=ArtifactKind.COACH_DRAFT,
                        relative_path=unsafe_path,
                        content="unsafe",
                        schema_version="1.0",
                        producer="test",
                    )

    def test_store_normalizes_run_id_with_the_manifest_rule(self):
        store = FileRunStore(self.runs_root, "  review_normalized  ")

        self.assertEqual("review_normalized", store.run_id)
        self.assertEqual(
            self.runs_root / "review_normalized",
            store.run_directory,
        )

    def test_store_rejects_non_portable_or_unsafe_run_ids(self):
        for run_id in (
            "",
            "../outside",
            "folder/run",
            "folder\\run",
            "C:drive",
            "run with spaces",
            "NUL",
            "com1.log",
            "run.",
            "r" * 129,
        ):
            with self.subTest(run_id=run_id):
                with self.assertRaises(ValueError):
                    FileRunStore(self.runs_root, run_id)

    def test_artifact_paths_are_immutable_after_first_write(self):
        self.store.create_run(self.manifest)
        arguments = {
            "kind": ArtifactKind.COACH_DRAFT,
            "relative_path": "drafts/coach_draft.md",
            "schema_version": "1.0",
            "producer": "generator",
        }
        self.store.write_artifact(content="first version", **arguments)

        with self.assertRaises(FileExistsError):
            self.store.write_artifact(content="replacement", **arguments)

        loaded = self.store.read_manifest()
        self.assertEqual(1, len(loaded.artifacts))
        self.assertEqual(
            b"first version",
            self.store.read_artifact(loaded.artifacts[0]),
        )

    def test_failed_manifest_serialization_keeps_previous_manifest(self):
        self.store.create_run(self.manifest)
        manifest_path = self.store.run_directory / "manifest.json"
        previous_content = manifest_path.read_text(encoding="utf-8")
        self.manifest.artifacts.append({"not_json_serializable": object()})

        with self.assertRaises(TypeError):
            self.store.write_manifest(self.manifest)

        self.assertEqual(previous_content, manifest_path.read_text(encoding="utf-8"))
        self.assertEqual([], list(self.store.run_directory.glob(".manifest.*.tmp")))
        json.loads(previous_content)


if __name__ == "__main__":
    unittest.main()
