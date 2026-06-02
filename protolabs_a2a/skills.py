"""protoLabs A2A structured skill outputs — schema-enforced DataPart conventions.

A skill that must return machine-parseable output declares a JSON Schema. The
**runtime** (each agent's executor — protoAgent, workstacean, jon) is what forces
the model to fill that schema, via a forced tool call, and runs any repair retry:
the model invocation is inherently runtime-local (a different LLM stack per agent,
not mirrorable byte-for-byte) and deliberately stays OUT of this package — see
ADR-0006 + protoAgent#476 / protoWorkstacean#756.

This module owns only the LLM-free, mirrorable conventions:

  - ``submit_skill_tool(skill_id, schema)`` → the OpenAI-style function-tool spec
    the executor binds with ``tool_choice`` forced (pure transform of the schema).
  - ``validate_skill_args(args, schema)`` → JSON-Schema validation of the model's
    returned tool args; returns a list of human-readable error strings (``[]`` =
    valid). The executor repair-retries on a non-empty list, feeding the errors
    back to the model.
  - ``skill_result_mime(name)`` → the ``metadata.mimeType`` for a skill's
    structured result, in the protoLabs vendor form (matches the extension MIMEs).
  - ``emit_skill_result(obj, mime)`` → the wire DataPart (reuses ``parts.data_part``).
  - ``parse_skill_result(part, mime=None)`` → the typed payload iff the part matches.

Mirror ``@protolabs/a2a`` (TS) byte-for-byte: pure dict in / dict out, no
``a2a-sdk`` runtime objects, no model client — exactly like ``parts.py`` +
``extensions.py``.
"""

from __future__ import annotations

from typing import Any

from .parts import data_part, read_data

# A skill result rides as a custom DataPart whose ``metadata.mimeType`` is the
# protoLabs vendor MIME for that skill's schema version, e.g.
# ``market-review-v1`` → ``application/vnd.protolabs.market-review-v1+json`` —
# the same form as the cost-v1 / confidence-v1 extension MIMEs.
_SKILL_RESULT_MIME_FMT = "application/vnd.protolabs.{name}+json"
_VENDOR_PREFIX = "application/vnd.protolabs."

# The forced tool the executor binds is named ``submit_<skill_id>``; binding it
# with ``tool_choice`` forced makes the model emit args matching the schema
# instead of free-form prose.
_TOOL_PREFIX = "submit_"


def skill_tool_name(skill_id: str) -> str:
    """The forced tool name for a skill (``submit_<skill_id>``)."""
    return f"{_TOOL_PREFIX}{skill_id}"


def submit_skill_tool(
    skill_id: str,
    schema: dict[str, Any],
    *,
    description: str | None = None,
) -> dict[str, Any]:
    """Build the OpenAI-style function-tool spec for a skill's output schema.

    The executor binds this tool and forces ``tool_choice`` to it, so the model
    must return args matching ``schema`` (the enforcement mechanism — see module
    docstring; ``response_format`` is NOT used, our reasoning backend ignores it).
    ``schema`` becomes the tool ``parameters`` verbatim.
    """
    return {
        "type": "function",
        "function": {
            "name": skill_tool_name(skill_id),
            "description": (
                description
                or f"Return the {skill_id} result. Fill every required field; "
                "respond via this tool only."
            ),
            "parameters": schema,
        },
    }


def skill_result_mime(name: str) -> str:
    """The ``metadata.mimeType`` for a skill result.

    ``name`` is the schema-version label (e.g. ``"market-review-v1"``); the result
    rides as ``application/vnd.protolabs.<name>+json``.
    """
    return _SKILL_RESULT_MIME_FMT.format(name=name)


def validate_skill_args(
    args: Any, schema: dict[str, Any]
) -> list[str]:
    """Validate model-returned tool args against ``schema`` (JSON Schema).

    Returns a list of human-readable error strings — empty means valid. LLM-free;
    the executor uses a non-empty result to trigger a repair retry (feeding the
    errors back to the model). Picks the validator dialect from the schema's
    ``$schema`` (defaults to the latest), so draft-07 and 2020-12 schemas both work.
    """
    if not isinstance(schema, dict):
        return ["schema must be a JSON Schema object"]
    from jsonschema import validators

    validator_cls = validators.validator_for(schema)
    try:
        validator_cls.check_schema(schema)
    except Exception as exc:  # noqa: BLE001 — surface a malformed schema clearly
        return [f"invalid schema: {exc}"]

    validator = validator_cls(schema)
    errors = sorted(validator.iter_errors(args), key=lambda e: list(e.absolute_path))
    return [
        f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}"
        for e in errors
    ]


def emit_skill_result(obj: Any, mime: str) -> dict[str, Any]:
    """Wrap a validated skill-result object as a wire DataPart (``parts.data_part``)."""
    return data_part(obj, mime)


def parse_skill_result(part: dict[str, Any], mime: str | None = None) -> Any:
    """Return the payload of a skill-result DataPart, or ``None``.

    When ``mime`` is given, matches only that exact ``metadata.mimeType``; otherwise
    matches any ``application/vnd.protolabs.*+json`` data part. Non-data / non-match
    parts return ``None``. Accepts both the member-discriminated 1.0 shape and the
    flattened proto-JSON shape (via ``read_data``).
    """
    part_mime, payload = read_data(part)
    if part_mime is None:
        return None
    if mime is not None:
        return payload if part_mime == mime else None
    return payload if part_mime.startswith(_VENDOR_PREFIX) else None
