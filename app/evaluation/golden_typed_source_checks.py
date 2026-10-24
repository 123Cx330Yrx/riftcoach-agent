"""Ordinary source checks outside the two specialized inference audits.

Checks locate and compare supplied values. They do not prove that a source
entails a prose claim, or turn supplied text into a trusted instruction.
"""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import math
import re
from typing import Literal

from pydantic import Field

from app.evaluation.golden_integrated_review import Strict
from app.evaluation.golden_review_source_catalog import Kind, build_catalog
from app.evaluation.golden_review_experiment import QuoteRef
from app.evaluation.golden_fact_candidate import NUMBER


class SourceRef(Strict):
    key: str = Field(min_length=1, max_length=160)
    kind: Kind
    path: list[str | int] = Field(max_length=12)


class SourceLiteral(Strict):
    source: SourceRef
    reported: str = Field(min_length=1, max_length=160)
    format: Literal["exact", "date", "timestamp", "percent", "tier", "rounded"]
    places: int | None = Field(ge=0, le=6)


class SourceCheck(Strict):
    quote_ref: QuoteRef
    kind: Literal["source_fact", "advice", "boundary"]
    disposition: Literal["supported", "unsupported", "ambiguous"]
    sources: list[SourceRef] = Field(max_length=12)
    literals: list[SourceLiteral] = Field(max_length=24)
    explanation: str = Field(min_length=1, max_length=500)


def render_literal(value, binding):
    fmt, places = binding.format, binding.places
    if fmt in ("rounded", "percent"):
        if places is None or type(value) not in (int, float) or not math.isfinite(value):
            raise ValueError("typed_literal_numeric_format_invalid")
        if fmt == "percent" and not 0 <= value <= 1:
            raise ValueError("typed_literal_ratio_invalid")
        number = Decimal(str(value)) * (100 if fmt == "percent" else 1)
        return format(number.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP), "f") + ("%" if fmt == "percent" else "")
    if places is not None:
        raise ValueError("typed_literal_unexpected_precision")
    if fmt in ("date", "timestamp"):
        if type(value) is not str:
            raise ValueError("typed_literal_timestamp_invalid")
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError("typed_literal_timestamp_invalid")
        parsed = parsed.astimezone(timezone.utc)
        return parsed.date().isoformat() if fmt == "date" else parsed.isoformat(timespec="seconds").replace("+00:00", "Z")
    if fmt == "tier":
        if type(value) is not int or value < 0:
            raise ValueError("typed_literal_tier_invalid")
        return f"T{value}"
    if type(value) not in (str, int, float):
        raise ValueError("typed_literal_scalar_required")
    if type(value) is float and not math.isfinite(value):
        raise ValueError("typed_literal_scalar_required")
    return str(value)


def validate_checks(checks, issues, verdict, inputs):
    catalog = build_catalog(inputs)
    ledger, seen = [], set()
    issue_quotes = {(i.quote_ref.block, inputs.source.resolve(i.quote_ref.model_dump())) for i in issues}
    for check in checks:
        quote = inputs.source.resolve(check.quote_ref.model_dump())
        identity = (check.quote_ref.block, quote)
        if identity in seen:
            raise ValueError("typed_source_check_duplicate")
        seen.add(identity)
        if quote.lstrip().startswith("#"):
            raise ValueError("typed_source_heading_requires_audit")
        if check.disposition != "supported" and (verdict == "pass" or identity not in issue_quotes):
            raise ValueError("typed_source_issue_required")
        if not check.sources and not check.literals and check.disposition == "supported":
            raise ValueError("typed_source_evidence_required")
        refs = [*check.sources, *(v.source for v in check.literals)]
        validate_refs(refs, inputs)
        intervals, values = [], []
        for literal in check.literals:
            value = catalog.resolve(inputs, literal.source.key,
                kind=literal.source.kind, path=literal.source.path)
            expected = render_literal(value, literal)
            occurrences = list(re.finditer(re.escape(literal.reported), quote))
            if not occurrences:
                raise ValueError("typed_literal_not_in_quote")
            matches = expected == literal.reported
            if not matches and check.disposition == "supported":
                raise ValueError("typed_literal_value_mismatch")
            intervals.extend((m.start(), m.end()) for m in occurrences)
            values.append(dict(source=literal.source.model_dump(), reported=literal.reported,
                expected=expected, matches=matches))
        if check.disposition == "supported":
            for number in NUMBER.finditer(quote):
                if not any(a <= number.start() and number.end() <= b for a, b in intervals):
                    raise ValueError("typed_source_number_unbound")
        ledger.append(dict(quote_ref=check.quote_ref.model_dump(),
            kind=check.kind, disposition=check.disposition, literals=values,
            sources=[r.model_dump() for r in check.sources], semantic_approval=False))
    return ledger


def validate_refs(refs, inputs, *, ordinary_only=True):
    catalog = build_catalog(inputs)
    for ref in refs:
        # Match results and numeric derived facts retain the existing
        # arithmetic/inference audit path, rather than escape via prose.
        if ordinary_only and ref.kind in ("match", "aggregate", "role_statistic", "generation_projection"):
            raise ValueError("typed_source_match_requires_audit")
        if ordinary_only and ref.kind == "position_context" and (not ref.path or ref.path[0] in ("observed", "unknown_position_games", "excluded_games")):
            raise ValueError("typed_source_match_requires_audit")
        catalog.resolve(inputs, ref.key, kind=ref.kind, path=ref.path)
