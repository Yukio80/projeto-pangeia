from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi import Body

from pangeia.config import SimulationConfig
from pangeia.engine.event_store import EventStore
from pangeia.engine.simulation_worker import WorkerManager
from pangeia.api.state_reader import StateReader
from pangeia.api.schemas import (
    SimulationStatus, WorldSummary, EconomySummary,
    GovernanceSummary, MetricsSummary, FullSummary,
    BotRegisterRequest, BotRegisterResponse,
    BotManifestResponse, BotObserveResponse,
    BotDecideRequest, BotDecideResponse,
    BotVoteRequest, BotVoteResponse,
    BotCommunicateRequest, BotCommunicateResponse,
    BotAuditResponse, ExternalAgentsListResponse,
    IcarusStartRequest, IcarusStartResponse, IcarusCycleResponse,
    SimulationStartRequest, SimulationConfigResponse,
    AuditEventResponse, AuditStatsResponse, AuditReplayStatusResponse,
    NewsArticleResponse, NewsListResponse,
    AblationRunRequest, AblationRunResponse,
    SnapshotResponse, SnapshotMeta, TimelinePoint, TimelineResponse,
)


_api_dir = os.path.dirname(os.path.abspath(__file__))
_static_dir = os.path.join(_api_dir, "static")

app = FastAPI(title="Projeto Pangeia API")
app.mount("/static", StaticFiles(directory=_static_dir), name="static")

worker_manager: Optional[WorkerManager] = None
state_reader: Optional[StateReader] = None
event_store: Optional[EventStore] = None
config: Optional[SimulationConfig] = None

websocket_clients: list[WebSocket] = []
ws_lock = asyncio.Lock()
_ws_send_queue: asyncio.Queue[Dict] = asyncio.Queue()


def init_simulation(
    event_store_path: str = ":memory:",
    seed: int = 42,
    population: int = 500,
):
    global worker_manager, state_reader, event_store, config
    from pangeia.persistence.config import PersistenceConfig

    config = SimulationConfig.default()
    config.world.seed = seed
    config.world.initial_population = population
    config.persistence = PersistenceConfig.from_env()

    event_store = EventStore(event_store_path)
    worker_manager = WorkerManager(config, event_store_path=event_store_path)
    worker_manager.start()
    state_reader = StateReader(event_store, worker_manager)


async def drain_status_task():
    """Task que drena status do worker e alimenta WebSocket."""
    while True:
        await asyncio.sleep(0.05)
        if not worker_manager or not worker_manager.is_alive:
            continue
        status_msgs = worker_manager.drain_status()
        for msg in status_msgs:
            if msg["type"] == "tick":
                await _ws_broadcast({
                    "type": "tick",
                    "tick": msg["tick"],
                    "metrics": msg["metrics"],
                    "alive_count": msg.get("alive_count", 0),
                    "agent_count": msg.get("agent_count", 0),
                })
            elif msg["type"] == "error":
                await _ws_broadcast({
                    "type": "error",
                    "error": msg.get("error", "unknown error"),
                })


async def _ws_broadcast(data: Dict):
    """Envia mensagem para todos os WebSocket clients."""
    async with ws_lock:
        if not websocket_clients:
            return
        clients = list(websocket_clients)
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


# ─── Ablation Experiment Runner ────────────────────────────

import uuid
import asyncio
from concurrent.futures import ThreadPoolExecutor

_ablation_tasks: Dict[str, Dict] = {}
_ablation_executor = ThreadPoolExecutor(max_workers=1)


@app.post("/ablation/run", response_model=AblationRunResponse)
async def run_ablation_api(req: AblationRunRequest):
    task_id = str(uuid.uuid4())[:8]
    _ablation_tasks[task_id] = {"status": "running", "results": None}

    def _run():
        from pangeia.experiments.ablation import run_ablation, AblationConfig
        cfg = AblationConfig(
            conditions=req.conditions,
            seeds=req.seeds,
            ticks=req.ticks,
            population=req.population,
            verbose=False,
            personality_wiring=True,
        )
        results = run_ablation(cfg)
        _ablation_tasks[task_id] = {"status": "done", "results": [
            {"condition": r.condition, "seed": r.seed, "metrics": r.metrics}
            for r in results
        ]}

    loop = asyncio.get_event_loop()
    loop.run_in_executor(_ablation_executor, _run)

    return AblationRunResponse(
        status="started",
        task_id=task_id,
        message=f"Ablation started: {len(req.conditions)} conditions × {len(req.seeds)} seeds × {req.ticks} ticks",
    )


@app.get("/ablation/result/{task_id}")
async def ablation_result(task_id: str):
    task = _ablation_tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task["status"] == "running":
        raise HTTPException(status_code=202, detail="Still running")
    return task


def get_reader() -> StateReader:
    if state_reader is None:
        raise HTTPException(status_code=503, detail="Simulation not initialized")
    return state_reader


def get_worker() -> WorkerManager:
    if worker_manager is None:
        raise HTTPException(status_code=503, detail="Simulation not initialized")
    return worker_manager


# ─── Lifecycle ──────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    seed = int(os.environ.get("PANGEIA_SEED", "42"))
    pop = int(os.environ.get("PANGEIA_POPULATION", "500"))
    init_simulation(seed=seed, population=pop)
    asyncio.create_task(drain_status_task())


# ─── Root ────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "project": "Projeto Pangeia",
        "description": "Laboratório de civilizações artificiais",
        "status": get_reader().status(),
    }


@app.get("/dashboard")
async def dashboard():
    return FileResponse(os.path.join(_static_dir, "dashboard.html"))


# ─── Core State ──────────────────────────────────────────────

@app.get("/status", response_model=SimulationStatus)
async def status():
    return get_reader().status()


@app.get("/summary")
async def summary():
    return get_reader().summary()


@app.get("/world")
async def world():
    return get_reader().world()


@app.get("/economy")
async def economy():
    return get_reader().economy()


@app.get("/governance")
async def governance():
    return get_reader().governance()


@app.get("/culture")
async def culture():
    return get_reader().culture()


@app.get("/ideologies")
async def ideologies():
    base = get_reader().culture().get("ideologies", {})
    emergent = get_reader().culture().get("emergent_ideologies", {})
    return {
        **base,
        "emergent": emergent.get("emergent", []),
        "emergent_count": emergent.get("count", 0),
        "emergent_followers": emergent.get("total_followers", 0),
    }


@app.get("/diplomacy")
async def diplomacy():
    return get_reader().diplomacy()


@app.get("/stratification")
async def stratification():
    return get_reader().stratification()


# ─── Agents ──────────────────────────────────────────────────

@app.get("/agents")
async def agents_list(limit: int = 100, offset: int = 0):
    return get_reader().agent_list(limit=limit, offset=offset)


@app.get("/agents/{agent_id}")
async def agent_detail(agent_id: str):
    agent = get_reader().agent_detail(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


# ─── Metrics ─────────────────────────────────────────────────

@app.get("/metrics")
async def metrics():
    return get_reader().metrics()


@app.get("/metrics/history")
async def metrics_history(n: int = 100):
    return get_reader().metrics_history(n=n)


@app.get("/events")
async def world_events():
    return get_reader().world_events()


# ─── Civilization ────────────────────────────────────────────

@app.get("/civilization")
async def civilization():
    return get_reader().civilization()


# ─── Technology ──────────────────────────────────────────────

@app.get("/technology")
async def technology():
    return get_reader().technology()


@app.get("/technology/tree")
async def technology_tree():
    return get_reader().technology_tree()


# ─── History / Narratives ────────────────────────────────────

@app.get("/history")
async def history():
    return get_reader().narratives()


@app.get("/history/timeline")
async def history_timeline():
    return get_reader().narratives_timeline()


# ─── Collective Memory ───────────────────────────────────────

@app.get("/collective_memory")
async def collective_memory():
    return get_reader().collective_memory()


@app.get("/collective_memory/myths")
async def collective_memory_myths():
    cm = get_reader().collective_memory()
    return cm.get("by_narrative_type", {}).get("myth", [])


@app.get("/collective_memory/volatility")
async def collective_memory_volatility():
    cm = get_reader().collective_memory()
    return cm.get("volatility", {})


@app.get("/collective_memory/narratives/{narrative_type}")
async def collective_memory_narratives(narrative_type: str):
    cm = get_reader().collective_memory()
    return cm.get("by_narrative_type", {}).get(narrative_type, [])


@app.get("/collective_memory/identity")
async def collective_memory_identity():
    cm = get_reader().collective_memory()
    return cm.get("identity", {})


@app.get("/collective_memory/actors")
async def collective_memory_actors():
    cm = get_reader().collective_memory()
    return cm.get("actor_details", [])


@app.get("/collective_memory/actors/{agent_id}")
async def collective_memory_actor(agent_id: str):
    cm = get_reader().collective_memory()
    actors = cm.get("actor_details", [])
    for a in actors:
        if a.get("actor_id") == agent_id:
            return a
    raise HTTPException(status_code=404, detail="Actor not found")


# ─── Bot / PAP ───────────────────────────────────────────────

@app.post("/bot/register", response_model=BotRegisterResponse)
async def bot_register(req: BotRegisterRequest):
    result = get_worker().register_bot(
        name=req.name, api_endpoint=req.api_endpoint, api_key=req.api_key,
        capabilities=req.capabilities, version=req.version, description=req.description,
    )
    return {"agent_id": result.get("agent_id", "unknown"), "status": "registered"}


@app.get("/bot/manifest/{agent_id}", response_model=BotManifestResponse)
async def bot_manifest(agent_id: str):
    return get_worker().bot_manifest(agent_id=agent_id)


@app.post("/bot/observe/{agent_id}", response_model=BotObserveResponse)
async def bot_observe(agent_id: str):
    return get_worker().bot_observe(agent_id=agent_id)


@app.post("/bot/decide/{agent_id}", response_model=BotDecideResponse)
async def bot_decide(agent_id: str, req: BotDecideRequest = Body(default=BotDecideRequest())):
    return get_worker().bot_decide(agent_id=agent_id, nonce=req.nonce)


@app.post("/bot/vote/{agent_id}", response_model=BotVoteResponse)
async def bot_vote(agent_id: str, req: BotVoteRequest):
    return get_worker().bot_vote(
        agent_id=agent_id, proposal_id=req.proposal_id, vote=req.vote, nonce=req.nonce,
    )


@app.post("/bot/communicate/{agent_id}", response_model=BotCommunicateResponse)
async def bot_communicate(agent_id: str, req: BotCommunicateRequest):
    return get_worker().bot_communicate(
        agent_id=agent_id, message=req.message, channel=req.channel, nonce=req.nonce,
    )


@app.get("/bot/audit/{agent_id}", response_model=BotAuditResponse)
async def bot_audit(agent_id: str, limit: int = 100, offset: int = 0):
    return get_worker().bot_audit(agent_id=agent_id, limit=limit, offset=offset)


@app.get("/external_agents", response_model=ExternalAgentsListResponse)
async def external_agents():
    return get_worker().external_agents_summary()


# ─── Icarus ──────────────────────────────────────────────────

@app.post("/bot/icarus/start", response_model=IcarusStartResponse)
async def icarus_start(req: IcarusStartRequest):
    return get_worker().icarus_start(strategy=req.strategy, remote_url=req.remote_url)


@app.get("/bot/icarus/status")
async def icarus_status():
    return get_worker().icarus_status()


@app.post("/bot/icarus/cycle", response_model=IcarusCycleResponse)
async def icarus_cycle():
    return get_worker().icarus_cycle()


# ─── Simulation Control ──────────────────────────────────────

@app.post("/simulation/start")
async def start_simulation(req: SimulationStartRequest = Body(default=SimulationStartRequest())):
    w = get_worker()
    w.send_command("start", speed=req.speed)
    return {"status": "started", "speed": req.speed}


@app.post("/simulation/stop")
async def stop_simulation():
    w = get_worker()
    w.send_command("pause")
    return {"status": "paused"}


@app.post("/simulation/reset")
async def reset_simulation():
    w = get_worker()
    w.send_command("reset", config=(config.as_dict() if config else {}))
    return {"status": "reset"}


@app.get("/simulation/config", response_model=SimulationConfigResponse)
async def get_config():
    if config is None:
        return {"world": {}}
    return {
        "world": {
            "initial_population": config.world.initial_population,
            "max_population": config.world.max_population,
            "territory_size": config.world.territory_size,
            "seed": config.world.seed,
        }
    }


# ─── Audit ───────────────────────────────────────────────────

@app.get("/audit/events")
async def audit_events(
    event_type: Optional[str] = None,
    aggregate_type: Optional[str] = None,
    aggregate_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    return get_worker().audit_events(
        event_type=event_type, aggregate_type=aggregate_type,
        aggregate_id=aggregate_id, limit=limit, offset=offset,
    )


@app.get("/audit/events/tick/{tick}")
async def audit_events_by_tick(tick: int):
    return get_worker().audit_by_tick(tick=tick)


@app.get("/audit/events/range")
async def audit_events_range(start_tick: int, end_tick: int):
    return get_worker().audit_range(start_tick=start_tick, end_tick=end_tick)


@app.get("/audit/stats", response_model=AuditStatsResponse)
async def audit_stats():
    return get_worker().audit_stats()


@app.get("/audit/replay-status", response_model=AuditReplayStatusResponse)
async def audit_replay_status():
    return {
        "authoritative_source": "worker_process",
        "event_store": "sqlite",
        "snapshot_interval": 10,
        "warning": "Events are append-only; snapshots enable fast restart",
    }


# ─── News ────────────────────────────────────────────────────

@app.get("/news", response_model=NewsListResponse)
async def news_list(category: Optional[str] = None,
                    severity: Optional[str] = None,
                    limit: int = 20, offset: int = 0):
    return get_worker().get_news(
        category=category, severity=severity, limit=limit, offset=offset,
    )


@app.get("/news/latest", response_model=NewsListResponse)
async def news_latest(n: int = 10):
    return get_worker().news_latest(n=n)


@app.get("/news/{article_id}", response_model=Optional[NewsArticleResponse])
async def news_detail(article_id: str):
    result = get_worker().news_detail(article_id=article_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Article not found")
    return result


# ─── Snapshots ───────────────────────────────────────────────

_SNAPSHOT_DIR = Path("snapshots")

_SNAPSHOT_METRIC_PATHS: dict[str, list[str]] = {
    "gdp": ["economy", "indicators", "gdp"],
    "population": ["status", "alive_count"],
    "stability": ["governance", "government", "stability"],
    "inequality": ["economy", "indicators", "inequality"],
    "happiness": ["summary", "metrics", "current", "collective_happiness"],
    "technology_count": ["technology", "discovered"],
    "volatility": ["collective_memory_volatility", "composite"],
}


def _snapshot_dig(snapshot: dict, path: list[str]) -> Any:
    for key in path:
        if isinstance(snapshot, dict):
            snapshot = snapshot.get(key, {})
        else:
            return None
    return snapshot if snapshot != {} else None

def _collect_full_state_sync() -> dict:
    """Collect full simulation state from in-process reader/worker (no HTTP)."""
    try:
        reader = get_reader()
    except HTTPException:
        return {"error": "simulation_not_initialized"}
    state: dict[str, Any] = {
        "status": reader.status(),
        "summary": reader.summary(),
        "economy": reader.economy(),
        "economy_history": reader.metrics_history(),
        "governance": reader.governance(),
        "culture": reader.culture(),
        "ideologies": reader.culture().get("ideologies", {}),
        "civilization": reader.civilization(),
        "collective_memory": reader.collective_memory(),
        "collective_memory_myths": reader.collective_memory().get("by_narrative_type", {}).get("myth", []),
        "collective_memory_volatility": reader.collective_memory().get("volatility", {}),
        "technology": reader.technology(),
        "technology_tree": reader.technology_tree(),
        "diplomacy": reader.diplomacy(),
        "stratification": reader.stratification(),
    }
    try:
        state["news_latest"] = get_worker().news_latest(n=20)
    except Exception:
        state["news_latest"] = {"articles": []}
    return state


@app.post("/snapshot", response_model=SnapshotResponse)
async def create_snapshot(label: str = ""):
    _SNAPSHOT_DIR.mkdir(exist_ok=True)

    state = _collect_full_state_sync()
    state["snapshot_timestamp"] = datetime.now(timezone.utc).isoformat()
    state["snapshot_label"] = label
    actual_tick = state.get("status", {}).get("tick", 0) if isinstance(state.get("status"), dict) else 0
    state["tick"] = actual_tick

    suffix = f"_{label}" if label else ""
    filename = f"{actual_tick:06d}{suffix}.json"
    path = _SNAPSHOT_DIR / filename
    content = json.dumps(state, indent=2, ensure_ascii=False, default=str)
    path.write_text(content, encoding="utf-8")

    return SnapshotResponse(
        tick=actual_tick,
        path=str(path),
        size_bytes=len(content.encode()),
        timestamp=state["snapshot_timestamp"],
        label=label,
    )


@app.get("/snapshots", response_model=list[SnapshotMeta])
async def list_snapshots():
    if not _SNAPSHOT_DIR.is_dir():
        return []
    files = sorted(_SNAPSHOT_DIR.glob("*.json"), key=lambda f: f.name)
    result = []
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        tick = data.get("tick", 0)
        label = data.get("snapshot_label", "")
        ts = data.get("snapshot_timestamp", "")
        result.append(SnapshotMeta(
            tick=tick,
            path=str(f),
            size_bytes=f.stat().st_size,
            timestamp=ts,
            label=label,
            filename=f.name,
        ))
    return result


@app.get("/snapshot/{tick}")
async def get_snapshot(tick: int):
    if not _SNAPSHOT_DIR.is_dir():
        raise HTTPException(status_code=404, detail=f"No snapshot found for tick {tick}")
    files = sorted(_SNAPSHOT_DIR.glob(f"{tick:06d}*.json"))
    if not files:
        raise HTTPException(status_code=404, detail=f"No snapshot found for tick {tick}")
    latest = files[-1]
    try:
        data = json.loads(latest.read_text(encoding="utf-8"))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read snapshot: {e}")
    return data


@app.get("/timeline", response_model=TimelineResponse)
async def get_timeline(metric: str = "gdp", from_tick: int = 0, to_tick: int = 999999):
    if metric not in _SNAPSHOT_METRIC_PATHS:
        valid = list(_SNAPSHOT_METRIC_PATHS.keys())
        raise HTTPException(
            status_code=400,
            detail=f"Unknown metric '{metric}'. Valid: {', '.join(valid)}",
        )
    if not _SNAPSHOT_DIR.is_dir():
        return TimelineResponse(
            metric=metric, from_tick=from_tick, to_tick=to_tick,
            points=[], snapshot_count=0,
        )
    files = sorted(_SNAPSHOT_DIR.glob("*.json"), key=lambda f: f.name)
    points: list[TimelinePoint] = []
    count = 0
    path = _SNAPSHOT_METRIC_PATHS[metric]
    for f in files:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        tick = data.get("tick", 0)
        if tick < from_tick or tick > to_tick:
            continue
        count += 1
        value = _snapshot_dig(data, path)
        if isinstance(value, (int, float)):
            points.append(TimelinePoint(tick=tick, value=float(value)))
        else:
            points.append(TimelinePoint(tick=tick, value=None))
    return TimelineResponse(
        metric=metric, from_tick=from_tick, to_tick=to_tick,
        points=points, snapshot_count=count,
    )


# ─── WebSocket ───────────────────────────────────────────────

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
