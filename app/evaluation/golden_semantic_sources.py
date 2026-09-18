"""Lossless whole-report sources with numbered root references.

The host verifies source identity, location and original values. A valid root
reference is not proof that its contents support a report sentence. No source
is selected on behalf of the reviewer and no Provider is called here.
"""
from app.evaluation.golden_bounded_correction_requests import source_data
from app.evaluation.golden_computed_evidence import build as computed_evidence
from app.evaluation.golden_contextual_requests import project
from app.evaluation.golden_review_source_catalog import build_catalog


ROOTS_VERSION = "semantic-source-roots-v1"


def _numbered(catalog, inputs):
    numbered = dict(enumerate(catalog.entries, 1))
    # Keep the existing evidence numbering rather than introducing a second
    # index for the same legacy roots. Extra roots follow in catalog order.
    for number, key in enumerate(inputs.source.evidence_keys, 1):
        entry = numbered.get(number)
        if entry is None or entry.legacy_ref != number or entry.key != "legacy/" + key:
            raise ValueError("semantic_source_legacy_numbering_changed")
    return numbered


def source_catalog(inputs):
    """Map source IDs to immutable SourceEntry values after input checks.

    IDs are local to the complete input. Callers must bind review state to its
    input/catalog hash before reusing selections across request boundaries.
    """
    return _numbered(build_catalog(inputs), inputs)


def request_data(inputs):
    """Project every original source once and append root/arithmetic navigation.

    Legacy IDs retain the existing evidence key list; extra root paths locate
    the original input or its embedded JSON. There is no leaf-value catalog.
    Source projection helpers independently verify exact reconstruction.
    """
    catalog = build_catalog(inputs)
    numbered = _numbered(catalog, inputs)
    roots = catalog.prompt_index()
    roots.update(schema_version=ROOTS_VERSION, legacy_columns=["source_id", "kind"],
                 additional_columns=["source_id", "key", "kind", "path", "json_span"],
                 additional=[[number, entry.key, entry.kind, list(entry.path),
                              list(entry.json_span) if entry.json_span else None]
                             for number, entry in numbered.items() if entry.legacy_ref is None])
    data = project(source_data(inputs))
    data.update(source_roots=roots, computed_evidence=computed_evidence(inputs))
    return data


def resolve_refs(inputs, ids):
    """Resolve only explicitly selected IDs to original root values for audit.

    Reject unknown, duplicate and non-integer IDs, including bool. Returned
    values are independent copies. Missing metadata, null and empty containers
    are neither filled nor normalized. ``semantic_approval`` stays false.
    """
    catalog = build_catalog(inputs)
    numbered = _numbered(catalog, inputs)
    if not isinstance(ids, (list, tuple)) or any(type(number) is not int for number in ids):
        raise ValueError("semantic_source_ids_must_be_integers")
    if len(ids) != len(set(ids)):
        raise ValueError("semantic_source_ids_duplicate")
    if any(number not in numbered for number in ids):
        raise ValueError("semantic_source_id_unknown")
    return [dict(source_id=number, **numbered[number].metadata(),
                 value=catalog.resolve(inputs, numbered[number].key, kind=numbered[number].kind),
                 input_sha256=catalog.input_sha256, catalog_sha256=catalog.catalog_sha256,
                 semantic_approval=False)
            for number in ids]
