from __future__ import annotations

import json
import multiprocessing
import signal
import sys
import time
import traceback
import uuid
from multiprocessing import Queue, Value
from typing import Any, Dict, Optional

from pangeia.config import SimulationConfig
from pangeia.simulation import Simulation
from pangeia.engine.event_store import EventStore
from pangeia.api.schemas import SimulationStatus


SNAPSHOT_INTERVAL = 10


def _build_state_snapshot(sim: Simulation) -> Dict[str, Any]:
    """Constrói um dicionário serializável com o estado da simulação."""
    alive = [a for a in sim.agents.values() if a.state.is_alive]
    dead = [a for a in sim.agents.values() if not a.state.is_alive]
    return {
        "tick": sim.world.state.tick,
        "time": sim.world.state.time,
        "agent_count": len(sim.agents),
        "alive_count": len(alive),
        "dead_count": len(dead),
        "alive_agents": {a.agent_id: a.summarize() for a in alive},
        "dead_agents": {a.agent_id: a.summarize() for a in dead},
        "world": sim.world.summary(),
        "economy": sim.economy.summary(),
        "governance": sim.governance.summary(),
        "metrics": sim.metrics.summary(),
        "metrics_history": [m.as_dict() for m in sim.metrics.history[-200:]],
        "events": sim.world.state.events[-50:],
        "culture": {
            "religion": sim.religion_system.summary(),
            "ideologies": sim.ideology_system.summary(),
            "memes": sim.meme_pool.summarize(),
        },
        "civilization": sim.civilization_index(),
        "technology": sim.technology.summary(),
        "technology_tree": [t.as_dict() for t in sim.technology.technologies.values()],
        "collective_memory": sim.collective_memory.summarize(),
        "narratives": sim.narratives.summary(),
        "narratives_timeline": sim.narratives.timeline[-200:],
        "stratification": sim.stratification.summary(),
        "diplomacy": sim.diplomacy.summary(),
    }


def _run_worker(
    config_json: str,
    event_store_path: str,
    cmd_queue: "multiprocessing.Queue[Dict]",
    status_queue: "multiprocessing.Queue[Dict]",
    latest_tick: "multiprocessing.Value",
):
    """Entry point do processo filho.

    Cria a Simulation e executa o loop de ticks, respondendo
    a comandos e publicando status.
    """
    signal.signal(signal.SIGINT, signal.SIG_IGN)

    config = SimulationConfig.from_dict(json.loads(config_json))
    store = EventStore(event_store_path)
    sim = Simulation(config)

    running = False
    speed = 1.0
    paused = False
    last_snapshot_tick = -SNAPSHOT_INTERVAL

    rpc_handlers: Dict[str, Any] = {
        "register_bot": lambda name, api_endpoint, api_key, caps_str="[]", version="1.0", description="": (
            sim.pap.register(name, api_endpoint, api_key,
                            json.loads(caps_str) if isinstance(caps_str, str) else caps_str,
                            sim.world.state.tick)
        ),
        "get_bot_manifest": lambda agent_id: sim.pap.get_manifest(agent_id),
        "bot_observe": lambda agent_id: sim.pap.observe(agent_id, sim),
        "bot_decide": lambda agent_id, nonce="": (
            sim.pap.decide(agent_id, sim.pap.observe(agent_id, sim), sim, nonce=nonce)
        ),
        "bot_vote": lambda agent_id, proposal_id, vote, nonce="": (
            sim.pap.vote(agent_id, proposal_id, vote, sim, nonce=nonce)
        ),
        "bot_communicate": lambda agent_id, message, channel="public", nonce="": (
            sim.pap.communicate(agent_id, message, channel, sim, nonce=nonce)
        ),
        "get_bot_audit": lambda agent_id, limit=100, offset=0: {
            "agent_id": agent_id,
            "total": sim.audit_log.get_event_count(aggregate_id=agent_id),
            "events": [e.as_dict() for e in sim.audit_log.get_events(
                aggregate_id=agent_id, limit=limit, offset=offset)],
        },
        "get_external_agents_summary": lambda: sim.pap.summary(),
        "icarus_start": lambda strategy="conservative", remote_url="": _start_icarus(sim, strategy, remote_url),
        "icarus_status": lambda: sim.icarus.summary() if sim.icarus else {"status": "not_started"},
        "icarus_cycle": lambda: _cycle_icarus(sim),
        "get_audit_events": lambda event_type=None, aggregate_type=None, aggregate_id=None, limit=100, offset=0: {
            "total": sim.audit_log.get_event_count(
                event_type=event_type or None,
                aggregate_type=aggregate_type or None,
                aggregate_id=aggregate_id or None,
            ),
            "events": [e.as_dict() for e in sim.audit_log.get_events(
                event_type=event_type or None,
                aggregate_type=aggregate_type or None,
                aggregate_id=aggregate_id or None,
                limit=limit,
                offset=offset,
            )],
        },
        "get_audit_by_tick": lambda tick: [e.as_dict() for e in sim.audit_log.get_events(tick=tick)],
        "get_audit_range": lambda start_tick, end_tick: {
            "events": [e.as_dict() for e in sim.audit_log.get_events_range(start_tick, end_tick)],
        },
        "get_audit_stats": lambda: {
            "total_events": sim.audit_log.get_event_count(),
            "latest_tick": sim.audit_log.get_latest_tick(),
        },
        "get_news": lambda category=None, severity=None, limit=20, offset=0: {
            "total": sim.newsroom.summary()["total_articles"],
            "articles": [a.as_dict() for a in sim.newsroom.query(
                category=category or None,
                severity=severity or None,
                limit=limit,
                offset=offset,
            )],
        },
        "get_news_latest": lambda n=10: {"articles": [a.as_dict() for a in sim.newsroom.latest(n)]},
        "get_news_detail": lambda article_id: (
            sim.newsroom.get(article_id).as_dict() if sim.newsroom.get(article_id) else None
        ),
    }

    def _start_icarus(sim_obj, strategy, remote_url):
        from pangeia.external_agents.icarus_gateway import IcarusGateway
        gateway = IcarusGateway(strategy_name=strategy, remote_url=remote_url)
        bot_id = gateway.register_via_pap(sim_obj)
        sim_obj.icarus = gateway
        return {"status": "icarus_started", "bot_id": bot_id, "strategy": strategy, "summary": gateway.summary()}

    def _cycle_icarus(sim_obj):
        if not sim_obj.icarus:
            return {"error": "Icarus not started"}
        observe_result = sim_obj.icarus.observe(sim_obj)
        decisions = sim_obj.icarus.decide(sim_obj)
        return {"observe": observe_result, "decisions": decisions, "decision_count": len(decisions)}

    def _handle_rpc(sim_obj, cmd, status_q, handlers):
        request_id = cmd.get("request_id", "")
        fn_name = cmd.get("fn", "")
        args = cmd.get("args", {})
        handler = handlers.get(fn_name)
        if handler is None:
            _put_nb(status_q, {
                "type": "rpc_result",
                "request_id": request_id,
                "error": f"Unknown RPC: {fn_name}",
            })
            return
        try:
            result = handler(**args)
            _put_nb(status_q, {
                "type": "rpc_result",
                "request_id": request_id,
                "result": result,
            })
        except Exception:
            _put_nb(status_q, {
                "type": "rpc_result",
                "request_id": request_id,
                "error": traceback.format_exc(),
            })

    latest_tick.value = sim.world.state.tick

    def _do_tick():
        nonlocal last_snapshot_tick
        sim.step()
        tick = sim.world.state.tick
        latest_tick.value = tick

        record = sim.metrics.history[-1] if sim.metrics.history else None
        data = {
            "type": "tick",
            "tick": tick,
            "metrics": record.as_dict() if record else {},
            "alive_count": sum(1 for a in sim.agents.values() if a.state.is_alive),
            "agent_count": len(sim.agents),
            "real_time": time.time(),
        }
        _put_nb(status_queue, data)

        if tick - last_snapshot_tick >= SNAPSHOT_INTERVAL:
            snapshot = _build_state_snapshot(sim)
            store.save_snapshot(tick, snapshot)
            _put_nb(status_queue, {
                "type": "state_snapshot",
                "data": snapshot,
                "real_time": time.time(),
            })
            last_snapshot_tick = tick

    while True:
        try:
            while not cmd_queue.empty():
                cmd = cmd_queue.get_nowait()
                if cmd["action"] == "stop":
                    store.close()
                    return
                elif cmd["action"] == "start":
                    running = True
                    speed = cmd.get("speed", 1.0)
                elif cmd["action"] == "pause":
                    running = False
                    paused = True
                elif cmd["action"] == "resume":
                    running = True
                    paused = False
                elif cmd["action"] == "set_speed":
                    speed = cmd.get("speed", 1.0)
                elif cmd["action"] == "reset":
                    config2 = SimulationConfig.from_dict(
                        json.loads(cmd.get("config", config_json))
                    )
                    sim = Simulation(config2)
                    running = False
                    paused = False
                    last_snapshot_tick = -SNAPSHOT_INTERVAL
                    latest_tick.value = 0
                    _put_nb(status_queue, {
                        "type": "reset",
                        "tick": 0,
                        "real_time": time.time(),
                    })
                elif cmd["action"] == "get_state":
                    snapshot = _build_state_snapshot(sim)
                    _put_nb(status_queue, {
                        "type": "state_snapshot",
                        "data": snapshot,
                        "real_time": time.time(),
                    })
                elif cmd["action"] == "rpc_call":
                    _handle_rpc(sim, cmd, status_queue, rpc_handlers)

            if running and not paused:
                _do_tick()
                base_delay = 1.0 / max(0.1, speed)
                time.sleep(base_delay)
            else:
                time.sleep(0.05)

        except KeyboardInterrupt:
            store.close()
            return
        except Exception:
            import traceback
            _put_nb(status_queue, {
                "type": "error",
                "error": traceback.format_exc(),
                "real_time": time.time(),
            })
            time.sleep(1)


def _put_nb(q: Queue, item: Dict):
    """Put não-bloqueante: descarta se a fila estiver cheia."""
    try:
        q.put_nowait(item)
    except Exception:
        pass


class WorkerManager:
    """Gerencia o processo SimulationWorker a partir do processo API.

    Fornece interface síncrona para comandos e fila de status para WebSocket.
    """

    def __init__(self, config: SimulationConfig,
                 event_store_path: str = ":memory:"):
        self.config = config
        self.event_store_path = event_store_path
        self._process: Optional[multiprocessing.Process] = None
        self._cmd_queue: "multiprocessing.Queue[Dict]" = Queue()
        self._status_queue: "multiprocessing.Queue[Dict]" = Queue()
        self._latest_tick = Value("i", 0)
        self._latest_state: Optional[Dict] = None
        self._status_cache: list[Dict] = []
        self._rpc_timeout: float = 10.0

    def start(self):
        if self._process is not None and self._process.is_alive():
            return False
        self._latest_state = None
        self._status_cache.clear()
        self._process = multiprocessing.Process(
            target=_run_worker,
            args=(
                json.dumps(self.config.as_dict()),
                self.event_store_path,
                self._cmd_queue,
                self._status_queue,
                self._latest_tick,
            ),
            daemon=True,
        )
        self._process.start()
        return True

    def stop(self, timeout: float = 5.0):
        if self._process is None or not self._process.is_alive():
            return
        self.send_command("stop")
        self._process.join(timeout=timeout)
        if self._process.is_alive():
            self._process.kill()
            self._process.join()
        self._process = None

    def send_command(self, action: str, **kwargs):
        _put_nb(self._cmd_queue, {"action": action, **kwargs})

    def set_speed(self, speed: float):
        self.send_command("set_speed", speed=speed)

    def request_state(self):
        self.send_command("get_state")

    def call_rpc(self, fn: str, args: Optional[Dict] = None,
                 timeout: Optional[float] = None) -> Any:
        """Chama uma RPC no processo worker e espera a resposta."""
        request_id = str(uuid.uuid4())
        self.send_command("rpc_call", fn=fn, args=args or {}, request_id=request_id)
        deadline = time.time() + (timeout or self._rpc_timeout)
        while time.time() < deadline:
            while not self._status_queue.empty():
                try:
                    msg = self._status_queue.get_nowait()
                    if msg.get("type") == "rpc_result" and msg.get("request_id") == request_id:
                        if "error" in msg:
                            raise RuntimeError(f"RPC {fn} failed: {msg['error']}")
                        return msg["result"]
                    self._status_cache.append(msg)
                except RuntimeError:
                    raise
                except Exception:
                    pass
            time.sleep(0.005)
        raise TimeoutError(f"RPC {fn} timed out after {timeout or self._rpc_timeout}s")

    def drain_status(self) -> list[Dict]:
        """Drena todos os status pendentes da fila (não-bloqueante)."""
        results = []
        while not self._status_queue.empty():
            try:
                msg = self._status_queue.get_nowait()
                results.append(msg)
                self._status_cache.append(msg)
                if msg["type"] == "state_snapshot":
                    self._latest_state = msg["data"]
            except Exception:
                break
        max_cache = 1000
        if len(self._status_cache) > max_cache:
            self._status_cache = self._status_cache[-max_cache:]
        return results

    @property
    def is_alive(self) -> bool:
        return self._process is not None and self._process.is_alive()

    @property
    def tick(self) -> int:
        return self._latest_tick.value

    @property
    def latest_state(self) -> Optional[Dict]:
        return self._latest_state

    def register_bot(self, name: str, api_endpoint: str, api_key: str,
                     capabilities: str = "[]", version: str = "1.0",
                     description: str = ""):
        return self.call_rpc("register_bot", {
            "name": name, "api_endpoint": api_endpoint, "api_key": api_key,
            "caps_str": capabilities, "version": version, "description": description,
        })

    def bot_observe(self, agent_id: str):
        return self.call_rpc("bot_observe", {"agent_id": agent_id})

    def bot_decide(self, agent_id: str, nonce: str = ""):
        return self.call_rpc("bot_decide", {"agent_id": agent_id, "nonce": nonce})

    def bot_vote(self, agent_id: str, proposal_id: str, vote: str, nonce: str = ""):
        return self.call_rpc("bot_vote", {
            "agent_id": agent_id, "proposal_id": proposal_id,
            "vote": vote, "nonce": nonce,
        })

    def bot_communicate(self, agent_id: str, message: str, channel: str = "public", nonce: str = ""):
        return self.call_rpc("bot_communicate", {
            "agent_id": agent_id, "message": message,
            "channel": channel, "nonce": nonce,
        })

    def bot_manifest(self, agent_id: str):
        return self.call_rpc("get_bot_manifest", {"agent_id": agent_id})

    def bot_audit(self, agent_id: str, limit: int = 100, offset: int = 0):
        return self.call_rpc("get_bot_audit", {
            "agent_id": agent_id, "limit": limit, "offset": offset,
        })

    def external_agents_summary(self):
        return self.call_rpc("get_external_agents_summary")

    def audit_events(self, **kwargs):
        return self.call_rpc("get_audit_events", kwargs)

    def audit_by_tick(self, tick: int):
        return self.call_rpc("get_audit_by_tick", {"tick": tick})

    def audit_range(self, start_tick: int, end_tick: int):
        return self.call_rpc("get_audit_range", {"start_tick": start_tick, "end_tick": end_tick})

    def audit_stats(self):
        return self.call_rpc("get_audit_stats")

    def icarus_start(self, strategy: str = "conservative", remote_url: str = ""):
        return self.call_rpc("icarus_start", {"strategy": strategy, "remote_url": remote_url})

    def icarus_status(self):
        return self.call_rpc("icarus_status")

    def icarus_cycle(self):
        return self.call_rpc("icarus_cycle")

    def get_news(self, **kwargs):
        return self.call_rpc("get_news", kwargs)

    def news_latest(self, n: int = 10):
        return self.call_rpc("get_news_latest", {"n": n})

    def news_detail(self, article_id: str):
        return self.call_rpc("get_news_detail", {"article_id": article_id})
