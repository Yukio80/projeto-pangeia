from __future__ import annotations

import asyncio
import os
import threading
from typing import Optional, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from pangeia.simulation import Simulation
from pangeia.metrics.tracker import MetricsSnapshot
from pangeia.api.schemas import (
    SimulationStatus, WorldSummary, EconomySummary,
    GovernanceSummary, MetricsSummary, FullSummary,
)

_api_dir = os.path.dirname(os.path.abspath(__file__))
_static_dir = os.path.join(_api_dir, "static")

app = FastAPI(title="Projeto Pangeia API")
app.mount("/static", StaticFiles(directory=_static_dir), name="static")

simulation: Optional[Simulation] = None
sim_thread: Optional[threading.Thread] = None
sim_running: bool = False
sim_speed: float = 1.0

websocket_clients: list[WebSocket] = []
ws_lock = asyncio.Lock()


def get_sim() -> Simulation:
    global simulation
    if simulation is None:
        from pangeia.config import SimulationConfig
        from pangeia.persistence.config import PersistenceConfig
        cfg = SimulationConfig.default()
        cfg.persistence = PersistenceConfig.from_env()
        simulation = Simulation(cfg)
    return simulation


@app.on_event("startup")
async def startup():
    global simulation
    from pangeia.config import SimulationConfig
    from pangeia.persistence.config import PersistenceConfig
    cfg = SimulationConfig.default()
    cfg.persistence = PersistenceConfig.from_env()
    simulation = Simulation(cfg)


@app.get("/")
async def root():
    return {
        "project": "Projeto Pangeia",
        "description": "Laboratório de civilizações artificiais",
        "status": await status(),
    }


@app.get("/dashboard")
async def dashboard():
    return FileResponse(os.path.join(_static_dir, "dashboard.html"))


@app.get("/status")
async def status():
    sim = get_sim()
    return SimulationStatus(
        running=sim_running,
        tick=sim.world.state.tick,
        time=sim.world.state.time,
        agent_count=len(sim.agents),
        alive_count=sum(1 for a in sim.agents.values() if a.state.is_alive),
    )


@app.get("/summary")
async def summary():
    sim = get_sim()
    return sim.summary()


@app.get("/world")
async def world():
    sim = get_sim()
    return sim.world.summary()


@app.get("/economy")
async def economy():
    sim = get_sim()
    return sim.economy.summary()


@app.get("/governance")
async def governance():
    sim = get_sim()
    return sim.governance.summary()


@app.get("/agents")
async def agents_list(limit: int = 100, offset: int = 0):
    sim = get_sim()
    agent_list = list(sim.agents.values())
    page = agent_list[offset:offset + limit]
    return {
        "total": len(agent_list),
        "alive": sum(1 for a in agent_list if a.state.is_alive),
        "agents": [a.summarize() for a in page],
    }


@app.get("/agents/{agent_id}")
async def agent_detail(agent_id: str):
    sim = get_sim()
    agent = sim.get_agent(agent_id)
    if not agent:
        return JSONResponse(status_code=404, content={"error": "Agent not found"})
    return agent.summarize()


@app.get("/metrics")
async def metrics():
    sim = get_sim()
    return sim.metrics.summary()


@app.get("/metrics/history")
async def metrics_history(n: int = 100):
    sim = get_sim()
    return [m.as_dict() for m in sim.metrics.history[-n:]]


@app.get("/events")
async def events():
    sim = get_sim()
    return sim.world.state.events[-50:]


@app.get("/culture")
async def culture():
    sim = get_sim()
    return {
        "beliefs": sim.belief_system.summary(),
        "memes": sim.meme_pool.summarize(),
        "religion": sim.religion_system.summary(),
        "ideologies": sim.ideology_system.summary(),
    }


@app.get("/civilization")
async def civilization():
    sim = get_sim()
    return sim.civilization_index()


@app.get("/ideologies")
async def ideologies():
    sim = get_sim()
    return sim.ideology_system.summary()


@app.get("/diplomacy")
async def diplomacy():
    sim = get_sim()
    return sim.diplomacy.summary()


@app.get("/stratification")
async def stratification():
    sim = get_sim()
    return sim.stratification.summary()


@app.get("/history")
async def history():
    sim = get_sim()
    return sim.narratives.summary()


@app.get("/history/timeline")
async def history_timeline():
    sim = get_sim()
    return sim.narratives.timeline[-100:]


@app.get("/technology")
async def technology():
    sim = get_sim()
    return sim.technology.summary()


@app.get("/technology/tree")
async def technology_tree():
    sim = get_sim()
    return [t.as_dict() for t in sim.technology.technologies.values()]


@app.get("/collective_memory")
async def collective_memory():
    sim = get_sim()
    return sim.collective_memory.summarize()


@app.get("/collective_memory/myths")
async def collective_memory_myths():
    sim = get_sim()
    return [m.as_dict() for m in sim.collective_memory.get_myths()]


@app.post("/bot/register")
async def bot_register(name: str, api_endpoint: str, api_key: str,
                       capabilities: str = "[]", version: str = "1.0",
                       description: str = ""):
    sim = get_sim()
    import json
    try:
        caps = json.loads(capabilities)
    except json.JSONDecodeError:
        caps = [capabilities]
    manifest = {
        "capabilities": caps,
        "version": version,
        "description": description,
    }
    return sim.pap.register(name, api_endpoint, api_key, manifest, sim.world.state.tick)


@app.get("/bot/manifest/{agent_id}")
async def bot_manifest(agent_id: str):
    sim = get_sim()
    return sim.pap.get_manifest(agent_id)


@app.post("/bot/observe/{agent_id}")
async def bot_observe(agent_id: str):
    sim = get_sim()
    return sim.pap.observe(agent_id, sim)


@app.post("/bot/decide/{agent_id}")
async def bot_decide(agent_id: str, nonce: str = ""):
    sim = get_sim()
    observation = sim.pap.observe(agent_id, sim)
    if "error" in observation:
        return observation
    return sim.pap.decide(agent_id, observation, sim, nonce=nonce)


@app.post("/bot/vote/{agent_id}")
async def bot_vote(agent_id: str, proposal_id: str, vote: str, nonce: str = ""):
    sim = get_sim()
    return sim.pap.vote(agent_id, proposal_id, vote, sim, nonce=nonce)


@app.post("/bot/communicate/{agent_id}")
async def bot_communicate(agent_id: str, message: str, channel: str = "public", nonce: str = ""):
    sim = get_sim()
    return sim.pap.communicate(agent_id, message, channel, sim, nonce=nonce)


@app.get("/bot/audit/{agent_id}")
async def bot_audit(agent_id: str, limit: int = 100, offset: int = 0):
    sim = get_sim()
    events = sim.audit_log.get_events(
        aggregate_id=agent_id,
        limit=limit,
        offset=offset,
    )
    return {
        "agent_id": agent_id,
        "total": sim.audit_log.get_event_count(aggregate_id=agent_id),
        "events": [e.as_dict() for e in events],
    }


@app.get("/external_agents")
async def external_agents():
    sim = get_sim()
    return sim.pap.summary()


@app.post("/bot/icarus/start")
async def icarus_start(strategy: str = "conservative", remote_url: str = ""):
    sim = get_sim()
    from pangeia.external_agents.icarus_gateway import IcarusGateway
    gateway = IcarusGateway(strategy_name=strategy, remote_url=remote_url)
    bot_id = gateway.register_via_pap(sim)
    sim.icarus = gateway
    return {
        "status": "icarus_started",
        "bot_id": bot_id,
        "strategy": strategy,
        "summary": gateway.summary(),
    }


@app.get("/bot/icarus/status")
async def icarus_status():
    sim = get_sim()
    if not sim.icarus:
        return {"status": "not_started"}
    return sim.icarus.summary()


@app.post("/bot/icarus/cycle")
async def icarus_cycle():
    sim = get_sim()
    if not sim.icarus:
        return {"error": "Icarus not started. POST /bot/icarus/start first."}
    observe_result = sim.icarus.observe(sim)
    decisions = sim.icarus.decide(sim)
    return {
        "observe": observe_result,
        "decisions": decisions,
        "decision_count": len(decisions),
    }


@app.post("/simulation/start")
async def start_simulation(speed: float = 1.0):
    global sim_running, sim_speed
    if sim_running:
        return {"status": "already_running"}
    sim_speed = speed
    sim_running = True
    asyncio.create_task(_run_simulation_loop())
    return {"status": "started", "speed": speed}


@app.post("/simulation/stop")
async def stop_simulation():
    global sim_running
    sim_running = False
    return {"status": "stopped"}


@app.post("/simulation/reset")
async def reset_simulation():
    global simulation, sim_running
    sim_running = False
    simulation = Simulation()
    return {"status": "reset"}


@app.get("/simulation/config")
async def get_config():
    sim = get_sim()
    return {
        "world": {
            "initial_population": sim.config.world.initial_population,
            "max_population": sim.config.world.max_population,
            "territory_size": sim.config.world.territory_size,
            "seed": sim.config.world.seed,
        }
    }


@app.get("/audit/events")
async def audit_events(
    event_type: Optional[str] = None,
    aggregate_type: Optional[str] = None,
    aggregate_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    sim = get_sim()
    events = sim.audit_log.get_events(
        event_type=event_type or None,
        aggregate_type=aggregate_type or None,
        aggregate_id=aggregate_id or None,
        limit=limit,
        offset=offset,
    )
    return {
        "total": sim.audit_log.get_event_count(
            event_type=event_type or None,
            aggregate_type=aggregate_type or None,
        ),
        "events": [e.as_dict() for e in events],
    }


@app.get("/audit/events/tick/{tick}")
async def audit_events_by_tick(tick: int):
    sim = get_sim()
    return [e.as_dict() for e in sim.audit_log.get_events(tick=tick)]


@app.get("/audit/events/range")
async def audit_events_range(start_tick: int, end_tick: int):
    sim = get_sim()
    return {
        "events": [
            e.as_dict()
            for e in sim.audit_log.get_events_range(start_tick, end_tick)
        ],
    }


@app.get("/audit/stats")
async def audit_stats():
    sim = get_sim()
    return {
        "total_events": sim.audit_log.get_event_count(),
        "latest_tick": sim.audit_log.get_latest_tick(),
        "events_by_type": {
            t: sim.audit_log.get_event_count(event_type=t)
            for t in [
                "agent_created", "agent_died", "company_created",
                "religion_founded", "technology_discovered",
                "faction_created", "world_event", "tick",
            ]
        },
    }


@app.get("/audit/replay-status")
async def audit_replay_status():
    sim = get_sim()
    return {
        "authoritative_source": "in_memory",
        "audit_log_size": sim.audit_log.get_event_count(),
        "snapshot_count": 0,
        "warning": "Full replay not supported in this version",
    }


@app.get("/news")
async def news_list(category: Optional[str] = None,
                    severity: Optional[str] = None,
                    limit: int = 20, offset: int = 0):
    sim = get_sim()
    articles = sim.newsroom.query(
        category=category or None,
        severity=severity or None,
        limit=limit,
        offset=offset,
    )
    return {
        "total": sim.newsroom.summary()["total_articles"],
        "articles": [a.as_dict() for a in articles],
    }


@app.get("/news/latest")
async def news_latest(n: int = 10):
    sim = get_sim()
    return {
        "articles": [a.as_dict() for a in sim.newsroom.latest(n)],
    }


@app.get("/news/{article_id}")
async def news_detail(article_id: str):
    sim = get_sim()
    article = sim.newsroom.get(article_id)
    if not article:
        return JSONResponse(status_code=404, content={"error": "Article not found"})
    return article.as_dict()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    async with ws_lock:
        websocket_clients.append(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        async with ws_lock:
            websocket_clients.remove(websocket)


async def _run_simulation_loop():
    global sim_running
    sim = get_sim()
    while sim_running:
        snapshot = sim.step()
        await _broadcast_tick(sim, snapshot)
        await asyncio.sleep(1.0 / max(0.1, sim_speed))


async def _broadcast_tick(sim: Simulation, snapshot: MetricsSnapshot):
    async with ws_lock:
        if not websocket_clients:
            return
        clients = list(websocket_clients)
    news = sim.newsroom.latest(3)
    data = {
        "type": "tick",
        "tick": snapshot.tick,
        "metrics": snapshot.as_dict(),
        "summary": sim.summary()["economy"],
        "headlines": [{"id": a.id, "headline": a.headline, "category": a.category, "severity": a.severity} for a in news],
    }
    stale = []
    for ws in clients:
        try:
            await ws.send_json(data)
        except Exception:
            stale.append(ws)
    if stale:
        async with ws_lock:
            for ws in stale:
                if ws in websocket_clients:
                    websocket_clients.remove(ws)
