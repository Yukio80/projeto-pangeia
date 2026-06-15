from __future__ import annotations

import json
from unittest.mock import patch, AsyncMock

import pytest
import httpx

from pangeia.mcp_server import (
    handle_call_tool,
    _tool_status,
    _tool_economy,
    _tool_governance,
    _tool_culture,
    _tool_collective_memory,
    _tool_technology,
    _tool_news,
    _tool_agent_sample,
    _tool_run_ticks,
    _tool_register_bot,
)


SAMPLE_STATUS = {
    "running": True,
    "tick": 150,
    "alive_count": 280,
    "dead_count": 20,
    "agent_count": 300,
}

SAMPLE_SUMMARY = {
    "tick": 150,
    "economy": {"gdp": 15000.0, "inequality": 0.35},
    "governance": {"stability": 0.72},
    "technology": {"era": "Industrial", "score": 450.0},
}

SAMPLE_ECONOMY = {
    "gdp": 15000.0,
    "inflation": 0.03,
    "employment": 0.88,
    "companies": 42,
    "inequality": 0.35,
    "prices": {"energy": 5.0, "food": 3.0},
}

SAMPLE_GOVERNANCE = {
    "government_type": "democracy",
    "laws": 12,
    "stability": 0.72,
    "legitimacy": 0.65,
    "tax_rate": 0.10,
    "officials": 5,
}

SAMPLE_CULTURE = {
    "religion": {
        "religions": [{"name": "Order of the Sun", "followers": 120, "influence": 0.6}],
    },
    "memes": {"memes": [{"id": "m1", "content": "Cooperation pays"}]},
}

SAMPLE_IDEOLOGIES = {
    "progressivism": {"share": 0.45, "adherents": 130},
    "conservatism": {"share": 0.30, "adherents": 85},
}

SAMPLE_CIVILIZATION = {
    "religiosity": 0.25,
    "militarism": 0.45,
    "individualism": 0.70,
    "traditionalism": 0.55,
    "innovation": 0.60,
    "pluralism": 0.80,
}

SAMPLE_COLLECTIVE_MEMORY = {
    "by_narrative_type": {
        "foundational": [{"title": "Founding", "dominance": 0.8}],
        "reformist": [{"title": "Reform", "dominance": 0.4}],
        "myth": [{"title": "The Great Founding", "dominance": 0.9}],
    },
    "volatility": {"score": 0.22, "regime": "instável"},
    "identity": SAMPLE_CIVILIZATION,
    "actor_details": [{"actor_id": "a1", "role": "governor"}],
}

SAMPLE_TECH = {
    "era": "Industrial",
    "score": 450.0,
    "discovered_count": 8,
    "total_count": 26,
}

SAMPLE_TREE = [
    {"id": "t1", "name": "Agriculture", "discovered": True, "era": "Tribal"},
    {"id": "t2", "name": "Writing", "discovered": True, "era": "Tribal"},
    {"id": "t3", "name": "Steam Engine", "discovered": False, "era": "Industrial"},
]

SAMPLE_NEWS = {
    "total": 3,
    "articles": [
        {"id": "n1", "headline": "GDP rises", "category": "economy", "severity": "medium", "tick": 148},
        {"id": "n2", "headline": "New tech discovered", "category": "technology", "severity": "high", "tick": 149},
    ],
}

SAMPLE_AGENTS_LIST = {
    "total": 10,
    "alive": 8,
    "dead": 2,
    "agents": [
        {"agent_id": "a0001", "name": "Agent1", "agent_class": "Citizen"},
        {"agent_id": "a0002", "name": "Agent2", "agent_class": "Entrepreneur"},
    ],
}

SAMPLE_AGENT_DETAIL = {
    "agent_id": "a0001",
    "name": "Agent1",
    "agent_class": "Citizen",
    "wealth": 150.0,
    "employer_id": None,
    "health": 1.0,
    "age": 45,
    "alive": True,
    "temperament": {"extraversion": 0.5, "openness": 0.7},
    "archetype": "Sage",
    "psychological_needs": {"autonomy": 0.6, "competence": 0.7, "belonging": 0.5},
}

SAMPLE_AUDIT_RANGE = [
    {"tick": 151, "event_type": "economy", "data": {"gdp_delta": 50}},
    {"tick": 152, "event_type": "governance", "data": {"new_law": "tax_reform"}},
]

SAMPLE_METRICS_HISTORY = [{"gdp": 14000 + i * 50, "inequality": 0.35} for i in range(20)]


@pytest.fixture
def mock_api():
    """Mock all httpx.AsyncClient HTTP calls with default responses."""

    async def mock_get(url: str):
        path = url.split("?")[0]
        if path == "/status":
            return httpx.Response(200, json=SAMPLE_STATUS)
        if path == "/summary":
            return httpx.Response(200, json=SAMPLE_SUMMARY)
        if path == "/economy":
            return httpx.Response(200, json=SAMPLE_ECONOMY)
        if path == "/governance":
            return httpx.Response(200, json=SAMPLE_GOVERNANCE)
        if path == "/culture":
            return httpx.Response(200, json=SAMPLE_CULTURE)
        if path == "/ideologies":
            return httpx.Response(200, json=SAMPLE_IDEOLOGIES)
        if path == "/civilization":
            return httpx.Response(200, json=SAMPLE_CIVILIZATION)
        if path == "/collective_memory":
            return httpx.Response(200, json=SAMPLE_COLLECTIVE_MEMORY)
        if path == "/technology":
            return httpx.Response(200, json=SAMPLE_TECH)
        if path == "/technology/tree":
            return httpx.Response(200, json=SAMPLE_TREE)
        if path == "/news/latest":
            return httpx.Response(200, json=SAMPLE_NEWS)
        if path == "/agents":
            return httpx.Response(200, json=SAMPLE_AGENTS_LIST)
        if path == "/metrics/history":
            return httpx.Response(200, json=SAMPLE_METRICS_HISTORY)
        if url.startswith("/audit/events/range"):
            return httpx.Response(200, json=SAMPLE_AUDIT_RANGE)
        # Agent detail by ID
        if path.startswith("/agents/") and len(path) > 9:
            return httpx.Response(200, json=SAMPLE_AGENT_DETAIL)
        return httpx.Response(404, json={"detail": "Not found"})

    async def mock_post(url: str, json=None):
        path = url.split("?")[0]
        if path == "/simulation/start":
            return httpx.Response(200, json={"status": "started"})
        if path == "/bot/register":
            return httpx.Response(200, json={"agent_id": "ext_bot_001", "status": "registered"})
        return httpx.Response(404, json={"detail": "Not found"})

    with patch("pangeia.mcp_server.client.get", AsyncMock(side_effect=mock_get)):
        with patch("pangeia.mcp_server.client.post", AsyncMock(side_effect=mock_post)):
            yield


def _parse_result(result):
    assert len(result) == 1
    assert result[0].type == "text"
    return json.loads(result[0].text)


# ─── Active API tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_simulation_status_returns_valid_structure(mock_api):
    result = await _tool_status({})
    data = _parse_result(result)
    assert data["tick"] == 150
    assert data["alive_population"] == 280
    assert data["gdp"] == 15000.0
    assert data["political_stability"] == 0.72
    assert data["technological_era"] == "Industrial"
    assert data["historical_regime"] == "instável"
    assert "civilization_identity" in data


@pytest.mark.asyncio
async def test_get_economy_snapshot_returns_valid_structure(mock_api):
    result = await _tool_economy({})
    data = _parse_result(result)
    assert data["gdp"] == 15000.0
    assert data["inflation"] == 0.03
    assert data["active_companies"] == 42
    assert len(data["recent_history"]) == 20


@pytest.mark.asyncio
async def test_get_governance_state_returns_valid_structure(mock_api):
    result = await _tool_governance({})
    data = _parse_result(result)
    assert data["government_type"] == "democracy"
    assert data["active_laws"] == 12
    assert data["stability"] == 0.72


@pytest.mark.asyncio
async def test_get_culture_and_ideology_returns_valid_structure(mock_api):
    result = await _tool_culture({})
    data = _parse_result(result)
    assert "religions" in data
    assert "ideologies" in data
    assert "progressivism" in data["ideologies"]
    assert data["ideologies"]["progressivism"]["share"] == 0.45
    assert "civilization_identity" in data


@pytest.mark.asyncio
async def test_get_collective_memory_returns_valid_structure(mock_api):
    result = await _tool_collective_memory({})
    data = _parse_result(result)
    assert "myths" in data
    assert "volatility" in data
    assert data["volatility"]["regime"] == "instável"
    assert "narratives_by_type" in data
    assert data["actor_count"] == 1


@pytest.mark.asyncio
async def test_get_technology_tree_returns_valid_structure(mock_api):
    result = await _tool_technology({})
    data = _parse_result(result)
    assert data["current_era"] == "Industrial"
    assert data["discovered_count"] == 8
    assert data["total_techs"] == 26
    assert len(data["discovered_technologies"]) == 2
    assert len(data["researchable_technologies"]) == 1


@pytest.mark.asyncio
async def test_get_news_feed_returns_valid_structure(mock_api):
    result = await _tool_news({})
    data = _parse_result(result)
    assert data["total_articles"] == 3
    assert len(data["latest_articles"]) == 2
    assert data["latest_articles"][0]["headline"] == "GDP rises"


@pytest.mark.asyncio
async def test_get_agent_sample_returns_agents(mock_api):
    result = await _tool_agent_sample({"sample_size": "5"})
    data = _parse_result(result)
    assert data["sample_size"] == 2
    assert len(data["agents"]) == 2
    assert data["agents"][0]["agent_class"] == "Citizen"
    assert "personality" in data["agents"][0]


@pytest.mark.asyncio
async def test_get_agent_sample_filters_by_class(mock_api):
    result = await _tool_agent_sample({"agent_class": "Citizen", "sample_size": "10"})
    data = _parse_result(result)
    assert data["sample_size"] == 1


@pytest.mark.asyncio
async def test_get_agent_sample_respects_max_size(mock_api):
    result = await _tool_agent_sample({"sample_size": "999"})
    data = _parse_result(result)
    # max is 50; but we only have 2 agents in mock
    assert data["sample_size"] == 2


@pytest.mark.asyncio
async def test_run_simulation_ticks_advances_and_returns_delta(mock_api):
    """Override mock to simulate advancing tick counter."""
    tick_counter = [150]

    async def advancing_get(url: str):
        path = url.split("?")[0]
        if path == "/status":
            tick_counter[0] += 1
            return httpx.Response(200, json={**SAMPLE_STATUS, "tick": tick_counter[0]})
        if path == "/summary":
            return httpx.Response(200, json=SAMPLE_SUMMARY)
        if path == "/audit/events/range":
            return httpx.Response(200, json=SAMPLE_AUDIT_RANGE)
        return await mock_get_default(url)

    async def mock_get_default(url: str):
        """Reuse the mock_api pattern for non-status endpoints."""
        path = url.split("?")[0]
        if path == "/status":
            return httpx.Response(200, json=SAMPLE_STATUS)
        if path == "/summary":
            return httpx.Response(200, json=SAMPLE_SUMMARY)
        if path == "/economy":
            return httpx.Response(200, json=SAMPLE_ECONOMY)
        if path == "/governance":
            return httpx.Response(200, json=SAMPLE_GOVERNANCE)
        if path == "/culture":
            return httpx.Response(200, json=SAMPLE_CULTURE)
        if path == "/ideologies":
            return httpx.Response(200, json=SAMPLE_IDEOLOGIES)
        if path == "/civilization":
            return httpx.Response(200, json=SAMPLE_CIVILIZATION)
        if path == "/collective_memory":
            return httpx.Response(200, json=SAMPLE_COLLECTIVE_MEMORY)
        if path == "/technology":
            return httpx.Response(200, json=SAMPLE_TECH)
        if path == "/technology/tree":
            return httpx.Response(200, json=SAMPLE_TREE)
        if path == "/news/latest":
            return httpx.Response(200, json=SAMPLE_NEWS)
        if path == "/agents":
            return httpx.Response(200, json=SAMPLE_AGENTS_LIST)
        if path == "/metrics/history":
            return httpx.Response(200, json=SAMPLE_METRICS_HISTORY)
        if url.startswith("/audit/events/range"):
            return httpx.Response(200, json=SAMPLE_AUDIT_RANGE)
        if path.startswith("/agents/") and len(path) > 9:
            return httpx.Response(200, json=SAMPLE_AGENT_DETAIL)
        return httpx.Response(404, json={"detail": "Not found"})

    with patch("pangeia.mcp_server.client.get", AsyncMock(side_effect=advancing_get)):
        with patch("pangeia.mcp_server.client.post", AsyncMock(return_value=httpx.Response(200, json={}))):
            result = await _tool_run_ticks({"ticks": "5"})
    data = _parse_result(result)
    assert "ticks_executed" in data
    assert "tick_from" in data
    assert "tick_to" in data
    assert "events_in_interval" in data


@pytest.mark.asyncio
async def test_register_external_bot_returns_sandbox(mock_api):
    result = await _tool_register_bot({"bot_name": "TestBot", "strategy": "Analyst"})
    data = _parse_result(result)
    assert data["bot_id"] == "ext_bot_001"
    assert data["citizenship"] == "SANDBOX"
    assert "rate_limit" in data


# ─── Inactive API tests ────────────────────────────────────────


def _make_inactive_mock():
    """Return mock GET/POST that simulate an inactive (not running) API."""

    async def mock_get(url: str):
        path = url.split("?")[0]
        if path == "/status":
            return httpx.Response(200, json={"running": False, "tick": 0, "alive_count": 0, "agent_count": 0})
        return httpx.Response(200, json={})

    async def mock_post(url: str, json=None):
        return httpx.Response(200, json={})

    return mock_get, mock_post


@pytest.mark.asyncio
async def test_status_returns_error_when_sim_not_active():
    mock_get, mock_post = _make_inactive_mock()
    with patch("pangeia.mcp_server.client.get", AsyncMock(side_effect=mock_get)):
        with patch("pangeia.mcp_server.client.post", AsyncMock(side_effect=mock_post)):
            result = await handle_call_tool("get_simulation_status", {})
    data = _parse_result(result)
    assert "error" in data
    assert "Simulação não está ativa" in data["error"]


@pytest.mark.asyncio
async def test_economy_returns_error_when_sim_not_active():
    mock_get, mock_post = _make_inactive_mock()
    with patch("pangeia.mcp_server.client.get", AsyncMock(side_effect=mock_get)):
        with patch("pangeia.mcp_server.client.post", AsyncMock(side_effect=mock_post)):
            result = await handle_call_tool("get_economy_snapshot", {})
    data = _parse_result(result)
    assert "error" in data
    assert "Simulação não está ativa" in data["error"]


@pytest.mark.asyncio
async def test_register_bot_returns_error_when_sim_not_active():
    mock_get, mock_post = _make_inactive_mock()
    with patch("pangeia.mcp_server.client.get", AsyncMock(side_effect=mock_get)):
        with patch("pangeia.mcp_server.client.post", AsyncMock(side_effect=mock_post)):
            result = await handle_call_tool("register_external_bot", {"bot_name": "Bot", "strategy": "Liberal"})
    data = _parse_result(result)
    assert "error" in data
    assert "Simulação não está ativa" in data["error"]


# ─── API connection error tests ─────────────────────────────────


@pytest.mark.asyncio
async def test_returns_connection_error_when_api_unreachable():
    with patch("pangeia.mcp_server.client.get", AsyncMock(side_effect=httpx.ConnectError("Connection refused"))):
        with patch("pangeia.mcp_server.client.post", AsyncMock(side_effect=httpx.ConnectError("Connection refused"))):
            result = await handle_call_tool("get_simulation_status", {})
    data = _parse_result(result)
    assert "error" in data
    assert "Não foi possível conectar" in data["error"]


# ─── run_simulation_ticks does not restart if already running ──


@pytest.mark.asyncio
async def test_run_simulation_ticks_does_not_restart_when_already_running():
    call_count = {"post_start": 0}
    tick_counter = [150]

    async def advancing_get(url: str):
        path = url.split("?")[0]
        if path == "/status":
            tick_counter[0] += 1
            return httpx.Response(200, json={**SAMPLE_STATUS, "tick": tick_counter[0]})
        if path == "/summary":
            return httpx.Response(200, json=SAMPLE_SUMMARY)
        if path == "/audit/events/range":
            return httpx.Response(200, json=SAMPLE_AUDIT_RANGE)
        return httpx.Response(200, json={})

    async def mock_post(url: str, json=None):
        if "/simulation/start" in url:
            call_count["post_start"] += 1
        return httpx.Response(200, json={})

    with patch("pangeia.mcp_server.client.get", AsyncMock(side_effect=advancing_get)):
        with patch("pangeia.mcp_server.client.post", AsyncMock(side_effect=mock_post)):
            result = await _tool_run_ticks({"ticks": "5"})
    data = _parse_result(result)
    assert "ticks_executed" in data
    # Should NOT have called /simulation/start since status says running=True
    assert call_count["post_start"] == 0
