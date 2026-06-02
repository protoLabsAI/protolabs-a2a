"""Tests for the structured-skill-output conventions (skills.py).

These cover only the LLM-free shared layer: the tool-spec transform, JSON-Schema
validation of returned args, and the DataPart emit/parse roundtrip. The forced
tool-call + repair retry are runtime-local (executor) and tested per-agent.
"""

from __future__ import annotations

import protolabs_a2a as pa
from protolabs_a2a.skills import (
    emit_skill_result,
    parse_skill_result,
    skill_result_mime,
    skill_tool_name,
    submit_skill_tool,
    validate_skill_args,
)

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "verdict": {
            "type": "string",
            "enum": ["approve", "approve-with-concerns", "revise", "reject"],
        },
        "reason": {"type": "string"},
    },
    "required": ["verdict", "reason"],
}


def test_submit_skill_tool_shape():
    tool = submit_skill_tool("market_review", SCHEMA)
    assert tool["type"] == "function"
    assert tool["function"]["name"] == "submit_market_review" == skill_tool_name("market_review")
    # schema passes through verbatim as the tool parameters
    assert tool["function"]["parameters"] is SCHEMA
    assert isinstance(tool["function"]["description"], str) and tool["function"]["description"]


def test_submit_skill_tool_custom_description():
    tool = submit_skill_tool("x", {"type": "object"}, description="custom")
    assert tool["function"]["description"] == "custom"


def test_skill_result_mime_form():
    assert skill_result_mime("market-review-v1") == "application/vnd.protolabs.market-review-v1+json"


def test_validate_skill_args_valid():
    assert validate_skill_args({"verdict": "reject", "reason": "off-brand"}, SCHEMA) == []


def test_validate_skill_args_missing_required():
    errs = validate_skill_args({"verdict": "reject"}, SCHEMA)
    assert errs and any("reason" in e for e in errs)


def test_validate_skill_args_bad_enum():
    errs = validate_skill_args({"verdict": "maybe", "reason": "x"}, SCHEMA)
    assert errs and any("verdict" in e for e in errs)


def test_validate_skill_args_rejects_extra_property():
    errs = validate_skill_args({"verdict": "approve", "reason": "x", "extra": 1}, SCHEMA)
    assert errs  # additionalProperties: false


def test_validate_skill_args_bad_schema():
    assert validate_skill_args({}, "not-a-schema") == ["schema must be a JSON Schema object"]


def test_emit_and_parse_roundtrip():
    obj = {"verdict": "revise", "reason": "needs work"}
    mime = skill_result_mime("market-review-v1")
    part = emit_skill_result(obj, mime)
    # canonical custom DataPart shape (mirrors parts.data_part)
    assert part["content"] == {"$case": "data", "value": obj}
    assert part["metadata"][pa.MIME_KEY] == mime
    assert part["mediaType"] == pa.DATA_MEDIA_TYPE
    # parse back: exact-mime match and vendor-prefix match both return the payload
    assert parse_skill_result(part, mime) == obj
    assert parse_skill_result(part) == obj


def test_parse_skill_result_mime_mismatch():
    part = emit_skill_result({"a": 1}, skill_result_mime("foo-v1"))
    assert parse_skill_result(part, "application/vnd.protolabs.bar-v1+json") is None


def test_parse_skill_result_non_data_part():
    assert parse_skill_result(pa.text_part("hello")) is None
    assert parse_skill_result({}) is None
