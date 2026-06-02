"""Smoke tests for the agent-card + auth conventions (require a2a-sdk types)."""

from __future__ import annotations

import protolabs_a2a as pa
from a2a.types import AgentSkill


def test_build_agent_card_applies_fleet_conventions():
    card = pa.build_agent_card(
        name="protoagent",
        description="test agent",
        url="http://protoagent:7870/a2a",
        version="1.0.0",
        skills=[AgentSkill(id="chat", name="Chat", description="chat", tags=["chat"])],
    )
    assert card.name == "protoagent"
    assert card.provider.organization == pa.PROVIDER_ORGANIZATION == "protoLabs AI"
    assert card.provider.url == pa.PROVIDER_URL
    # all four extensions declared by default
    declared = {e.uri for e in card.capabilities.extensions}
    assert declared == set(pa.ALL_EXTENSION_URIS)
    # apiKey always present; bearer absent unless requested
    assert pa.API_KEY_SCHEME_NAME in card.security_schemes
    assert pa.BEARER_SCHEME_NAME not in card.security_schemes


def test_build_agent_card_with_bearer_and_subset_extensions():
    card = pa.build_agent_card(
        name="roxy",
        description="portfolio mgr",
        url="http://roxy:7870/a2a",
        version="0.1.0",
        skills=[AgentSkill(id="manage", name="Manage", description="manage", tags=["ops"])],
        extension_uris=[pa.COST_EXT_URI, pa.CONFIDENCE_EXT_URI],
        bearer=True,
    )
    declared = {e.uri for e in card.capabilities.extensions}
    assert declared == {pa.COST_EXT_URI, pa.CONFIDENCE_EXT_URI}
    assert pa.BEARER_SCHEME_NAME in card.security_schemes
