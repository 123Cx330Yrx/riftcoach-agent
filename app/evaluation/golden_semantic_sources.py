"""Lossless whole-report sources with numbered root references.

The host verifies source identity, location and original values. A valid root
reference is not proof that its contents support a report sentence. No source
is selected on behalf of the reviewer and no Provider is called here.
"""
from app.evaluation.golden_bounded_correction_requests import source_data
from app.evaluation.golden_computed_evidence import build as computed_evidence
from app.evaluation.golden_contextual_requests import project
from app.evaluation.golden_review_source_catalog import build_catalog, SourceEntry
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_inference_scope_v5 import strict_json


ROOTS_VERSION = "semantic-source-roots-v2"
COMPUTED_KEY = "derived/computed_evidence"


def _statistic_series(evidence):
    """Transpose arithmetic rows without changing values or cohort membership."""
    columns = ["metric_index", "win_mean", "loss_mean", "all_pairs", "mean", "median", "missing_refs"]
    if evidence["columns"] != columns:
        raise ValueError("semantic_computed_columns_changed")
    result = {key: value for key, value in evidence.items() if key != "columns"}
    result.update(series_order="metrics", cohorts={})
    fields = ("win_mean", "loss_mean", "all_pairs", "cohort_mean", "cohort_median", "missing_refs")
    for name, group in evidence["cohorts"].items():
        rows = group["rows"]
        if len(rows) != len(evidence["metrics"]) or any(
                not isinstance(row, list) or len(row) != len(columns) or
                type(row[0]) is not int or row[0] != index
                for index, row in enumerate(rows, 1)):
            raise ValueError("semantic_computed_metric_order_changed")
        projected = {key: value for key, value in group.items() if key != "rows"}
        if any(field in projected for field in fields):
            raise ValueError("semantic_computed_series_collision")
        projected.update({field: [row[index] for row in rows]
                          for index, field in enumerate(fields, 1)})
        result["cohorts"][name] = projected
    return result


def _numbered(catalog, inputs):
    numbered = dict(enumerate(catalog.entries, 1))
    # Keep the existing evidence numbering rather than introducing a second
    # index for the same legacy roots. Extra roots follow in catalog order.
    for number, key in enumerate(inputs.source.evidence_keys, 1):
        entry = numbered.get(number)
        if entry is None or entry.legacy_ref != number or entry.key != "legacy/" + key:
            raise ValueError("semantic_source_legacy_numbering_changed")
    return numbered


def source_catalog(inputs, *, include_role_contrasts=False, computed_layout="rows"):
    """Map source IDs to immutable SourceEntry values after input checks.

    IDs are local to the complete input. Callers must bind review state to its
    input/catalog hash before reusing selections across request boundaries.
    """
    return _catalog(inputs, include_role_contrasts=include_role_contrasts,
                    computed_layout=computed_layout)[1]


def _catalog(inputs, *, include_role_contrasts=False, computed_layout="rows"):
    if computed_layout not in ("rows", "statistic_series"):
        raise ValueError("semantic_computed_layout_unknown")
    original = build_catalog(inputs)
    numbered = _numbered(original, inputs)
    calculated = computed_evidence(inputs, include_role_contrasts=include_role_contrasts)
    if computed_layout == "statistic_series":
        calculated = _statistic_series(calculated)
    numbered[len(numbered) + 1] = SourceEntry(COMPUTED_KEY, "computed_evidence",
        ("computed_evidence",), compact(calculated))
    identity = digest(compact(dict(version=ROOTS_VERSION,
        input_sha256=original.input_sha256, entries=[e.metadata() for e in numbered.values()])))
    return original, numbered, identity


def request_data(inputs, *, include_role_contrasts=False, computed_layout="rows"):
    """Project every original source once and append root/arithmetic navigation.

    Legacy IDs retain the existing evidence key list; extra root paths locate
    the original input or its embedded JSON. There is no leaf-value catalog.
    Source projection helpers independently verify exact reconstruction.
    ``statistic_series`` names each statistic and orders its values by metrics;
    the default ``rows`` layout preserves the existing catalog identity.
    """
    catalog, numbered, identity = _catalog(inputs, include_role_contrasts=include_role_contrasts,
                                         computed_layout=computed_layout)
    roots = catalog.prompt_index()
    roots.update(schema_version=ROOTS_VERSION, catalog_sha256=identity,
                 legacy_columns=["source_id", "kind"],
                 additional_columns=["source_id", "key", "kind", "path", "json_span"],
                 additional=[[number, entry.key, entry.kind, list(entry.path),
                              list(entry.json_span) if entry.json_span else None]
                             for number, entry in numbered.items() if entry.legacy_ref is None])
    data = project(source_data(inputs))
    data.update(source_roots=roots,
                computed_evidence=strict_json(numbered[len(numbered)].value_json))
    return data


def resolve_refs(inputs, ids, *, include_role_contrasts=False, computed_layout="rows"):
    """Resolve only explicitly selected IDs to original root values for audit.

    Reject unknown, duplicate and non-integer IDs, including bool. Returned
    values are independent copies. Missing metadata, null and empty containers
    are neither filled nor normalized. ``semantic_approval`` stays false.
    """
    catalog, numbered, identity = _catalog(inputs, include_role_contrasts=include_role_contrasts,
                                         computed_layout=computed_layout)
    if not isinstance(ids, (list, tuple)) or any(type(number) is not int for number in ids):
        raise ValueError("semantic_source_ids_must_be_integers")
    if len(ids) != len(set(ids)):
        raise ValueError("semantic_source_ids_duplicate")
    if any(number not in numbered for number in ids):
        raise ValueError("semantic_source_id_unknown")
    return [dict(source_id=number, **numbered[number].metadata(),
                 value=(strict_json(numbered[number].value_json)
                        if numbered[number].key == COMPUTED_KEY else
                        catalog.resolve(inputs, numbered[number].key, kind=numbered[number].kind)),
                 input_sha256=catalog.input_sha256, catalog_sha256=identity,
                 semantic_approval=False)
            for number in ids]
