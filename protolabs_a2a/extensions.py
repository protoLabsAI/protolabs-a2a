"""protoLabs A2A custom extensions — the four fleet-wide metadata conventions.

Each extension contributes a JSON payload to the ``metadata`` map of a core A2A
object (``Message`` / ``Artifact`` / ``Task``), **keyed by the extension URI**.
This is the convention the A2A spec prescribes for extension data:

    docs/topics/extensions.md → Limitations: "Extensions should place custom
    attributes in the `metadata` map present on core data structures."

and the one the official Timestamp extension follows verbatim ("stored in the
metadata for a Message or Artifact, under the Extension URI"). The URI is also
what the agent card declares in ``capabilities.extensions[]`` so a consumer
knows to look for it — the same URI serves as both the card declaration and the
metadata key, with the version encoded in the URI (``…/cost-v1``).

Mirrors the TS reference layer (``@protolabs/a2a``) so the hub and every agent
(in-process Ava, roxy, ORBIS, pwnDeck, protoAgent) interoperate byte-for-byte.

The four extensions
───────────────────
  cost-v1              token usage + duration + cost on a terminal task
  confidence-v1        agent self-reported confidence on a terminal task
  worldstate-delta-v1  observed shared-state mutations on a terminal task
  tool-call-v1         per-tool progress event on a status frame

Where each attaches (guidance — the helpers are location-agnostic):
  - cost / confidence / worldstate-delta are terminal telemetry → merge into the
    final **Artifact.metadata** (or the terminal status **Message.metadata**).
  - tool-call is a streaming progress event → merge into the status update's
    **Message.metadata** (the spec's profile-extension pattern:
    ``TaskStatus.message.metadata[<uri>]``).

Each ``*_metadata`` builder returns a one-key fragment ``{<EXT_URI>: <payload>}``;
merge one or more into an object's metadata (``merge_extension_metadata`` is a
convenience for combining several). Each ``parse_*`` reads a metadata map and
returns the typed payload iff the extension's URI key is present, else ``None`` —
so a consumer routes an object's ``metadata`` by URI.
"""

from __future__ import annotations

from typing import Any, Literal, TypedDict

# ── Card extension URIs — the metadata KEY and capabilities.extensions[].uri ───
# The version is encoded in the URI (…-v1); bump the URI to version an extension.
COST_EXT_URI = "https://proto-labs.ai/a2a/ext/cost-v1"
CONFIDENCE_EXT_URI = "https://proto-labs.ai/a2a/ext/confidence-v1"
WORLDSTATE_DELTA_EXT_URI = "https://proto-labs.ai/a2a/ext/worldstate-delta-v1"
TOOL_CALL_EXT_URI = "https://proto-labs.ai/a2a/ext/tool-call-v1"


# ── Payload shapes ────────────────────────────────────────────────────────────


class CostUsage(TypedDict, total=False):
    input_tokens: int
    output_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int


class CostPayload(TypedDict, total=False):
    usage: CostUsage
    durationMs: int
    costUsd: float
    success: bool


class ConfidencePayload(TypedDict, total=False):
    confidence: float
    explanation: str
    success: bool


class WorldstateDelta(TypedDict):
    domain: str
    path: str
    op: Literal["set", "inc", "push"]
    value: Any


class WorldstateDeltaPayload(TypedDict):
    deltas: list[WorldstateDelta]


class ToolCallPayload(TypedDict, total=False):
    toolCallId: str
    name: str
    phase: Literal["started", "completed", "failed"]
    args: Any
    result: Any
    error: str


# ── cost-v1 ───────────────────────────────────────────────────────────────────


def cost_metadata(
    usage: CostUsage,
    *,
    duration_ms: int | None = None,
    cost_usd: float | None = None,
    success: bool | None = None,
) -> dict[str, Any]:
    """Build a cost-v1 metadata fragment ``{COST_EXT_URI: <payload>}``.

    ``usage`` token counts are required; duration, cost, and success are included
    only when provided. Merge the fragment into a terminal Artifact's (or
    Message's) ``metadata`` map.
    """
    payload: CostPayload = {"usage": usage}
    if duration_ms is not None:
        payload["durationMs"] = duration_ms
    if cost_usd is not None:
        payload["costUsd"] = cost_usd
    if success is not None:
        payload["success"] = success
    return {COST_EXT_URI: payload}


def parse_cost(metadata: dict[str, Any] | None) -> CostPayload | None:
    """Read cost-v1 from an object's ``metadata`` map, or ``None`` if absent."""
    value = metadata.get(COST_EXT_URI) if isinstance(metadata, dict) else None
    return value if isinstance(value, dict) else None


# ── confidence-v1 ─────────────────────────────────────────────────────────────


def confidence_metadata(
    confidence: float,
    *,
    explanation: str | None = None,
    success: bool | None = None,
) -> dict[str, Any]:
    """Build a confidence-v1 metadata fragment ``{CONFIDENCE_EXT_URI: <payload>}``."""
    payload: ConfidencePayload = {"confidence": confidence}
    if explanation:
        payload["explanation"] = explanation
    if success is not None:
        payload["success"] = success
    return {CONFIDENCE_EXT_URI: payload}


def parse_confidence(metadata: dict[str, Any] | None) -> ConfidencePayload | None:
    """Read confidence-v1 from an object's ``metadata`` map, or ``None``."""
    value = metadata.get(CONFIDENCE_EXT_URI) if isinstance(metadata, dict) else None
    return value if isinstance(value, dict) else None


# ── worldstate-delta-v1 ───────────────────────────────────────────────────────


def worldstate_delta_metadata(deltas: list[WorldstateDelta]) -> dict[str, Any]:
    """Build a worldstate-delta-v1 metadata fragment wrapping ``deltas``."""
    return {WORLDSTATE_DELTA_EXT_URI: {"deltas": list(deltas)}}


def parse_worldstate_delta(
    metadata: dict[str, Any] | None,
) -> WorldstateDeltaPayload | None:
    """Read worldstate-delta-v1 from an object's ``metadata`` map, or ``None``."""
    value = (
        metadata.get(WORLDSTATE_DELTA_EXT_URI) if isinstance(metadata, dict) else None
    )
    return value if isinstance(value, dict) else None


# ── tool-call-v1 ──────────────────────────────────────────────────────────────


def tool_call_metadata(
    tool_call_id: str,
    name: str,
    phase: Literal["started", "completed", "failed"],
    *,
    args: Any = None,
    result: Any = None,
    error: str | None = None,
) -> dict[str, Any]:
    """Build a tool-call-v1 metadata fragment for a per-tool progress event.

    Merge into the status update's ``Message.metadata`` on the streaming frame.
    """
    payload: ToolCallPayload = {"toolCallId": tool_call_id, "name": name, "phase": phase}
    if args is not None:
        payload["args"] = args
    if result is not None:
        payload["result"] = result
    if error is not None:
        payload["error"] = error
    return {TOOL_CALL_EXT_URI: payload}


def parse_tool_call(metadata: dict[str, Any] | None) -> ToolCallPayload | None:
    """Read tool-call-v1 from an object's ``metadata`` map, or ``None``."""
    value = metadata.get(TOOL_CALL_EXT_URI) if isinstance(metadata, dict) else None
    return value if isinstance(value, dict) else None


# ── helpers ───────────────────────────────────────────────────────────────────


def merge_extension_metadata(*fragments: dict[str, Any]) -> dict[str, Any]:
    """Merge one or more ``*_metadata`` fragments into a single metadata map.

    A convenience for attaching several extensions at once, e.g.::

        artifact.metadata = merge_extension_metadata(
            cost_metadata(usage, cost_usd=0.01),
            confidence_metadata(0.92),
        )

    Later fragments win on key collision (each extension owns its own URI key, so
    a collision only happens when the same extension is passed twice).
    """
    merged: dict[str, Any] = {}
    for fragment in fragments:
        merged.update(fragment)
    return merged


# Convenience: all four card-extension URIs, in the canonical order.
ALL_EXTENSION_URIS = (
    COST_EXT_URI,
    CONFIDENCE_EXT_URI,
    WORLDSTATE_DELTA_EXT_URI,
    TOOL_CALL_EXT_URI,
)

# Human-readable descriptions for the AgentExtension card declaration.
EXTENSION_DESCRIPTIONS = {
    COST_EXT_URI: "Token usage, duration, and cost for a completed task.",
    CONFIDENCE_EXT_URI: "Agent self-reported confidence for a completed task.",
    WORLDSTATE_DELTA_EXT_URI: "Observed shared-state mutations for a completed task.",
    TOOL_CALL_EXT_URI: "Per-tool progress events emitted on status frames.",
}
