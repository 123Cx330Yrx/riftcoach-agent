import unittest
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.providers.errors import ProviderResponseError
from app.providers.models import ChatResponse, TokenUsage
from app.providers.structured import (
    StructuredDecodeResult,
    contract_for_model,
    decode_structured_response,
)


class IssueModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: Literal["high", "low"]
    explanation: str = Field(min_length=1)


class EvaluationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: int = Field(ge=0, le=100)
    verdict: Literal["pass", "fail"]
    issues: list[IssueModel]


def response(content: str, *, finish_reason: str = "stop") -> ChatResponse:
    return ChatResponse(
        content=content,
        model="fake-model",
        provider="fake-provider",
        finish_reason=finish_reason,
        usage=TokenUsage(input_tokens=0, output_tokens=0),
    )


class StructuredOutputTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = contract_for_model(
            name="coach_evaluation",
            version="1.0.0",
            output_model=EvaluationModel,
        )

    def test_decodes_one_strict_json_object(self) -> None:
        result = decode_structured_response(
            response=response(
                '{"score":90,"verdict":"pass","issues":[]}'
            ),
            contract=self.contract,
            output_model=EvaluationModel,
        )

        self.assertIsInstance(result, StructuredDecodeResult)
        self.assertEqual(90, result.value.score)
        self.assertFalse(result.repair_attempted)

    def test_rejects_invalid_json_schema_shapes_without_repair(self) -> None:
        invalid_contents = (
            '{"score":90,"verdict":"pass"}',
            '{"score":90,"verdict":"pass","issues":[],"extra":true}',
            '{"score":"90","verdict":"pass","issues":[]}',
            '{"score":90,"verdict":"unknown","issues":[]}',
            '{"score":90,"verdict":"fail","issues":[{"severity":"high"}]}',
            'not json',
            '```json\n{"score":90,"verdict":"pass","issues":[]}\n```',
        )

        for content in invalid_contents:
            with self.subTest(content=content):
                with self.assertRaises(ProviderResponseError) as captured:
                    decode_structured_response(
                        response=response(content),
                        contract=self.contract,
                        output_model=EvaluationModel,
                    )
                self.assertEqual(
                    "invalid_structured_output",
                    captured.exception.code,
                )
                self.assertNotIn(content, str(captured.exception))

    def test_finish_reason_length_is_treated_as_invalid_even_if_json_is_valid(
        self,
    ) -> None:
        with self.assertRaises(ProviderResponseError):
            decode_structured_response(
                response=response(
                    '{"score":90,"verdict":"pass","issues":[]}',
                    finish_reason="length",
                ),
                contract=self.contract,
                output_model=EvaluationModel,
            )

    def test_calls_repair_once_and_revalidates_with_the_same_contract(self) -> None:
        calls = []

        def repair(request):
            calls.append(request)
            return response('{"score":88,"verdict":"pass","issues":[]}')

        result = decode_structured_response(
            response=response('{"score":"bad"}'),
            contract=self.contract,
            output_model=EvaluationModel,
            repair=repair,
        )

        self.assertTrue(result.repair_attempted)
        self.assertEqual(88, result.value.score)
        self.assertEqual(1, len(calls))
        self.assertIs(self.contract, calls[0].contract)
        self.assertEqual('{"score":"bad"}', calls[0].invalid_content)

    def test_never_repairs_more_than_once(self) -> None:
        calls = []

        def repair(request):
            calls.append(request)
            return response('{"score":"still-bad"}')

        with self.assertRaises(ProviderResponseError) as captured:
            decode_structured_response(
                response=response("not json and contains sk-secret"),
                contract=self.contract,
                output_model=EvaluationModel,
                repair=repair,
            )

        self.assertEqual(1, len(calls))
        self.assertEqual("invalid_structured_output", captured.exception.code)
        self.assertNotIn("sk-secret", str(captured.exception))

    def test_rejects_model_that_does_not_forbid_extra_fields(self) -> None:
        class LooseModel(BaseModel):
            score: int

        loose_contract = contract_for_model(
            name="loose",
            version="1.0.0",
            output_model=LooseModel,
        )

        with self.assertRaises(ValueError):
            decode_structured_response(
                response=response('{"score":1}'),
                contract=loose_contract,
                output_model=LooseModel,
            )


if __name__ == "__main__":
    unittest.main()
