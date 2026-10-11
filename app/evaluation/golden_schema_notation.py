"""Compact, constraint-preserving prompt notation; host JSON Schema stays intact.

Only the explicitly supported schema subset is rendered. Unknown keywords fail
closed rather than silently dropping a new validation constraint.
"""
from app.evaluation.golden_review_experiment import compact


LEGEND = ("Output one JSON object of type Result. Schema notation: Object{field:Type} "
          "forbids extra fields; every field is required unless marked ?. Array<T> "
          "contains T; | means union; quoted literals are exact enum values. "
          "Brackets contain unchanged JSON Schema constraints (lengths count "
          "characters/items, bounds are inclusive); default applies only to omitted "
          "optional fields. Type names refer to definitions below.\n")


def schema_notation(schema):
    definitions = schema.get("$defs", {})

    def render(node):
        node = dict(node)
        node.pop("$defs", None)
        if "$ref" in node:
            ref = node.pop("$ref")
            if not ref.startswith("#/$defs/") or ref[8:] not in definitions:
                raise ValueError("schema_notation_reference")
            text = ref[8:]
        elif "anyOf" in node:
            text = "(" + " | ".join(render(n) for n in node.pop("anyOf")) + ")"
        elif node.get("type") == "object":
            node.pop("type")
            if node.pop("additionalProperties", None) is not False:
                raise ValueError("schema_notation_object_policy")
            properties = node.pop("properties")
            required = node.pop("required", [])
            if len(set(required)) != len(required) or set(required) - set(properties):
                raise ValueError("schema_notation_required")
            text = "Object{" + "; ".join(k + ("" if k in required else "?") + ":" + render(v)
                for k, v in properties.items()) + "}"
        elif node.get("type") == "array":
            node.pop("type")
            text = "Array<" + render(node.pop("items")) + ">"
        else:
            kind = node.pop("type", None)
            if kind not in ("string", "integer", "number", "boolean", "null"):
                raise ValueError("schema_notation_type")
            text = kind
            if "enum" in node:
                # Retain the primitive type too: enum may contain mixed values.
                text += "(" + " | ".join(compact(v) for v in node.pop("enum")) + ")"
        if set(node) - {"minimum", "maximum", "minLength", "maxLength", "minItems", "maxItems", "pattern", "default"}:
            raise ValueError("schema_notation_unknown_constraint")
        return text + ("[" + compact(node) + "]" if node else "")

    return LEGEND + "\n".join(k + " = " + render(v) for k, v in definitions.items()) + "\nResult = " + render(schema)
