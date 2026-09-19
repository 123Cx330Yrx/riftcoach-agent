"""Locate duplicate fields without accepting or rewriting provider output."""
import json

from app.evaluation.golden_evidence_scope_v5 import (
    collect_diagnostics as previous_diagnostics,
    normalize_json,
)


class _Pairs(list):
    pass


def collect_diagnostics(raw, report, pack):
    try:
        tree = json.loads(normalize_json(raw), object_pairs_hook=_Pairs)
    except (ValueError, TypeError):
        return previous_diagnostics(raw, report, pack)
    rows = []

    def visit(node, path):
        if isinstance(node, _Pairs):
            seen = set()
            for key, value in node:
                child = f"{path}.{key[:60]}"
                if key in seen:
                    rows.append({"path": child[:180], "codes": ["duplicate_json_field"]})
                seen.add(key)
                visit(value, child)
        elif isinstance(node, list):
            for index, value in enumerate(node):
                visit(value, f"{path}[{index}]")

    visit(tree, "$")
    # Do not flatten ambiguous objects with last-value-wins semantics.
    return rows or previous_diagnostics(raw, report, pack)
