"""protolabs-a2a — protoLabs A2A 1.0 conventions on top of ``a2a-sdk``.

A THIN conventions layer: ``a2a-sdk`` owns all protocol mechanics (JSON-RPC,
SSE, task lifecycle, push delivery). This package owns only what is specific to
the protoLabs fleet so every agent (in-process Ava, roxy, ORBIS, pwnDeck,
protoAgent) interoperates byte-for-byte:

  - ``extensions`` — the four custom metadata conventions (cost / confidence /
    worldstate-delta / tool-call): extension-URI constants (the metadata key +
    card declaration), payload types, and ``*_metadata`` / ``parse_*`` helpers.
  - ``parts`` — build / read the A2A 1.0 member-discriminated Part shape.
  - ``agent_card`` — ``build_agent_card`` applying provider, JSONRPC interface,
    extension declarations, and auth schemes.
  - ``auth`` — the ``apiKey`` / ``bearer`` security-scheme builders.
"""

from __future__ import annotations

from .agent_card import (
    PROVIDER_ORGANIZATION,
    PROVIDER_URL,
    build_agent_card,
    jsonrpc_interface,
    protolabs_provider,
)
from .auth import (
    API_KEY_HEADER,
    API_KEY_SCHEME_NAME,
    BEARER_SCHEME_NAME,
    api_key_scheme,
    bearer_scheme,
    security_requirements,
    security_schemes,
)
from .extensions import (
    ALL_EXTENSION_URIS,
    CONFIDENCE_EXT_URI,
    COST_EXT_URI,
    EXTENSION_DESCRIPTIONS,
    TOOL_CALL_EXT_URI,
    WORLDSTATE_DELTA_EXT_URI,
    ConfidencePayload,
    CostPayload,
    CostUsage,
    ToolCallPayload,
    WorldstateDelta,
    WorldstateDeltaPayload,
    confidence_metadata,
    cost_metadata,
    merge_extension_metadata,
    parse_confidence,
    parse_cost,
    parse_tool_call,
    parse_worldstate_delta,
    tool_call_metadata,
    worldstate_delta_metadata,
)
from .parts import (
    DATA_MEDIA_TYPE,
    MIME_KEY,
    data_part,
    part_mime,
    read_data,
    read_text,
    text_part,
)
from .skills import (
    emit_skill_result,
    parse_skill_result,
    skill_result_mime,
    skill_tool_name,
    submit_skill_tool,
    validate_skill_args,
)

__all__ = [
    # parts
    "text_part",
    "data_part",
    "read_text",
    "read_data",
    "part_mime",
    "MIME_KEY",
    "DATA_MEDIA_TYPE",
    # structured skill outputs (LLM-free; runtime does the forced tool-call + repair)
    "submit_skill_tool",
    "skill_tool_name",
    "skill_result_mime",
    "validate_skill_args",
    "emit_skill_result",
    "parse_skill_result",
    # extensions — card URIs (also the metadata key) + descriptions
    "COST_EXT_URI",
    "CONFIDENCE_EXT_URI",
    "WORLDSTATE_DELTA_EXT_URI",
    "TOOL_CALL_EXT_URI",
    "ALL_EXTENSION_URIS",
    "EXTENSION_DESCRIPTIONS",
    # extensions — build metadata fragments
    "cost_metadata",
    "confidence_metadata",
    "worldstate_delta_metadata",
    "tool_call_metadata",
    "merge_extension_metadata",
    # extensions — parse (read a metadata map)
    "parse_cost",
    "parse_confidence",
    "parse_worldstate_delta",
    "parse_tool_call",
    # extensions — payload types
    "CostUsage",
    "CostPayload",
    "ConfidencePayload",
    "WorldstateDelta",
    "WorldstateDeltaPayload",
    "ToolCallPayload",
    # agent card
    "build_agent_card",
    "protolabs_provider",
    "jsonrpc_interface",
    "PROVIDER_ORGANIZATION",
    "PROVIDER_URL",
    # auth
    "security_schemes",
    "security_requirements",
    "api_key_scheme",
    "bearer_scheme",
    "API_KEY_SCHEME_NAME",
    "BEARER_SCHEME_NAME",
    "API_KEY_HEADER",
]
