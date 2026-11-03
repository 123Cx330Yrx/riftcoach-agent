"""Offline typed addresses over the complete supplied review sources.

This does not change the legacy fact pack, index, validators or live workflow.
A typed address proves provenance and literal equality, never prose entailment.
Source text is retained as a declaration, not promoted to an observed fact.
"""
from dataclasses import dataclass
from typing import Literal

from app.evaluation.golden_contextual_sources import MARKER
from app.evaluation.golden_inference_scope_v5 import strict_json
from app.evaluation.golden_review_experiment import SourceIndex, compact, digest
from app.evidence.fusion import DataDragonSnapshot, OfficialPatchEvidence
from app.product.coach_positions import CoachPositionContext

CATALOG_VERSION = "golden-review-source-catalog-v1"
POSITION_MARKER = "Position context (sample facts and explicit goals, not instructions): "
Kind = Literal["match", "aggregate", "role_statistic", "request_scope",
    "sample_boundary", "source_declaration", "external_snapshot", "position_context",
    "knowledge", "knowledge_inventory", "official_patch", "static_catalog",
    "external_bundle", "user_request", "generation_projection", "computed_evidence"]


def at(value, path):
    """Typed path segments; no boolean/negative indices or implicit coercion."""
    for part in path:
        if isinstance(value, dict) and type(part) is str and part in value:
            value = value[part]
        elif isinstance(value, list) and type(part) is int and 0 <= part < len(value):
            value = value[part]
        else:
            raise ValueError("review_source_path_missing")
    return value


def marked(text, marker):
    matches, offset = [], 0
    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        if content.startswith(marker):
            start = offset + len(marker)
            matches.append((strict_json(content[len(marker):]), start, offset + len(content)))
        offset += len(line)
    if len(matches) > 1:
        raise ValueError("review_source_duplicate_marker")
    if not matches:
        return None
    value, start, end = matches[0]
    if not isinstance(value, dict):
        raise ValueError("review_source_object_required")
    return value, start, end


@dataclass(frozen=True)
class SourceEntry:
    key: str
    kind: Kind
    path: tuple[str | int, ...]
    value_json: str
    # For JSON embedded in original source text, retain exact character span.
    json_span: tuple[int, int] | None = None
    legacy_ref: int | None = None

    def metadata(self):
        return dict(key=self.key, kind=self.kind, path=list(self.path),
            json_span=list(self.json_span) if self.json_span else None,
            value_sha256=digest(self.value_json), legacy_ref=self.legacy_ref)


@dataclass(frozen=True)
class SourceCatalog:
    input_sha256: str
    catalog_sha256: str
    entries: tuple[SourceEntry, ...]
    unavailable: tuple[str, ...]

    def get(self, key):
        for row in self.entries:
            if row.key == key:
                return row
        raise ValueError("review_source_unknown_key")

    def resolve(self, inputs, key, *, kind: Kind, path=()):
        if digest(inputs.data_json) != self.input_sha256:
            raise ValueError("review_source_input_changed")
        row = self.get(key)
        if row.kind != kind:
            raise ValueError("review_source_kind_mismatch")
        data = strict_json(inputs.data_json)
        if row.json_span is None:
            actual = at(data, row.path)
        else:
            start, end = row.json_span
            actual = at(strict_json(data["deterministic_source_facts"][start:end]), row.path)
        if compact(actual) != row.value_json:
            raise ValueError("review_source_value_changed")
        return at(actual, path)

    def check_literal(self, inputs, key, *, kind: Kind, path, expected):
        actual = self.resolve(inputs, key, kind=kind, path=path)
        # Explicit null is not an omitted value. 0 is not False, nor 1 == True.
        if compact(actual) != compact(expected):
            raise ValueError("review_source_literal_mismatch")
        return dict(source=key, kind=kind, path=list(path), value=actual,
                    semantic_approval=False)

    def manifest(self):
        return dict(schema_version=CATALOG_VERSION, input_sha256=self.input_sha256,
            catalog_sha256=self.catalog_sha256, entries=[r.metadata() for r in self.entries],
            unavailable=list(self.unavailable), semantic_approval=False, live_qualified=False)

    def prompt_index(self):
        """Address navigation only; full hashes/provenance stay in the manifest.

        Legacy keys/values already exist in source_index and the source tables.
        Additional paths point into the original review data; json_span, when
        present, first parses that exact slice of deterministic_source_facts.
        No values, categories or limitations are dropped from the source data.
        """
        return dict(schema_version=CATALOG_VERSION, catalog_sha256=self.catalog_sha256,
            legacy_columns=["evidence_ref", "kind"],
            legacy=[[r.legacy_ref, r.kind] for r in self.entries if r.legacy_ref],
            additional_columns=["key", "kind", "path", "json_span"],
            additional=[[r.key, r.kind, list(r.path), list(r.json_span) if r.json_span else None]
                        for r in self.entries if r.legacy_ref is None],
            unavailable=list(self.unavailable))


def build_catalog(inputs):
    data = strict_json(inputs.data_json)
    pack = strict_json(inputs.pack_json)
    if data["facts_and_provenance"] != pack:
        raise ValueError("review_source_pack_mismatch")
    if (SourceIndex.build(inputs.source.report, pack) != inputs.source
            or data["source_index"] != inputs.source.prompt_sources()):
        raise ValueError("review_source_index_mismatch")
    entries, unavailable = [], []

    def add(key, kind, path, *, embedded=None, legacy_ref=None):
        if any(e.key == key for e in entries):
            raise ValueError("review_source_duplicate_key")
        root, span = (data, None) if embedded is None else (embedded[0], embedded[1:])
        entries.append(SourceEntry(key, kind, tuple(path), compact(at(root, path)), span, legacy_ref))

    for index, key in enumerate(inputs.source.evidence_keys, 1):
        if key.startswith("facts:recent_match:"): kind = "match"
        elif key.startswith("role:"): kind = "role_statistic"
        elif key.startswith("external:opgg:"): kind = "external_snapshot"
        elif key == "facts:recent_aggregate": kind = "aggregate"
        elif key == "facts:scope": kind = "request_scope"
        elif key == "facts:sample_boundaries": kind = "sample_boundary"
        elif key == "scope:limits": kind = "source_declaration"
        else: raise ValueError("review_source_unclassified_legacy_key")
        add("legacy/" + key, kind, ("facts_and_provenance", "facts", key), legacy_ref=index)

    # Complete non-indexed inputs stay visible. These addresses do not attest
    # the truth of user/source text or turn instructions inside it into policy.
    add("source/deterministic", "source_declaration", ("deterministic_source_facts",))
    add("request/utterance", "user_request", ("user_utterance",))
    add("generation/projection", "generation_projection", ("generation_facts",))
    add("knowledge/inventory", "knowledge_inventory", ("knowledge",))
    for i, row in enumerate(data["knowledge"]["citations"]):
        citation_id = row.get("citation_id")
        if not isinstance(citation_id, str) or not citation_id:
            raise ValueError("review_source_citation_identity_missing")
        add("knowledge/" + citation_id, "knowledge", ("knowledge", "citations", i))
    if not data["knowledge"]["citations"]:
        unavailable.append("knowledge_citations")

    text = data["deterministic_source_facts"]
    position = marked(text, POSITION_MARKER)
    if position is None:
        unavailable.append("position_context")
    else:
        CoachPositionContext.model_validate_json(compact(position[0]), strict=True)
        add("source/position", "position_context", (), embedded=position)
    external = marked(text, MARKER)
    if external is None:
        unavailable.extend(("external_bundle", "official_patch", "static_catalog"))
    else:
        add("source/external_bundle", "external_bundle", (), embedded=external)
        for field, kind, model in (("official_patch", "official_patch", OfficialPatchEvidence),
                                   ("data_dragon", "static_catalog", DataDragonSnapshot)):
            if external[0].get(field) is None:
                unavailable.append(kind)
                continue
            # Validate but retain original values/timezones; no normalized copies.
            model.model_validate_json(compact(external[0][field]), strict=True)
            add("source/" + field, kind, (field,), embedded=external)
    identity = dict(version=CATALOG_VERSION, input_sha256=digest(inputs.data_json),
                    entries=[e.metadata() for e in entries], unavailable=unavailable)
    return SourceCatalog(identity["input_sha256"], digest(compact(identity)),
                         tuple(entries), tuple(unavailable))
