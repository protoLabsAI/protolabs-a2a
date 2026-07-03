"""Wire-contract tests for the four protoLabs A2A extensions + Part helpers.

These exercise ONLY ``protolabs_a2a`` (no protoagent runtime deps). They lock the
wire contract the TS mirror ``@protolabs/a2a`` also enforces: each extension
contributes a ``{<EXT_URI>: <payload>}`` fragment merged into an object's
``metadata`` map (the A2A convention — extension data lives in the metadata map
keyed by the extension URI), ``parse_*`` round-trips it from a metadata map, and
the URI constants are the canonical ones the fleet matches on.
"""

from __future__ import annotations

import protolabs_a2a as pa


# ── generic Part helpers (unchanged; still used for real content DataParts) ────


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
    mime, payload = pa.read_data({"data": {"x": 1}, "metadata": {"mimeType": "application/json"}})
    assert mime == "application/json"
    assert payload == {"x": 1}


def test_read_data_non_data_part_returns_none_tuple():
    assert pa.read_data(pa.text_part("hi")) == (None, None)


# ── canonical constants ─────────────────────────────────────────────────────


def test_extension_uris_are_canonical():
    assert pa.COST_EXT_URI == "https://proto-labs.ai/a2a/ext/cost-v1"
    assert pa.CONFIDENCE_EXT_URI == "https://proto-labs.ai/a2a/ext/confidence-v1"
    assert pa.WORLDSTATE_DELTA_EXT_URI == "https://proto-labs.ai/a2a/ext/worldstate-delta-v1"
    assert pa.TOOL_CALL_EXT_URI == "https://proto-labs.ai/a2a/ext/tool-call-v1"
    assert pa.ALL_EXTENSION_URIS == (
        pa.COST_EXT_URI,
        pa.CONFIDENCE_EXT_URI,
        pa.WORLDSTATE_DELTA_EXT_URI,
        pa.TOOL_CALL_EXT_URI,
    )


def test_every_extension_uri_has_a_card_description():
    assert set(pa.EXTENSION_DESCRIPTIONS) == set(pa.ALL_EXTENSION_URIS)
    assert all(pa.EXTENSION_DESCRIPTIONS[u] for u in pa.ALL_EXTENSION_URIS)


# ── cost-v1 ──────────────────────────────────────────────────────────────────


def test_cost_metadata_is_keyed_by_uri():
    meta = pa.cost_metadata({"input_tokens": 1, "output_tokens": 1})
    assert set(meta) == {pa.COST_EXT_URI}


def test_cost_payload_includes_cache_fields_and_costusd():
    meta = pa.cost_metadata(
        {
            "input_tokens": 1500, "output_tokens": 420,
            "cache_read_input_tokens": 900, "cache_creation_input_tokens": 100,
        },
        duration_ms=2000,
        cost_usd=0.0123,
        success=True,
    )
    payload = pa.parse_cost(meta)
    assert payload is not None
    assert payload["usage"]["cache_read_input_tokens"] == 900
    assert payload["usage"]["cache_creation_input_tokens"] == 100
    assert "cost_usd" not in payload["usage"]
    assert payload["costUsd"] == 0.0123
    assert payload["durationMs"] == 2000
    assert payload["success"] is True


def test_cost_payload_omits_costusd_when_not_supplied():
    payload = pa.parse_cost(pa.cost_metadata({"input_tokens": 10, "output_tokens": 5}, duration_ms=15))
    assert payload is not None
    assert "costUsd" not in payload
    assert "success" not in payload


# ── confidence-v1 ────────────────────────────────────────────────────────────


def test_confidence_metadata_minimal():
    meta = pa.confidence_metadata(0.7, success=True)
    assert set(meta) == {pa.CONFIDENCE_EXT_URI}
    assert pa.parse_confidence(meta) == {"confidence": 0.7, "success": True}


def test_confidence_includes_explanation_and_success_false():
    payload = pa.parse_confidence(pa.confidence_metadata(0.9, explanation="sure but wrong", success=False))
    assert payload["confidence"] == 0.9
    assert payload["explanation"] == "sure but wrong"
    assert payload["success"] is False


# ── worldstate-delta-v1 ──────────────────────────────────────────────────────


def test_worldstate_delta_round_trip():
    deltas = [
        {"domain": "board", "path": "data.backlog", "op": "inc", "value": 1},
        {"domain": "board", "path": "data.status", "op": "set", "value": "open"},
    ]
    meta = pa.worldstate_delta_metadata(deltas)
    assert set(meta) == {pa.WORLDSTATE_DELTA_EXT_URI}
    assert pa.parse_worldstate_delta(meta) == {"deltas": deltas}


# ── tool-call-v1 ─────────────────────────────────────────────────────────────


def test_tool_call_round_trip():
    meta = pa.tool_call_metadata("call_1", "file_bug", "completed", result="BUG-12")
    assert set(meta) == {pa.TOOL_CALL_EXT_URI}
    assert pa.parse_tool_call(meta) == {
        "toolCallId": "call_1",
        "name": "file_bug",
        "phase": "completed",
        "result": "BUG-12",
    }


# ── merge + isolation ────────────────────────────────────────────────────────


def test_merge_extension_metadata_combines_fragments():
    merged = pa.merge_extension_metadata(
        pa.cost_metadata({"input_tokens": 1, "output_tokens": 1}, cost_usd=0.01),
        pa.confidence_metadata(0.92),
    )
    assert set(merged) == {pa.COST_EXT_URI, pa.CONFIDENCE_EXT_URI}
    assert pa.parse_cost(merged)["costUsd"] == 0.01
    assert pa.parse_confidence(merged)["confidence"] == 0.92


def test_parse_helpers_read_only_their_own_uri_key():
    # A metadata map carrying only cost yields cost, and nothing for the others.
    meta = pa.cost_metadata({"input_tokens": 1, "output_tokens": 1})
    assert pa.parse_cost(meta) is not None
    assert pa.parse_confidence(meta) is None
    assert pa.parse_worldstate_delta(meta) is None
    assert pa.parse_tool_call(meta) is None


def test_parse_helpers_tolerate_none_and_empty():
    for m in (None, {}, {"unrelated": 1}):
        assert pa.parse_cost(m) is None
        assert pa.parse_tool_call(m) is None
