import unittest
from dataclasses import replace

from app.mcp.errors import (
    McpCapabilityError,
    McpEnvelopeError,
    McpErrorInfo,
    McpProtocolVersionError,
    McpRemoteError,
    McpResultError,
    McpSchemaDriftError,
    McpToolCatalogError,
    McpToolCallError,
)
from app.mcp.models import (
    McpContractLimits,
    McpImplementation,
    McpInitializeRequest,
    McpInitializeResult,
    McpListToolsRequest,
    McpToolCallRequest,
    McpToolCallResult,
    McpToolCatalog,
)


PROTOCOL_VERSION = "2025-06-18"


def initialize_response(
    *,
    request_id: str | int = "init-1",
    protocol_version: str = PROTOCOL_VERSION,
    capabilities: dict | None = None,
    result_overrides: dict | None = None,
    envelope_overrides: dict | None = None,
) -> dict:
    result = {
        "protocolVersion": protocol_version,
        "capabilities": (
            {"tools": {"listChanged": True}}
            if capabilities is None
            else capabilities
        ),
        "serverInfo": {
            "name": "fixture-mcp-server",
            "version": "1.2.3",
        },
    }
    if result_overrides:
        result.update(result_overrides)
    envelope = {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": result,
    }
    if envelope_overrides:
        envelope.update(envelope_overrides)
    return envelope


def initialized() -> McpInitializeResult:
    return McpInitializeResult.from_wire(
        initialize_response(),
        expected_request_id="init-1",
        supported_protocol_versions=frozenset({PROTOCOL_VERSION}),
    )


def valid_tool(
    *,
    name: str = "meta.patch",
    description: str = "Return bounded patch metadata.",
    input_schema: dict | None = None,
    output_schema: dict | None = None,
) -> dict:
    return {
        "name": name,
        "description": description,
        "inputSchema": input_schema
        or {
            "type": "object",
            "properties": {
                "patch": {"type": "string", "minLength": 1},
            },
            "required": ["patch"],
            "additionalProperties": False,
        },
        "outputSchema": output_schema
        or {
            "type": "object",
            "properties": {
                "tier": {"type": "string"},
            },
            "required": ["tier"],
            "additionalProperties": False,
        },
    }


def list_response(
    tools: list[dict],
    *,
    request_id: str | int = "list-1",
    next_cursor: str | None = None,
) -> dict:
    result: dict = {"tools": tools}
    if next_cursor is not None:
        result["nextCursor"] = next_cursor
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def catalog_from(*tools: dict, limits: McpContractLimits | None = None) -> McpToolCatalog:
    return McpToolCatalog.from_wire(
        list_response(list(tools)),
        initialization=initialized(),
        expected_request_id="list-1",
        limits=limits or McpContractLimits(),
    )


def valid_call(catalog: McpToolCatalog | None = None) -> McpToolCallRequest:
    actual_catalog = catalog or catalog_from(valid_tool())
    return McpToolCallRequest.from_catalog(
        request_id="call-1",
        catalog=actual_catalog,
        tool_name="meta.patch",
        arguments={"patch": "15.1"},
        allowed_tools=frozenset({"meta.patch"}),
    )


class McpInitializeContractTests(unittest.TestCase):
    def test_initialize_request_owns_a_strict_standard_envelope(self) -> None:
        request = McpInitializeRequest(
            request_id="init-1",
            protocol_version=PROTOCOL_VERSION,
            capabilities={},
            client_info=McpImplementation(name="riftcoach", version="0.1.0"),
        )

        self.assertEqual(
            {
                "jsonrpc": "2.0",
                "id": "init-1",
                "method": "initialize",
                "params": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {},
                    "clientInfo": {"name": "riftcoach", "version": "0.1.0"},
                },
            },
            request.to_wire(),
        )

        wire = request.to_wire()
        wire["params"]["clientInfo"]["name"] = "mutated"
        self.assertEqual("riftcoach", request.to_wire()["params"]["clientInfo"]["name"])

    def test_initialize_result_negotiates_an_allowlisted_version_and_tools(self) -> None:
        result = initialized()

        self.assertEqual(PROTOCOL_VERSION, result.protocol_version)
        self.assertEqual("fixture-mcp-server", result.server_info.name)
        self.assertTrue(result.tools.list_changed)
        result.require_tools()

    def test_initialize_rejects_version_outside_the_explicit_allowlist(self) -> None:
        with self.assertRaises(McpProtocolVersionError) as caught:
            McpInitializeResult.from_wire(
                initialize_response(protocol_version="2099-01-01"),
                expected_request_id="init-1",
                supported_protocol_versions=frozenset({PROTOCOL_VERSION}),
            )

        self.assertEqual("mcp_protocol_version_unsupported", caught.exception.info.code)

    def test_initialize_requires_the_server_tools_capability_before_discovery(self) -> None:
        result = McpInitializeResult.from_wire(
            initialize_response(capabilities={}),
            expected_request_id="init-1",
            supported_protocol_versions=frozenset({PROTOCOL_VERSION}),
        )

        with self.assertRaises(McpCapabilityError) as caught:
            result.require_tools()
        self.assertEqual("mcp_tools_capability_missing", caught.exception.info.code)

    def test_initialize_is_strict_about_envelope_result_and_boolean_types(self) -> None:
        bad_envelopes = (
            initialize_response(envelope_overrides={"jsonrpc": "1.0"}),
            initialize_response(envelope_overrides={"id": True}),
            initialize_response(envelope_overrides={"unexpected": "field"}),
            initialize_response(result_overrides={"unexpected": "field"}),
            initialize_response(capabilities={"tools": {"listChanged": 1}}),
        )

        for wire in bad_envelopes:
            with self.subTest(wire=wire):
                with self.assertRaises(McpEnvelopeError):
                    McpInitializeResult.from_wire(
                        wire,
                        expected_request_id="init-1",
                        supported_protocol_versions=frozenset({PROTOCOL_VERSION}),
                    )


class McpToolCatalogContractTests(unittest.TestCase):
    def test_tools_list_request_is_transport_neutral_and_cursor_bounded(self) -> None:
        first = McpListToolsRequest(request_id="list-1")
        next_page = McpListToolsRequest(request_id=2, cursor="cursor-2")

        self.assertEqual(
            {"jsonrpc": "2.0", "id": "list-1", "method": "tools/list", "params": {}},
            first.to_wire(),
        )
        self.assertEqual({"cursor": "cursor-2"}, next_page.to_wire()["params"])

    def test_tools_list_builds_an_immutable_unique_schema_snapshot(self) -> None:
        raw_tool = valid_tool()
        catalog = catalog_from(raw_tool)
        raw_tool["inputSchema"]["properties"]["patch"]["type"] = "integer"

        self.assertEqual(1, len(catalog.tools))
        self.assertEqual("meta.patch", catalog.tools[0].name)
        self.assertEqual(
            "string",
            catalog.tools[0].input_schema["properties"]["patch"]["type"],
        )
        self.assertEqual(64, len(catalog.digest))
        self.assertEqual(64, len(catalog.tools[0].schema_digest))
        with self.assertRaises(TypeError):
            catalog.tools[0].input_schema["type"] = "array"
        with self.assertRaises(ValueError):
            replace(catalog.tools[0], schema_digest="0" * 64)
        with self.assertRaises(ValueError):
            replace(catalog, digest="0" * 64)

    def test_tools_list_accepts_strict_standard_annotations_without_repr_leak(self) -> None:
        raw_tool = valid_tool(description="sk-secret untrusted description")
        raw_tool["annotations"] = {
            "title": "Read-only patch lookup",
            "readOnlyHint": True,
            "destructiveHint": False,
            "idempotentHint": True,
            "openWorldHint": True,
        }

        catalog = catalog_from(raw_tool)

        self.assertTrue(catalog.tools[0].annotations["readOnlyHint"])
        self.assertNotIn("sk-secret", repr(catalog))

    def test_tools_list_rejects_duplicate_names_and_invalid_json_schema(self) -> None:
        invalid_schema = valid_tool(
            input_schema={"type": "definitely-not-a-json-schema-type"}
        )
        cases = (
            [valid_tool(), valid_tool()],
            [invalid_schema],
        )

        for tools in cases:
            with self.subTest(tools=tools):
                with self.assertRaises(McpToolCatalogError):
                    catalog_from(*tools)

    def test_tools_list_enforces_count_and_canonical_byte_limits(self) -> None:
        with self.assertRaises(McpToolCatalogError) as count_error:
            catalog_from(
                valid_tool(name="meta.patch"),
                valid_tool(name="meta.roles"),
                limits=McpContractLimits(max_tools=1),
            )
        self.assertEqual("mcp_tool_catalog_too_large", count_error.exception.info.code)

        with self.assertRaises(McpToolCatalogError) as byte_error:
            catalog_from(
                valid_tool(description="x" * 500),
                limits=McpContractLimits(max_catalog_bytes=128),
            )
        self.assertEqual("mcp_tool_catalog_too_large", byte_error.exception.info.code)

    def test_tools_list_rejects_unknown_fields_and_non_object_schemas(self) -> None:
        extra = valid_tool()
        extra["rawBody"] = "must not cross the adapter"
        non_object = valid_tool(input_schema={"type": "array", "items": {}})

        for tool in (extra, non_object):
            with self.subTest(tool=tool):
                with self.assertRaises(McpToolCatalogError):
                    catalog_from(tool)


class McpToolCallContractTests(unittest.TestCase):
    def test_tools_call_requires_discovery_allowlist_and_valid_arguments(self) -> None:
        catalog = catalog_from(valid_tool())
        request = valid_call(catalog)

        self.assertEqual(
            {
                "jsonrpc": "2.0",
                "id": "call-1",
                "method": "tools/call",
                "params": {
                    "name": "meta.patch",
                    "arguments": {"patch": "15.1"},
                },
            },
            request.to_wire(),
        )

        bad_cases = (
            {"tool_name": "meta.unknown", "arguments": {}},
            {
                "tool_name": "meta.patch",
                "arguments": {"patch": "15.1"},
                "allowed_tools": frozenset(),
            },
            {"tool_name": "meta.patch", "arguments": {"patch": 151}},
            {"tool_name": "meta.patch", "arguments": {"patch": "15.1", "extra": True}},
        )
        for overrides in bad_cases:
            values = {
                "request_id": "call-bad",
                "catalog": catalog,
                "tool_name": "meta.patch",
                "arguments": {"patch": "15.1"},
                "allowed_tools": frozenset({"meta.patch"}),
            }
            values.update(overrides)
            with self.subTest(values=values):
                with self.assertRaises(McpToolCallError):
                    McpToolCallRequest.from_catalog(**values)

        with self.assertRaises(McpToolCallError):
            McpToolCallRequest.from_catalog(
                request_id="call-large",
                catalog=catalog,
                tool_name="meta.patch",
                arguments={"patch": "x" * 500},
                allowed_tools=frozenset({"meta.patch"}),
                limits=McpContractLimits(max_argument_bytes=128),
            )

    def test_tools_call_detects_schema_drift_before_transport(self) -> None:
        original = catalog_from(valid_tool())
        request = valid_call(original)
        changed = catalog_from(
            valid_tool(
                input_schema={
                    "type": "object",
                    "properties": {"patch": {"type": "integer"}},
                    "required": ["patch"],
                    "additionalProperties": False,
                }
            )
        )

        with self.assertRaises(McpSchemaDriftError) as caught:
            request.require_current_catalog(changed)
        self.assertEqual("mcp_tool_schema_drift", caught.exception.info.code)

    def test_tools_call_success_validates_bounded_structured_result(self) -> None:
        request = valid_call()
        wire = {
            "jsonrpc": "2.0",
            "id": "call-1",
            "result": {
                "content": [{"type": "text", "text": "bounded evidence"}],
                "structuredContent": {"tier": "S"},
                "isError": False,
            },
        }

        result = McpToolCallResult.from_wire(
            wire,
            request=request,
            limits=McpContractLimits(),
        )

        self.assertTrue(result.success)
        self.assertEqual("S", result.structured_content["tier"])
        self.assertEqual("text", result.content[0]["type"])
        self.assertIsNone(result.error)

    def test_tools_call_rejects_malformed_oversized_and_schema_invalid_results(self) -> None:
        request = valid_call()
        malformed_results = (
            {"content": {"type": "text"}, "isError": False},
            {"content": [], "isError": 0},
            {"content": [], "isError": False, "unexpected": True},
            {"content": [], "structuredContent": {"tier": 1}, "isError": False},
        )

        for raw_result in malformed_results:
            with self.subTest(raw_result=raw_result):
                with self.assertRaises(McpResultError):
                    McpToolCallResult.from_wire(
                        {"jsonrpc": "2.0", "id": "call-1", "result": raw_result},
                        request=request,
                        limits=McpContractLimits(),
                    )

        with self.assertRaises(McpResultError) as oversized:
            McpToolCallResult.from_wire(
                {
                    "jsonrpc": "2.0",
                    "id": "call-1",
                    "result": {
                        "content": [{"type": "text", "text": "x" * 500}],
                        "structuredContent": {"tier": "S"},
                        "isError": False,
                    },
                },
                request=request,
                limits=McpContractLimits(max_result_bytes=128),
            )
        self.assertEqual("mcp_result_too_large", oversized.exception.info.code)

    def test_is_error_discards_untrusted_content_and_projects_a_safe_error(self) -> None:
        request = valid_call()
        raw_secret = "sk-secret raw prompt and upstream body"
        result = McpToolCallResult.from_wire(
            {
                "jsonrpc": "2.0",
                "id": "call-1",
                "result": {
                    "content": [{"type": "text", "text": raw_secret}],
                    "isError": True,
                },
            },
            request=request,
            limits=McpContractLimits(),
        )

        self.assertFalse(result.success)
        self.assertEqual((), result.content)
        self.assertIsNone(result.structured_content)
        self.assertEqual("mcp_tool_error", result.error.code)
        self.assertNotIn(raw_secret, repr(result))

    def test_json_rpc_error_discards_remote_message_data_and_body(self) -> None:
        request = valid_call()
        remote_secret = "sk-secret raw prompt https://internal.invalid"

        with self.assertRaises(McpRemoteError) as caught:
            McpToolCallResult.from_wire(
                {
                    "jsonrpc": "2.0",
                    "id": "call-1",
                    "error": {
                        "code": -32603,
                        "message": remote_secret,
                        "data": {"body": remote_secret},
                    },
                },
                request=request,
                limits=McpContractLimits(),
            )

        self.assertEqual("mcp_remote_error", caught.exception.info.code)
        self.assertEqual(-32603, caught.exception.info.remote_code)
        self.assertNotIn(remote_secret, str(caught.exception))
        self.assertNotIn(remote_secret, repr(caught.exception.info))
        with self.assertRaises(TypeError):
            McpErrorInfo(  # type: ignore[call-arg]
                code="mcp_remote_error",
                retryable=False,
                request_id="call-1",
                raw_body=remote_secret,
            )

    def test_response_requires_matching_strict_request_id(self) -> None:
        request = valid_call()
        with self.assertRaises(McpEnvelopeError):
            McpToolCallResult.from_wire(
                {
                    "jsonrpc": "2.0",
                    "id": "different-call",
                    "result": {"content": [], "isError": False},
                },
                request=request,
                limits=McpContractLimits(),
            )


class McpPrimitiveStrictnessTests(unittest.TestCase):
    def test_integer_limits_and_error_codes_reject_booleans(self) -> None:
        with self.assertRaises(ValueError):
            McpContractLimits(max_tools=True)
        with self.assertRaises(ValueError):
            McpErrorInfo(
                code="mcp_remote_error",
                retryable=False,
                request_id="call-1",
                remote_code=True,
            )

    def test_remote_error_code_must_be_an_integer_not_a_boolean(self) -> None:
        request = valid_call()
        with self.assertRaises(McpEnvelopeError):
            McpToolCallResult.from_wire(
                {
                    "jsonrpc": "2.0",
                    "id": "call-1",
                    "error": {"code": True, "message": "untrusted"},
                },
                request=request,
                limits=McpContractLimits(),
            )


if __name__ == "__main__":
    unittest.main()
