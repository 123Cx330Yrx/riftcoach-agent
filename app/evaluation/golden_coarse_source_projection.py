"""Offline coarse citation roots over the unchanged complete RoleClarity input.

Table row numbers remain data addresses. Only the separately listed whole-source
roots are selectable citations. This changes a prospective request contract, not
an old response, its meaning, any manifest or the live candidate. Root membership
proves provenance, never that a statement follows from the selected material.
"""
from copy import deepcopy
from dataclasses import replace

from app.evaluation import golden_explicit_source_projection as explicit
from app.evaluation import golden_semantic_sources as sources
from app.evaluation.golden_native_issues_review import budget_check, strict_json
from app.evaluation.golden_review_experiment import compact, digest
from app.evaluation.golden_review_source_catalog import SourceEntry, build_catalog
from app.evaluation.golden_role_clarity import RoleClarityReview, RoleClarityReviewWorkflow


VERSION = "native-coarse-source-projection-v1"
FACTS_KEY = "source/facts_and_provenance"
ROOT_KEYS = frozenset({
    "source/deterministic", "request/utterance", "generation/projection",
    "knowledge/inventory", "source/position", "source/external_bundle",
    "source/official_patch", "source/data_dragon", sources.COMPUTED_KEY,
})
ROW_ADDRESS = (
    "编号直接查询source_index.table_rows_by_id的显式键；"
    "这些编号仅作表行和computed成员地址，不是审查引用；")
OLD_ROOT_POLICY = "source_roots列真实来源编号与位置，编号存在不等于支持结论；"
ROOT_POLICY = (
    "source_roots只列可引用的完整来源根，source_ids只能选其中编号。"
    "根路径指复原后的完整输入；source/facts_and_provenance包含按事实表、"
    "出处表及external_fact_paths复原的全部facts、provenance和来源元数据。"
    "引用根存在或范围较宽不等于支持解释或修法，仍须核对每项断言；")


def _catalog(inputs):
    original = build_catalog(inputs)
    numbered = sources.source_catalog(
        inputs, include_role_contrasts=True, computed_layout="statistic_series")
    data = strict_json(inputs.data_json)
    # A complete supplied evidence document, not a newly certified fact. Reuse
    # the ordinary SourceEntry/SourceCatalog path and original-value check.
    facts = SourceEntry(FACTS_KEY, "source_declaration", ("facts_and_provenance",),
                        compact(data["facts_and_provenance"]))
    facts_id = max(numbered) + 1
    roots = {number: entry for number, entry in numbered.items() if entry.key in ROOT_KEYS}
    roots[facts_id] = facts
    manifest = dict(schema_version=VERSION, input_sha256=original.input_sha256,
        roots=[dict(source_id=number, **entry.metadata()) for number, entry in roots.items()],
        unavailable=list(original.unavailable), semantic_approval=False)
    manifest["catalog_sha256"] = digest(compact(manifest))
    catalog = replace(original, entries=(*original.entries, facts),
                      catalog_sha256=manifest["catalog_sha256"])
    return roots, facts_id, catalog, manifest


def source_catalog(inputs):
    """Return source-bound root metadata; IDs are local to this complete input."""
    return _catalog(inputs)[3]


def resolve_refs(inputs, ids):
    """Resolve only the caller's selected roots, without expanding/repairing IDs.

    Values and their hashes are exact original values (or the existing unchanged
    computed evidence). Every result retains semantic_approval=False.
    """
    roots, facts_id, catalog, manifest = _catalog(inputs)
    if not isinstance(ids, (list, tuple)) or any(type(number) is not int for number in ids):
        raise ValueError("coarse_source_ids_must_be_integers")
    if len(ids) != len(set(ids)):
        raise ValueError("coarse_source_ids_duplicate")
    if any(number not in roots for number in ids):
        raise ValueError("coarse_source_id_not_citable")
    old_ids = [number for number in ids if number != facts_id]
    original = {ref["source_id"]: ref for ref in sources.resolve_refs(
        inputs, old_ids, include_role_contrasts=True, computed_layout="statistic_series")}
    result = []
    for number in ids:
        entry = roots[number]
        if number == facts_id:
            value = catalog.resolve(inputs, FACTS_KEY, kind=entry.kind)
        else:
            value = original[number]["value"]
        if digest(compact(value)) != entry.metadata()["value_sha256"]:
            raise ValueError("coarse_source_value_mismatch")
        result.append(dict(source_id=number, **entry.metadata(), value=value,
            input_sha256=catalog.input_sha256, catalog_sha256=manifest["catalog_sha256"],
            semantic_approval=False))
    return result


def _schema(root_ids):
    schema = deepcopy(RoleClarityReview.model_json_schema())
    for name in ("Problem", "IssueResolution"):
        reference = schema["$defs"][name]["properties"]["source_ids"]
        if reference["items"] != {"type": "integer"}:
            raise ValueError("coarse_source_schema_changed")
        reference["items"]["enum"] = list(root_ids)
        reference["uniqueItems"] = True
    return schema


def response_schema(inputs):
    """Keep all issue/marker fields; restrict citations to this input's roots."""
    return _schema(_catalog(inputs)[0])


def _project(inputs, **kwargs):
    base = RoleClarityReviewWorkflow.make_request(inputs, **kwargs)
    editing = kwargs.get("accepted") is not None
    header, data = explicit._unpack(base)
    roots, _, _, manifest = _catalog(inputs)
    if not editing and (len(base.tools) != 1 or base.tools[0].input_schema != RoleClarityReview.model_json_schema()):
        raise ValueError("coarse_source_tool_contract_changed")
    policy = base.messages[0].content
    if policy.count(explicit.NEW_ADDRESS) != 1 or policy.count(OLD_ROOT_POLICY) != 1:
        raise ValueError("coarse_source_policy_changed")
    index = data["source_index"]
    if "table_rows_by_id" in index or "evidence_by_id" not in index:
        raise ValueError("coarse_source_address_conflict")
    data["source_index"] = {
        ("table_rows_by_id" if key == "evidence_by_id" else key): value
        for key, value in index.items()}
    data["source_roots"] = dict(schema_version=VERSION,
        catalog_sha256=manifest["catalog_sha256"],
        columns=["source_id", "key", "kind", "path", "json_span"],
        roots=[[number, entry.key, entry.kind, list(entry.path),
                list(entry.json_span) if entry.json_span else None]
               for number, entry in roots.items()],
        unavailable=manifest["unavailable"])
    projected = replace(base,
        tools=base.tools if editing else (replace(base.tools[0], input_schema=_schema(roots)),),
        messages=(replace(base.messages[0], content=policy.replace(explicit.NEW_ADDRESS, ROW_ADDRESS)
                          .replace(OLD_ROOT_POLICY, ROOT_POLICY)),
            replace(base.messages[1], content=header + compact(data) + explicit.END),
            base.messages[2]),
        metadata={**base.metadata, "source_projection": VERSION,
                  "source_catalog_sha256": manifest["catalog_sha256"]})
    return base, budget_check(projected)


def project_request(inputs, **kwargs):
    """Construct one offline initial/fresh review; no IO or workflow activation."""
    return _project(inputs, **kwargs)[1]


def restore_request(request, inputs, **kwargs):
    """Verify the entire source-bound projection before restoring the old request.

    This is an offline reversibility check, not a way to relabel old receipts or
    to send a coarse-root response through the old fine-root validator.
    """
    base, expected = _project(inputs, **kwargs)
    if request != expected:
        raise ValueError("coarse_source_request_binding_mismatch")
    return base
