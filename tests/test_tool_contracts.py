import unittest

from app.tools.errors import (
    ToolInputValidationError,
    ToolOutputValidationError,
    ToolSchemaDefinitionError,
)
from app.tools.models import (
    CachePolicy,
    CircuitBreakerPolicy,
    RetryPolicy,
    ToolContext,
    ToolDefinition,
    ToolErrorInfo,
    ToolPolicy,
    ToolResult,
)
from app.tools.schema import (
    check_tool_schemas,
    validate_tool_input,
    validate_tool_output,
)


def echo_handler(params, context):
    return {"echo": params["message"], "call_id": context.call_id}


def valid_definition(**overrides):
    values = {
        "name": "system.echo",
        "version": "1.0.0",
        "description": "Echo one message for contract testing.",
        "handler": echo_handler,
        "input_schema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "minLength": 1},
            },
            "required": ["message"],
            "additionalProperties": False,
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "echo": {"type": "string"},
                "call_id": {"type": "string"},
            },
            "required": ["echo", "call_id"],
            "additionalProperties": False,
        },
    }
    values.update(overrides)
    return ToolDefinition(**values)


class ToolDefinitionTests(unittest.TestCase):
    def test_definition_contains_machine_readable_contract_and_policy(self) -> None:
        definition = valid_definition(
            policy=ToolPolicy(
                timeout_s=12.0,
                retry=RetryPolicy(
                    max_attempts=2,
                    base_delay_s=0.1,
                    max_delay_s=0.5,
                ),
                cache=CachePolicy(ttl_s=30.0),
                circuit_breaker=CircuitBreakerPolicy(
                    failure_threshold=3,
                    recovery_s=20.0,
                ),
            ),
            idempotent=True,
        )

        self.assertEqual("system.echo", definition.name)
        self.assertEqual(2, definition.policy.retry.max_attempts)
        self.assertEqual(30.0, definition.policy.cache.ttl_s)

    def test_definition_rejects_ambiguous_identity_and_invalid_handler(self) -> None:
        cases = [
            {"name": "Echo"},
            {"name": "echo"},
            {"name": "system..echo"},
            {"version": "latest"},
            {"description": "   "},
            {"handler": None},
        ]
        for overrides in cases:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    valid_definition(**overrides)

    def test_non_idempotent_tool_cannot_enable_automatic_retries(self) -> None:
        with self.assertRaises(ValueError):
            valid_definition(
                idempotent=False,
                policy=ToolPolicy(retry=RetryPolicy(max_attempts=2)),
            )

    def test_policy_values_are_bounded(self) -> None:
        invalid_factories = [
            lambda: RetryPolicy(max_attempts=0),
            lambda: RetryPolicy(max_attempts=6),
            lambda: RetryPolicy(base_delay_s=-1),
            lambda: RetryPolicy(base_delay_s=2, max_delay_s=1),
            lambda: CachePolicy(ttl_s=-1),
            lambda: CircuitBreakerPolicy(failure_threshold=0),
            lambda: CircuitBreakerPolicy(recovery_s=0),
            lambda: ToolPolicy(timeout_s=0),
        ]
        for factory in invalid_factories:
            with self.subTest(factory=factory):
                with self.assertRaises(ValueError):
                    factory()


class ToolContextAndResultTests(unittest.TestCase):
    def test_context_separates_runtime_budget_from_business_params(self) -> None:
        context = ToolContext(
            call_id="call-123",
            attempt=2,
            deadline_monotonic=110.0,
            metadata={"run_id": "review-1"},
        )

        self.assertEqual(10.0, context.remaining_s(now_monotonic=100.0))
        self.assertEqual(0.0, context.remaining_s(now_monotonic=120.0))

    def test_context_rejects_invalid_identity_attempt_and_deadline(self) -> None:
        cases = [
            {"call_id": "", "attempt": 1, "deadline_monotonic": 10.0},
            {"call_id": "call", "attempt": 0, "deadline_monotonic": 10.0},
            {"call_id": "call", "attempt": 1, "deadline_monotonic": 0.0},
        ]
        for values in cases:
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    ToolContext(**values)

    def test_result_distinguishes_upstream_cache_fallback_and_failure(self) -> None:
        upstream = ToolResult.ok(
            data={"value": 1},
            tool_name="system.echo",
            tool_version="1.0.0",
            call_id="call-1",
            attempts=1,
            latency_ms=5.0,
        )
        cached = ToolResult.ok(
            data={"value": 1},
            tool_name="system.echo",
            tool_version="1.0.0",
            call_id="call-2",
            attempts=0,
            latency_ms=0.1,
            cached=True,
        )
        fallback = ToolResult.ok(
            data={"value": "fallback"},
            tool_name="system.echo",
            tool_version="1.0.0",
            call_id="call-3",
            attempts=1,
            latency_ms=6.0,
            fallback_used=True,
            upstream_error=ToolErrorInfo(
                code="unavailable",
                message="Upstream unavailable.",
                retryable=True,
            ),
        )
        failed = ToolResult.fail(
            tool_name="system.echo",
            tool_version="1.0.0",
            call_id="call-4",
            attempts=1,
            latency_ms=7.0,
            error=ToolErrorInfo(
                code="invalid_input",
                message="Input contract rejected.",
                retryable=False,
            ),
        )

        self.assertTrue(upstream.success)
        self.assertTrue(cached.cached)
        self.assertTrue(fallback.fallback_used)
        self.assertIsNotNone(fallback.upstream_error)
        self.assertFalse(failed.success)
        self.assertEqual("invalid_input", failed.error.code)

    def test_result_rejects_inconsistent_success_flags(self) -> None:
        error = ToolErrorInfo(
            code="failed",
            message="failure",
            retryable=False,
        )
        invalid_factories = [
            lambda: ToolResult(
                success=True,
                data={},
                tool_name="system.echo",
                tool_version="1.0.0",
                call_id="call",
                attempts=1,
                latency_ms=1,
                error=error,
            ),
            lambda: ToolResult(
                success=False,
                data=None,
                tool_name="system.echo",
                tool_version="1.0.0",
                call_id="call",
                attempts=1,
                latency_ms=1,
                error=None,
            ),
            lambda: ToolResult.ok(
                data={},
                tool_name="system.echo",
                tool_version="1.0.0",
                call_id="call",
                attempts=1,
                latency_ms=1,
                cached=True,
                fallback_used=True,
            ),
        ]
        for factory in invalid_factories:
            with self.subTest(factory=factory):
                with self.assertRaises(ValueError):
                    factory()


class ToolSchemaTests(unittest.TestCase):
    def test_validates_input_and_output_with_full_json_schema_rules(self) -> None:
        definition = valid_definition()
        check_tool_schemas(definition)
        validate_tool_input(definition, {"message": "hello"})
        validate_tool_output(
            definition,
            {"echo": "hello", "call_id": "call-1"},
        )

    def test_rejects_missing_wrong_type_and_unknown_input_fields(self) -> None:
        definition = valid_definition()
        invalid_inputs = [
            {},
            {"message": 123},
            {"message": ""},
            {"message": "hello", "unexpected": True},
        ]
        for params in invalid_inputs:
            with self.subTest(params=params):
                with self.assertRaises(ToolInputValidationError):
                    validate_tool_input(definition, params)

    def test_rejects_output_that_breaks_declared_contract(self) -> None:
        definition = valid_definition()
        with self.assertRaises(ToolOutputValidationError):
            validate_tool_output(definition, {"echo": "hello"})

    def test_rejects_invalid_schema_definition_during_registration_check(self) -> None:
        definition = valid_definition(
            input_schema={"type": "definitely-not-a-json-schema-type"}
        )
        with self.assertRaises(ToolSchemaDefinitionError):
            check_tool_schemas(definition)


if __name__ == "__main__":
    unittest.main()
