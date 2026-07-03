# protolabs-a2a

A **thin** Python conventions layer on top of the official
[`a2a-sdk`](https://pypi.org/project/a2a-sdk/) (A2A spec 1.0). `a2a-sdk` owns
every piece of protocol mechanics — JSON-RPC dispatch, SSE streaming, the task
lifecycle, push-notification delivery. This package owns **only** what is
specific to the protoLabs fleet, so every agent (in-process Ava, roxy, ORBIS,
pwnDeck, protoAgent) interoperates byte-for-byte.

> It is the Python mirror of the TypeScript reference layer **`@protolabs/a2a`**,
> which lives in **protoWorkstacean** (`packages/a2a` / the `@protolabs/a2a`
> workspace). The wire contract below — extension URIs, payload shapes, and the
> metadata convention — is shared verbatim across both. Change one, change the other.

## Install

```bash
pip install git+https://github.com/protoLabsAI/protolabs-a2a.git
```

Or pin it as a git dependency (e.g. in `pyproject.toml`):

```toml
dependencies = [
    "protolabs-a2a @ git+https://github.com/protoLabsAI/protolabs-a2a.git",
]
```

Requires Python `>=3.11` and pulls in `a2a-sdk>=1.1`.

## What's in it

| Module | Responsibility |
| --- | --- |
| `parts` | Build / read the A2A 1.0 member-discriminated `Part` shape (generic content parts). |
| `extensions` | The four custom metadata conventions: extension-URI constants (the metadata key + card declaration), payload types, `*_metadata` / `parse_*`. |
| `agent_card` | `build_agent_card(...)` — provider, JSONRPC interface, extension declarations, auth schemes. |
| `auth` | The `apiKey` (`X-API-Key`) and `bearer` security-scheme builders. |

## Public API

Everything below is exported at the top level (`import protolabs_a2a as pa`):

**Parts** — `text_part`, `data_part`, `read_text`, `read_data`, `part_mime`,
`MIME_KEY`, `DATA_MEDIA_TYPE`

**Extensions — URIs** (the metadata key **and** the card declaration) —
`COST_EXT_URI`, `CONFIDENCE_EXT_URI`, `WORLDSTATE_DELTA_EXT_URI`,
`TOOL_CALL_EXT_URI`, `ALL_EXTENSION_URIS`, `EXTENSION_DESCRIPTIONS`

**Extensions — build metadata fragments** — `cost_metadata`,
`confidence_metadata`, `worldstate_delta_metadata`, `tool_call_metadata`,
`merge_extension_metadata`

**Extensions — parse** (read a metadata map) — `parse_cost`, `parse_confidence`,
`parse_worldstate_delta`, `parse_tool_call`

**Extensions — payload types** — `CostUsage`, `CostPayload`, `ConfidencePayload`,
`WorldstateDelta`, `WorldstateDeltaPayload`, `ToolCallPayload`

**Agent card** — `build_agent_card`, `protolabs_provider`, `jsonrpc_interface`,
`PROVIDER_ORGANIZATION`, `PROVIDER_URL`

**Auth** — `security_schemes`, `security_requirements`, `api_key_scheme`,
`bearer_scheme`, `API_KEY_SCHEME_NAME`, `BEARER_SCHEME_NAME`, `API_KEY_HEADER`

## Extension data: the metadata convention

Each extension contributes its payload to the **`metadata` map** of a core A2A
object, **keyed by the extension URI**:

```json
"metadata": {
  "https://proto-labs.ai/a2a/ext/cost-v1": { "usage": { "input_tokens": 1500, "output_tokens": 420 }, "costUsd": 0.01, "success": true }
}
```

This is the convention the A2A spec prescribes — *"Extensions should place custom
attributes in the `metadata` map present on core data structures"*
([extensions.md → Limitations](https://a2a-protocol.org/latest/topics/extensions/)) —
and the one the official Timestamp extension follows verbatim. The same URI is
both the metadata key and the `capabilities.extensions[].uri` card declaration,
with the version encoded in the URI (`…-v1`).

Each `*_metadata` helper returns a one-key fragment `{<EXT_URI>: <payload>}`;
merge it into the target object's `metadata` (`merge_extension_metadata` combines
several). `parse_*` reads a metadata map and returns the payload iff its URI key
is present. **Where each attaches:**

| Extension | URI (metadata key + card declaration) | Attaches to |
| --- | --- | --- |
| cost-v1 | `https://proto-labs.ai/a2a/ext/cost-v1` | terminal `Artifact.metadata` |
| confidence-v1 | `https://proto-labs.ai/a2a/ext/confidence-v1` | terminal `Artifact.metadata` |
| worldstate-delta-v1 | `https://proto-labs.ai/a2a/ext/worldstate-delta-v1` | terminal `Artifact.metadata` |
| tool-call-v1 | `https://proto-labs.ai/a2a/ext/tool-call-v1` | status-frame `Message.metadata` |

Payload shapes:

- **cost-v1** — `{usage:{input_tokens, output_tokens, cache_creation_input_tokens?, cache_read_input_tokens?}, durationMs?, costUsd?, success?}`
- **confidence-v1** — `{confidence, explanation?, success?}`
- **worldstate-delta-v1** — `{deltas:[{domain, path, op:"set"|"inc"|"push", value}]}`
- **tool-call-v1** — `{toolCallId, name, phase:"started"|"completed"|"failed", args?, result?, error?}`

## Usage

```python
import protolabs_a2a as pa
from a2a.types import AgentSkill

# Build extension metadata fragments and merge them into the terminal Artifact's
# metadata map (each fragment is {<EXT_URI>: <payload>}):
artifact.metadata = pa.merge_extension_metadata(
    pa.cost_metadata({"input_tokens": 1500, "output_tokens": 420}, duration_ms=900, cost_usd=0.01, success=True),
    pa.confidence_metadata(0.92, explanation="high coverage"),
    pa.worldstate_delta_metadata([{"domain": "board", "path": "data.backlog", "op": "inc", "value": 1}]),
)

# A streaming tool-call event rides on the status update's Message.metadata:
status_message.metadata = pa.tool_call_metadata("call_1", "file_bug", "completed", result="BUG-12")

# Parse (returns the typed payload iff the extension's URI key is present, else None):
payload = pa.parse_cost(artifact.metadata)

# Build a 1.0 agent card with the fleet conventions:
card = pa.build_agent_card(
    name="protoagent",
    description="…",
    url="http://protoagent:7870/a2a",
    version="1.0.0",
    skills=[AgentSkill(id="chat", name="Chat", description="…", tags=["chat"])],
    bearer=True,          # advertise the bearer scheme
)
```

The agent owns *which* extensions it emits — pass `extension_uris=[…]` to
`build_agent_card` to declare a subset; it defaults to all four.

> **Generic parts.** `parts` (`text_part`, `data_part`, `read_text`, `read_data`)
> still builds/reads the A2A 1.0 member-discriminated `Part` shape for real
> **content** (and is reused by `skills`). The four extensions above are telemetry
> *about* a task, so they live in `metadata`, not in `parts[]`.
