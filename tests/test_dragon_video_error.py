import hashlib
import json
import subprocess
import sys
from pathlib import Path

from scripts.sanitize_dragon_video_error import sanitize_dragon_video_error


def test_extracts_nested_parameter_error_without_persisting_outer_body():
    body = json.dumps(
        {
            "code": "fail_to_fetch_task",
            "message": json.dumps(
                {
                    "error": {
                        "code": "InvalidParameter.TaskTypeConstraint",
                        "message": (
                            "The parameter ratio specified in the request is not valid. "
                            "Request id: req-sensitive"
                        ),
                        "param": "ratio",
                        "type": "BadRequest",
                    }
                }
            ),
            "data": None,
        }
    )

    diagnostic = sanitize_dragon_video_error(body, http_status=400)

    assert diagnostic == {
        "http_status": 400,
        "outer_code": "fail_to_fetch_task",
        "remote_error_code": "InvalidParameter.TaskTypeConstraint",
        "remote_error_param": "ratio",
        "remote_error_type": "BadRequest",
        "remote_message": (
            "The parameter ratio specified in the request is not valid. "
            "Request id: [redacted]"
        ),
        "raw_body_length": len(body.encode("utf-8")),
        "raw_body_sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
    }


def test_unknown_or_sensitive_body_is_digest_only():
    body = 'upstream echoed https://signed.example/output?token=secret and sk-live-secret'

    diagnostic = sanitize_dragon_video_error(body, http_status=400)

    assert diagnostic["http_status"] == 400
    assert diagnostic["raw_body_length"] == len(body.encode("utf-8"))
    assert len(diagnostic["raw_body_sha256"]) == 64
    assert set(diagnostic) == {"http_status", "raw_body_length", "raw_body_sha256"}
    assert "signed.example" not in json.dumps(diagnostic)
    assert "sk-live-secret" not in json.dumps(diagnostic)


def test_rejects_non_allowlisted_nested_fields_instead_of_leaking_them():
    body = json.dumps(
        {
            "code": "fail_to_fetch_task",
            "message": json.dumps(
                {
                    "error": {
                        "code": "InvalidParameter",
                        "message": "bad reference",
                        "param": "video_with_roles",
                        "type": "BadRequest",
                        "raw_request": "secret prompt and signed URL",
                    }
                }
            ),
        }
    )

    diagnostic = sanitize_dragon_video_error(body, http_status=400)

    assert set(diagnostic) == {"http_status", "raw_body_length", "raw_body_sha256"}


def test_cli_reads_body_from_stdin_and_emits_only_sanitized_json():
    body = json.dumps(
        {
            "code": "fail_to_fetch_task",
            "message": json.dumps(
                {
                    "error": {
                        "code": "InvalidParameter",
                        "message": "The parameter duration must be -1. Request id: req-abcdef",
                        "param": "duration",
                        "type": "BadRequest",
                    }
                }
            ),
            "data": None,
        }
    )
    script = Path(__file__).parents[1] / "scripts" / "sanitize_dragon_video_error.py"

    completed = subprocess.run(
        [sys.executable, str(script), "--http-status", "400"],
        input=body,
        text=True,
        capture_output=True,
        check=True,
    )
    diagnostic = json.loads(completed.stdout)

    assert completed.stderr == ""
    assert diagnostic["remote_error_param"] == "duration"
    assert diagnostic["remote_message"].endswith("Request id: [redacted]")
    assert "req-abcdef" not in completed.stdout
