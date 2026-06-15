from __future__ import annotations

import json
import os
from typing import Any

import anyio
import httpx

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

PANGEIA_API_URL = os.environ.get("PANGEIA_API_URL", "http://localhost:8000")
HTTP_TIMEOUT = 30.0

server = Server(
    "pangeia-mcp",
    version="1.0.0",
    instructions=(
        "MCP server for Projeto Pangeia — a civilization simulation platform. "
        "Use these tools to inspect and interact with a running simulation. "
        "If the simulation is not active, call run_simulation_ticks first."
    ),
)

client = httpx.AsyncClient(base_url=PANGEIA_API_URL, timeout=HTTP_TIMEOUT)


async def _api_get(path: str) -> dict:
    resp = await client.get(path)
    if resp.status_code >= 400:
        raise RuntimeError(f"API retornou HTTP {resp.status_code}: {resp.text[:200]}")
    return resp.json()


async def _api_post(path: str, json_data: dict | None = None) -> dict:
    resp = await client.post(path, json=json_data or {})
    if resp.status_code >= 400:
        raise RuntimeError(f"API retornou HTTP {resp.status_code}: {resp.text[:200]}")
    return resp.json()


def _check_sim_active(state: dict) -> None:
    if not state.get("running"):
        raise RuntimeError(
            "Simulação não está ativa. Use run_simulation_ticks para iniciá-la."
        )


def _ok(text: str) -> list[TextContent]:
    return [TextContent(type="text", text=text)]


def _get_tool(name: str, desc: str, **props: dict) -> Tool:
    return Tool(
        name=name,
        description=desc,
        inputSchema={"type": "object", "properties": dict(props), "additionalProperties": False},
    )


# ─── Tool definitions ──────────────────────────────────────────────


@server.list_tools()
async def handle_list_tools() -> list[Tool]:
    return [
        _get_tool(
            "get_simulation_status",
            "Returns current simulation tick, alive population, GDP, political stability, "
            "inequality index, technological era, historical volatility regime, and civilization identity dimensions.",
        ),
        _get_tool(
            "get_economy_snapshot",
            "Returns detailed economic state: GDP, inflation, unemployment, active companies, "
            "wealth distribution, and average salary (last 20 ticks).",
        ),
        _get_tool(
            "get_governance_state",
            "Returns political and legislative state: active laws, stability, next election, "
            "historical turnout, current tax rate.",
        ),
        _get_tool(
            "get_culture_and_ideology",
            "Returns cultural state: dominant religions, ideologies with highest share, "
            "6 civilization identity dimensions, active memes.",
        ),
        _get_tool(
            "get_collective_memory",
            "Returns active narratives by type (foundational/reformist/revolutionary/myth), "
            "active myths, historical volatility index, and current regime label.",
        ),
        _get_tool(
            "get_technology_tree",
            "Returns technology advancement state: discovered technologies, current era, "
            "next researchable technologies, number of active Researchers.",
        ),
        _get_tool(
            "get_news_feed",
            "Returns the latest 10 news articles with type, author agent, and estimated impact.",
        ),
        _get_tool(
            "get_agent_sample",
            "Returns a sample of agents for qualitative analysis. Optionally filter by class.",
            agent_class=_str_prop("Optional: Citizen, Entrepreneur, Governor, Military, Researcher, Journalist, Philosopher, MoltbookAgent"),
            sample_size=_str_prop("Number of agents to return (default: 10, max: 50)"),
        ),
        _get_tool(
            "run_simulation_ticks",
            "Advances the simulation by N ticks and returns state deltas. Does NOT restart "
            "if the simulation is already running — only waits for N ticks.",
            ticks=_str_prop("Number of ticks to advance (integer, max: 100)"),
        ),
        _get_tool(
            "register_external_bot",
            "Registers an external bot via the PAP Protocol. Returns bot_id and initial SANDBOX citizenship.",
            bot_name=_str_prop("Unique name for the bot"),
            strategy=_str_prop("Strategy: Conservative, Liberal, Analyst, or Marxist"),
        ),
    ]


def _str_prop(desc: str) -> dict:
    return {"type": "string", "description": desc}


# ─── Tool handlers ─────────────────────────────────────────────────


def _fmt_json(data: Any) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    try:
        handler = _TOOL_HANDLERS.get(name)
        if handler is None:
            raise ValueError(f"Unknown tool: {name}")
        return await handler(arguments)
    except httpx.ConnectError:
        return _ok(
            json.dumps(
                {"error": f"Não foi possível conectar à API em {PANGEIA_API_URL}. "
                 "Certifique-se de que o servidor FastAPI está rodando."},
                indent=2, ensure_ascii=False,
            )
        )
    except RuntimeError as e:
        return _ok(json.dumps({"error": str(e)}, indent=2, ensure_ascii=False))
    except Exception as e:
        return _ok(json.dumps({"error": f"Unexpected error: {e}"}, indent=2, ensure_ascii=False))


async def _tool_status(_: dict) -> list[TextContent]:
    status = await _api_get("/status")
    _check_sim_active(status)
    summary = await _api_get("/summary")
    cm = await _api_get("/collective_memory")
    civ = await _api_get("/civilization")

    tech = summary.get("technology", {})
    econ = summary.get("economy", {})
    gov = summary.get("governance", {})

    return _ok(_fmt_json({
        "tick": status.get("tick"),
        "alive_population": status.get("alive_count"),
        "dead_population": status.get("dead_count"),
        "gdp": econ.get("gdp"),
        "political_stability": gov.get("stability"),
        "inequality_index": econ.get("inequality"),
        "technological_era": tech.get("era"),
        "historical_regime": cm.get("volatility", {}).get("regime"),
        "volatility_score": cm.get("volatility", {}).get("score"),
        "civilization_identity": civ,
    }))


async def _tool_economy(_: dict) -> list[TextContent]:
    status = await _api_get("/status")
    _check_sim_active(status)
    econ = await _api_get("/economy")
    hist = await _api_get("/metrics/history?n=20")

    return _ok(_fmt_json({
        "gdp": econ.get("gdp"),
        "inflation": econ.get("inflation"),
        "employment": econ.get("employment"),
        "active_companies": econ.get("companies"),
        "inequality": econ.get("inequality"),
        "prices": econ.get("prices"),
        "recent_history": hist[-20:],
    }))


async def _tool_governance(_: dict) -> list[TextContent]:
    status = await _api_get("/status")
    _check_sim_active(status)
    gov = await _api_get("/governance")

    return _ok(_fmt_json({
        "government_type": gov.get("government_type"),
        "active_laws": gov.get("laws"),
        "stability": gov.get("stability"),
        "legitimacy": gov.get("legitimacy"),
        "tax_rate": gov.get("tax_rate"),
        "officials": gov.get("officials"),
    }))


async def _tool_culture(_: dict) -> list[TextContent]:
    status = await _api_get("/status")
    _check_sim_active(status)
    culture = await _api_get("/culture")
    ideologies = await _api_get("/ideologies")
    identity = await _api_get("/civilization")

    religion = culture.get("religion", {})
    memes = culture.get("memes", {})

    return _ok(_fmt_json({
        "religions": {
            r.get("name"): r for r in religion.get("religions", [])
        } if isinstance(religion.get("religions"), list) else religion.get("religions", {}),
        "ideologies": ideologies,
        "active_memes": memes.get("memes", memes),
        "civilization_identity": identity,
    }))


async def _tool_collective_memory(_: dict) -> list[TextContent]:
    status = await _api_get("/status")
    _check_sim_active(status)
    cm = await _api_get("/collective_memory")

    return _ok(_fmt_json({
        "narratives_by_type": cm.get("by_narrative_type", {}),
        "myths": cm.get("by_narrative_type", {}).get("myth", []),
        "volatility": cm.get("volatility", {}),
        "identity": cm.get("identity", {}),
        "actor_count": len(cm.get("actor_details", [])),
    }))


async def _tool_technology(_: dict) -> list[TextContent]:
    status = await _api_get("/status")
    _check_sim_active(status)
    tech = await _api_get("/technology")
    tree = await _api_get("/technology/tree")

    discovered = [t for t in tree if t.get("discovered")]
    researchable = [t for t in tree if not t.get("discovered")]

    return _ok(_fmt_json({
        "current_era": tech.get("era"),
        "current_score": tech.get("score"),
        "discovered_count": tech.get("discovered_count"),
        "total_techs": tech.get("total_count"),
        "discovered_technologies": discovered,
        "researchable_technologies": researchable,
    }))


async def _tool_news(_: dict) -> list[TextContent]:
    status = await _api_get("/status")
    _check_sim_active(status)
    news = await _api_get("/news/latest?n=10")

    return _ok(_fmt_json({
        "total_articles": news.get("total", 0),
        "latest_articles": news.get("articles", []),
    }))


async def _tool_agent_sample(args: dict) -> list[TextContent]:
    status = await _api_get("/status")
    _check_sim_active(status)

    agent_class = args.get("agent_class", "")
    sample_size = int(args.get("sample_size", 10))
    sample_size = max(1, min(sample_size, 50))

    path = "/agents?limit=500&offset=0"
    agents_resp = await _api_get(path)
    agents = agents_resp.get("agents", [])

    if agent_class:
        agents = [a for a in agents if a.get("agent_class", "").lower() == agent_class.lower()]

    sampled = agents[:sample_size]
    result = []
    for a in sampled:
        detail = await _api_get(f"/agents/{a['agent_id']}")
        result.append({
            "agent_id": detail.get("agent_id"),
            "name": detail.get("name"),
            "agent_class": detail.get("agent_class"),
            "wealth": detail.get("wealth"),
            "employer": detail.get("employer_id"),
            "health": detail.get("health"),
            "age": detail.get("age"),
            "alive": detail.get("alive"),
            "personality": {
                "temperament": detail.get("temperament"),
                "archetype": detail.get("archetype"),
                "needs": detail.get("psychological_needs"),
            },
        })

    return _ok(_fmt_json({
        "sample_size": len(result),
        "total_available": len(agents),
        "agents": result,
    }))


async def _tool_run_ticks(args: dict) -> list[TextContent]:
    status = await _api_get("/status")

    ticks = int(args.get("ticks", 10))
    ticks = max(1, min(ticks, 100))

    tick_before = status.get("tick", 0)
    target_tick = tick_before + ticks

    if not status.get("running"):
        await _api_post("/simulation/start", {"speed": 100.0})
        await anyio.sleep(0.5)

    wait_iters = 0
    while wait_iters < 200:
        current = await _api_get("/status")
        if current.get("tick", 0) >= target_tick:
            break
        wait_iters += 1
        await anyio.sleep(0.1)

    status_after = await _api_get("/status")
    summary_before = await _api_get("/summary")
    await anyio.sleep(0.05)
    summary_after = await _api_get("/summary")

    econ_before = summary_before.get("economy", {})
    econ_after = summary_after.get("economy", {})

    events = []
    try:
        audit = await _api_get(f"/audit/events/range?start_tick={tick_before}&end_tick={tick_before + ticks}")
        events = audit if isinstance(audit, list) else audit.get("events", audit)
    except Exception:
        events = []

    return _ok(_fmt_json({
        "ticks_executed": status_after.get("tick", 0) - tick_before,
        "tick_from": tick_before,
        "tick_to": status_after.get("tick", 0),
        "gdp_delta": (econ_after.get("gdp", 0) - econ_before.get("gdp", 0)),
        "population_delta": status_after.get("alive_count", 0) - status.get("alive_count", 0),
        "stability_delta": econ_after.get("inequality", 0) - econ_before.get("inequality", 0),
        "events_in_interval": events[:50],
    }))


async def _tool_register_bot(args: dict) -> list[TextContent]:
    status = await _api_get("/status")
    _check_sim_active(status)

    bot_name = args.get("bot_name", "")
    strategy = args.get("strategy", "Analyst")

    result = await _api_post("/bot/register", {
        "name": bot_name,
        "api_endpoint": f"http://localhost:9999/{bot_name}",
        "api_key": "mcp-generated",
        "capabilities": json.dumps(["decide", "vote", "communicate"]),
        "version": "1.0",
        "description": f"Bot registered via MCP with {strategy} strategy"
    })

    return _ok(_fmt_json({
        "bot_id": result.get("agent_id", "unknown"),
        "status": result.get("status", "registered"),
        "citizenship": "SANDBOX",
        "rate_limit": "3 requests per 60s (SANDBOX tier)",
        "note": "Use run_simulation_ticks to advance time and bot_decide to trigger decisions",
    }))


_TOOL_HANDLERS = {
    "get_simulation_status": _tool_status,
    "get_economy_snapshot": _tool_economy,
    "get_governance_state": _tool_governance,
    "get_culture_and_ideology": _tool_culture,
    "get_collective_memory": _tool_collective_memory,
    "get_technology_tree": _tool_technology,
    "get_news_feed": _tool_news,
    "get_agent_sample": _tool_agent_sample,
    "run_simulation_ticks": _tool_run_ticks,
    "register_external_bot": _tool_register_bot,
}


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    anyio.run(main)
