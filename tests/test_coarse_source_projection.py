"""Offline provenance/address checks, never a model-quality certificate."""
from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path

from jsonschema import Draft202012Validator
import pytest

from app.evaluation import golden_coarse_source_projection as coarse
from app.evaluation import golden_explicit_source_projection as explicit
from app.evaluation import golden_semantic_sources as fine
from app.evaluation.golden_bounded_correction_requests import restore_generation
from app.evaluation.golden_contextual_requests import restore as restore_tables
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_role_clarity import RoleClarityReview, RoleClarityReviewWorkflow as Workflow
from app.evaluation.golden_stream_bridge import REVIEW_MODEL_TRANSPORT_ID, validate_request
from app.evaluation.role_qualification import frozen_cases


@pytest.fixture(scope="module")
def cases():
    return {row["key"]: Workflow.build_inputs(source) for row, source in frozen_cases()[0]}


def unpack(request):
    return explicit._unpack(request)[1]


def issue(ids):
    return dict(score=70, verdict="needs_revision", advisories=[], issue_resolutions=[],
        issues=[dict(block=3, severity="high", category="unsupported_comparison",
            source_ids=ids, explanation="Synthetic unsupported future claim.",
            suggested_correction="Remove the future extrapolation.")])


def test_all_fifteen_preserve_every_original_report_and_source(cases):
    assert len(cases) == 15
    for inputs in cases.values():
        original_input = deepcopy(inputs)
        base = Workflow.make_request(inputs)
        projected = coarse.project_request(inputs)
        assert inputs == original_input
        assert coarse.restore_request(projected, inputs) == base
        assert projected.messages[2] == base.messages[2]
        before, after = unpack(base), unpack(projected)
        # The only data changes are the address label and selectable directory.
        restored = deepcopy(after)
        restored["source_index"] = {
            ("evidence_by_id" if key == "table_rows_by_id" else key): value
            for key, value in restored["source_index"].items()}
        restored["source_roots"] = before["source_roots"]
        assert restored == before
        assert after["source_index"]["blocks"] == before["source_index"]["blocks"]
        # Independently restore tables, external snapshots and generation view
        # all the way to original JSON, not merely back to another projection.
        native = unpack(explicit.restore_request(base, inputs))
        native.pop("source_roots")
        native.pop("computed_evidence")
        native["deterministic_source_facts"] = json.loads(inputs.data_json)["deterministic_source_facts"]
        native = restore_tables(native)
        native["generation_facts"] = restore_generation(
            native.pop("generation_view"), native["facts_and_provenance"]["facts"])
        assert native == json.loads(inputs.data_json)
        assert projected.max_tokens == base.max_tokens and projected.timeout_s == base.timeout_s
        assert projected.temperature == base.temperature and projected.top_p == base.top_p
        assert projected.tools[0].name == base.tools[0].name
        assert validate_request(projected, transport_id=REVIEW_MODEL_TRANSPORT_ID) != validate_request(
            base, transport_id=REVIEW_MODEL_TRANSPORT_ID)


def test_every_available_source_family_resolves_to_exact_original_values(cases):
    for inputs in cases.values():
        old = fine.source_catalog(inputs, include_role_contrasts=True, computed_layout="statistic_series")
        manifest = coarse.source_catalog(inputs)
        rows = manifest["roots"]
        ids = [row["source_id"] for row in rows]
        assert ids == sorted(ids)
        assert len(ids) < len(old)
        expected_old = {number: entry for number, entry in old.items() if entry.key in coarse.ROOT_KEYS}
        assert {r["source_id"]: r["key"] for r in rows[:-1]} == {
            number: entry.key for number, entry in expected_old.items()}
        assert rows[-1]["source_id"] == max(old) + 1
        assert rows[-1]["key"] == coarse.FACTS_KEY
        resolved = coarse.resolve_refs(inputs, ids)
        previous = {ref["source_id"]: ref for ref in fine.resolve_refs(inputs, list(expected_old),
            include_role_contrasts=True, computed_layout="statistic_series")}
        raw = json.loads(inputs.data_json)
        for ref in resolved:
            expected = (raw["facts_and_provenance"] if ref["key"] == coarse.FACTS_KEY
                        else previous[ref["source_id"]]["value"])
            assert ref["value"] == expected
            assert ref["value_sha256"] == digest(compact(expected))
            assert ref["input_sha256"] == digest(inputs.data_json)
            assert ref["catalog_sha256"] == manifest["catalog_sha256"]
            assert ref["semantic_approval"] is False
        assert resolved[-1]["value"]["provenance"] == raw["facts_and_provenance"]["provenance"]
        assert coarse.resolve_refs(inputs, list(reversed(ids))) == list(reversed(resolved))
        # Mutation of returned JSON cannot modify later reads or original input.
        resolved[-1]["value"]["facts"].clear()
        assert coarse.resolve_refs(inputs, [ids[-1]])[0]["value"] == raw["facts_and_provenance"]


def test_full_pack_root_retains_fields_missing_from_generation_projection(cases):
    inputs = cases["observed:2"]
    roots = {row["key"]: row["source_id"] for row in coarse.source_catalog(inputs)["roots"]}
    full, generated = coarse.resolve_refs(inputs, [roots[coarse.FACTS_KEY], roots["generation/projection"]])
    match = full["value"]["facts"]["facts:recent_match:00"]
    assert all(field in match for field in (
        "game_version", "queue_id", "game_duration_seconds", "damage_share", "gold_share", "deaths_before_10"))
    assert "game_version" not in generated["value"]["matches"][0]
    assert full["value"]["source_sha256"] == json.loads(inputs.pack_json)["source_sha256"]


@pytest.mark.parametrize("bad", [True, False, 1.0, "1", None])
def test_non_integer_and_boolean_ids_are_rejected_without_coercion(cases, bad):
    inputs = cases["observed:2"]
    with pytest.raises(ValueError, match="must_be_integers"):
        coarse.resolve_refs(inputs, [bad])
    assert not Draft202012Validator(coarse.response_schema(inputs)).is_valid(issue([bad]))


def test_leaf_unknown_and_duplicate_ids_are_not_repaired(cases):
    inputs = cases["observed:2"]
    old = fine.source_catalog(inputs, include_role_contrasts=True, computed_layout="statistic_series")
    allowed = {r["source_id"] for r in coarse.source_catalog(inputs)["roots"]}
    schema = Draft202012Validator(coarse.response_schema(inputs))
    for number in set(old) - allowed | {0, -1, max(old) + 100}:
        raw = issue([number])
        before = deepcopy(raw)
        with pytest.raises(ValueError, match="not_citable"):
            coarse.resolve_refs(inputs, raw["issues"][0]["source_ids"])
        assert not schema.is_valid(raw)
        assert raw == before
    number = max(allowed)
    with pytest.raises(ValueError, match="duplicate"):
        coarse.resolve_refs(inputs, [number, number])
    assert not schema.is_valid(issue([number, number]))
    with pytest.raises(ValueError, match="must_be_integers"):
        coarse.resolve_refs(inputs, {number})


def test_dynamic_enum_changes_only_reference_constraints(cases):
    for inputs in cases.values():
        before = RoleClarityReview.model_json_schema()
        after = coarse.response_schema(inputs)
        allowed = [r["source_id"] for r in coarse.source_catalog(inputs)["roots"]]
        for name in ("Problem", "IssueResolution"):
            refs = after["$defs"][name]["properties"]["source_ids"]
            assert refs["items"].pop("enum") == allowed
            assert refs.pop("uniqueItems") is True
        assert after == before
        data = unpack(coarse.project_request(inputs))
        assert [r[0] for r in data["source_roots"]["roots"]] == allowed
        assert "legacy" not in data["source_roots"]
        assert not (set(map(int, data["source_index"]["table_rows_by_id"])) & set(allowed))


def test_wide_citation_is_not_semantic_approval(cases):
    inputs = cases["observed:2"]
    last = coarse.source_catalog(inputs)["roots"][-1]["source_id"]
    raw = issue([last])
    # Structurally legal citations do not attest to this false assertion.
    raw["issues"][0]["explanation"] = "The sample proves every future loss has less damage than every future win."
    assert Draft202012Validator(coarse.response_schema(inputs)).is_valid(raw)
    assert coarse.resolve_refs(inputs, [last])[0]["semantic_approval"] is False
    assert coarse.source_catalog(inputs)["semantic_approval"] is False
    assert raw["issues"][0]["source_ids"] == [last]


@pytest.mark.parametrize("changed", ["report", "source", "schema", "metadata", "policy", "other_input"])
def test_restore_rejects_changed_inputs_catalogs_and_contract(cases, changed):
    inputs = cases["observed:2"]
    request = coarse.project_request(inputs)
    if changed in ("report", "source"):
        header, data = explicit._unpack(request)
        if changed == "report":
            data["source_index"]["blocks"][0]["text"] = "Changed report."
        else:
            data["fact_tables"][0]["rows"][0][1][0] = None
        request = replace(request, messages=(request.messages[0], replace(request.messages[1],
            content=header + compact(data) + explicit.END), request.messages[2]))
    elif changed == "schema":
        request = replace(request, tools=(replace(request.tools[0], input_schema=RoleClarityReview.model_json_schema()),))
    elif changed == "metadata":
        request = replace(request, metadata={**request.metadata, "source_catalog_sha256": "0" * 64})
    elif changed == "policy":
        request = replace(request, messages=(replace(request.messages[0], content="Changed policy."), *request.messages[1:]))
    else:
        inputs = cases["observed:1"]
    with pytest.raises(ValueError, match="binding_mismatch"):
        coarse.restore_request(request, inputs)


def test_construction_needs_no_local_runs_or_provider(monkeypatch):
    original, original_text = Path.read_bytes, Path.read_text
    def check_path(path):
        parts = [part.lower() for part in path.parts]
        assert not any(parts[index:index + 2] == ["data", "runs"] for index in range(len(parts) - 1))
    def safe_read(path):
        check_path(path)
        return original(path)
    def safe_text(path, *args, **kwargs):
        check_path(path)
        return original_text(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_bytes", safe_read)
    monkeypatch.setattr(Path, "read_text", safe_text)
    # Frozen datasets and source contracts are repository-owned public inputs.
    inputs = Workflow.build_inputs(frozen_cases()[0][0][1])
    assert coarse.project_request(inputs).metadata["source_projection"] == coarse.VERSION
