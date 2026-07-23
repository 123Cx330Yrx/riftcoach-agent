import unittest

from app.tools.errors import DuplicateToolError, ToolNotFoundError
from app.tools.models import ToolDefinition
from app.tools.registry import ToolRegistry


def handler(params, context):
    return {"ok": True}


def definition(name: str, version: str = "1.0.0") -> ToolDefinition:
    return ToolDefinition(
        name=name,
        version=version,
        description=f"Test tool {name}.",
        handler=handler,
        input_schema={
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        output_schema={
            "type": "object",
            "properties": {"ok": {"type": "boolean"}},
            "required": ["ok"],
            "additionalProperties": False,
        },
    )


class ToolRegistryTests(unittest.TestCase):
    def test_registers_gets_and_lists_tools_in_stable_order(self) -> None:
        registry = ToolRegistry()
        registry.register(definition("lol.riot.summary"))
        registry.register(definition("lol.knowledge.search"))

        self.assertEqual(
            "lol.riot.summary",
            registry.get("lol.riot.summary").name,
        )
        self.assertEqual(
            ["lol.knowledge.search", "lol.riot.summary"],
            [tool.name for tool in registry.list_tools()],
        )
        self.assertEqual(2, len(registry))

    def test_rejects_duplicate_name_even_when_version_differs(self) -> None:
        registry = ToolRegistry()
        registry.register(definition("lol.riot.summary", "1.0.0"))

        with self.assertRaises(DuplicateToolError):
            registry.register(definition("lol.riot.summary", "2.0.0"))

    def test_rejects_invalid_schema_before_tool_becomes_visible(self) -> None:
        registry = ToolRegistry()
        invalid = definition("lol.invalid.schema")
        object.__setattr__(
            invalid,
            "input_schema",
            {"type": "not-valid"},
        )

        with self.assertRaises(Exception):
            registry.register(invalid)

        self.assertEqual(0, len(registry))

    def test_unknown_tool_raises_typed_not_found_error(self) -> None:
        registry = ToolRegistry()
        with self.assertRaises(ToolNotFoundError) as captured:
            registry.get("lol.missing.tool")
        self.assertEqual("lol.missing.tool", captured.exception.tool_name)


if __name__ == "__main__":
    unittest.main()
