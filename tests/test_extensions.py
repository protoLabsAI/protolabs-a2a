"""Wire-contract tests for the four protoLabs A2A extensions + Part helpers.

These exercise ONLY ``protolabs_a2a`` (no protoagent runtime deps). They lock the
byte-for-byte wire contract the TS mirror ``@protolabs/a2a`` also enforces:
emit produces the member-discriminated DataPart shape, parse round-trips it, and
the MIME / URI constants are the canonical ones the fleet matches on.
"""

from __future__ import annotations

import protolabs_a2a as pa


# ── part shape ────────────────────────────────────────────────────────────────


def test_data_part_is_member_discriminated_shape():
    part = pa.data_part({"k": "v"}, "application/json")
    assert part["content"] == {"$case": "data", "value": {"k": "v"}}
    assert part["metadata"]["mimeType"] == "application/json"
    assert part["mediaType"] == pa.DATA_MEDIA_TYPE == "application/json"
    assert part["filename"] == ""


def test_text_part_and_read_text_round_trip():
    part = pa.text_part("hello")
    assert part["content"] == {"$case": "text", "value": "hello"}
    assert pa.read_text(part) == "hello"


def test_read_data_accepts_flattened_proto_json():
    # a2a-sdk's protobuf serializer flattens content.value to a top-level `data`.
    flat = {"data": {"x": 1}, "metadata": {"mimeType": "application/json"}}
    mime, payload = pa.read_data(flat)
    assert mime == "application/json"
    assert payload == {"x": 1}


def test_read_data_non_data_part_returns_none_tuple():
    assert pa.read_data(pa.text_part("hi")) == (None, None)


# ── canonical constants ─────────────────────────────────────────────────────


def test_extension_uris_and_mimes_are_canonical():
    assert pa.COST_EXT_URI == "https://proto-labs.ai/a2a/ext/cost-v1"
    assert pa.COST_MIME == "application/vnd.protolabs.cost-v1+json"
    assert pa.CONFIDENCE_MIME == "application/vnd.protolabs.confidence-v1+json"
    assert pa.WORLDSTATE_DELTA_MIME == "application/vnd.protolabs.worldstate-delta-v1+json"
    assert pa.WORLDSTATE_DELTA_EXT_URI == "https://proto-labs.ai/a2a/ext/worldstate-delta-v1"
    assert pa.TOOL_CALL_MIME == "application/vnd.protolabs.tool-call-v1+json"
    assert pa.ALL_EXTENSION_URIS == (
        pa.COST_EXT_URI,
        pa.CONFIDENCE_EXT_URI,
        pa.WORLDSTATE_DELTA_EXT_URI,
        pa.TOOL_CALL_EXT_URI,
    )


# ── cost-v1 ──────────────────────────────────────────────────────────────────


def test_cost_payload_includes_cache_fields_and_costusd():
    part = pa.emit_cost(
        {
            "input_tokens": 1500, "output_tokens": 420,
            "cache_read_input_tokens": 900, "cache_creation_input_tokens": 100,
        },
        duration_ms=2000,
        cost_usd=0.0123,
        success=True,
    )
    assert part["metadata"]["mimeType"] == pa.COST_MIME
    payload = pa.parse_cost(part)
    assert payload is not None
    assert payload["usage"]["cache_read_input_tokens"] == 900
    assert payload["usage"]["cache_creation_input_tokens"] == 100
    assert "cost_usd" not in payload["usage"]
    assert payload["costUsd"] == 0.0123
    assert payload["durationMs"] == 2000
    assert payload["success"] is True


def test_cost_payload_omits_costusd_when_not_supplied():
    part = pa.emit_cost({"input_tokens": 10, "output_tokens": 5}, duration_ms=15)
    payload = pa.parse_cost(part)
    assert payload is not None
    assert "costUsd" not in payload
    assert "success" not in payload


# ── confidence-v1 ────────────────────────────────────────────────────────────


def test_emit_confidence_payload_minimal():
    part = pa.emit_confidence(0.7, success=True)
    assert part["metadata"]["mimeType"] == pa.CONFIDENCE_MIME
    assert pa.parse_confidence(part) == {"confidence": 0.7, "success": True}


def test_emit_confidence_includes_explanation_and_success_false():
    part = pa.emit_confidence(0.9, explanation="sure but wrong", success=False)
    payload = pa.parse_confidence(part)
    assert payload["confidence"] == 0.9
    assert payload["explanation"] == "sure but wrong"
    assert payload["success"] is False


# ── worldstate-delta-v1 ──────────────────────────────────────────────────────


def test_emit_and_parse_worldstate_delta():
    deltas = [
        {"domain": "board", "path": "data.backlog", "op": "inc", "value": 1},
        {"domain": "board", "path": "data.status", "op": "set", "value": "open"},
    ]
    part = pa.emit_worldstate_delta(deltas)
    assert part["metadata"]["mimeType"] == pa.WORLDSTATE_DELTA_MIME
    payload = pa.parse_worldstate_delta(part)
    assert payload == {"deltas": deltas}


# ── tool-call-v1 ─────────────────────────────────────────────────────────────


def test_emit_and_parse_tool_call():
    part = pa.emit_tool_call("call_1", "file_bug", "completed", result="BUG-12")
    assert part["metadata"]["mimeType"] == pa.TOOL_CALL_MIME
    payload = pa.parse_tool_call(part)
    assert payload == {
        "toolCallId": "call_1",
        "name": "file_bug",
        "phase": "completed",
        "result": "BUG-12",
    }


# ── cross-extension: parse only matches its own MIME ──────────────────────────


def test_parse_helpers_reject_foreign_mime():
    cost = pa.emit_cost({"input_tokens": 1, "output_tokens": 1})
    assert pa.parse_confidence(cost) is None
    assert pa.parse_worldstate_delta(cost) is None
    assert pa.parse_tool_call(cost) is None
    assert pa.parse_cost(cost) is not None
