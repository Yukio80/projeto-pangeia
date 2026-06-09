from __future__ import annotations

import random
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from pangeia.core.communication import Message

if TYPE_CHECKING:
    from pangeia.simulation import Simulation


class RateLimiter:
    def __init__(self, max_calls: int, window_seconds: int):
        self.max_calls = max_calls
        self.window = window_seconds
        self._calls: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, bot_id: str) -> bool:
        now = time.time()
        calls = self._calls[bot_id]
        self._calls[bot_id] = [t for t in calls if now - t < self.window]
        if len(self._calls[bot_id]) >= self.max_calls:
            return False
        self._calls[bot_id].append(now)
        return True

    def remaining(self, bot_id: str) -> int:
        now = time.time()
        calls = [t for t in self._calls.get(bot_id, []) if now - t < self.window]
        return max(0, self.max_calls - len(calls))


class CitizenshipStatus(Enum):
    PENDING = "pending"
    SANDBOX = "sandbox"
    PARTIAL = "partial"
    FULL = "full"


@dataclass
class ExternalAgent:
    agent_id: str
    name: str
    api_endpoint: str
    api_key_hash: str
    manifest: Dict[str, Any]
    citizenship: CitizenshipStatus = CitizenshipStatus.PENDING
    registration_tick: int = 0
    last_ping: int = 0
    reputation: float = 0.5
    interaction_count: int = 0
    sandbox_score: float = 0.0
    wealth: float = 50.0
    influence: float = 0.0

    def as_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "status": self.citizenship.value,
            "reputation": round(self.reputation, 3),
            "interactions": self.interaction_count,
            "sandbox_score": round(self.sandbox_score, 3),
            "wealth": round(self.wealth, 2),
            "influence": round(self.influence, 3),
            "capabilities": self.manifest.get("capabilities", []),
        }


class PAPProtocol:
    _decide_limiter = RateLimiter(max_calls=10, window_seconds=60)
    _vote_limiter = RateLimiter(max_calls=5, window_seconds=60)
    _comm_limiter = RateLimiter(max_calls=20, window_seconds=60)

    # Economic impact thresholds by citizenship
    _MAX_IMPACT_DELTA = {
        CitizenshipStatus.PENDING: 0.0,
        CitizenshipStatus.SANDBOX: 0.01,
        CitizenshipStatus.PARTIAL: 0.03,
        CitizenshipStatus.FULL: 0.05,
    }

    def __init__(self, rng: Optional[random.Random] = None):
        self.rng = rng or random.Random()
        self.external_agents: Dict[str, ExternalAgent] = {}
        self._seen_nonces: Dict[str, float] = {}
        self._nonce_cleanup_counter = 0

    def register(self, name: str, api_endpoint: str,
                 api_key: str, manifest: Dict[str, Any],
                 tick: int) -> Dict[str, Any]:
        agent_id = f"ext_{uuid.uuid4().hex[:8]}"
        api_key_hash = str(hash(api_key))[:16]

        required_fields = ["capabilities", "version", "description"]
        for field in required_fields:
            if field not in manifest:
                return {"error": f"Missing required manifest field: {field}"}

        agent = ExternalAgent(
            agent_id=agent_id,
            name=name,
            api_endpoint=api_endpoint,
            api_key_hash=api_key_hash,
            manifest=manifest,
            registration_tick=tick,
        )
        self.external_agents[agent_id] = agent

        return {
            "agent_id": agent_id,
            "status": "pending",
            "message": "Registration successful. Sandbox evaluation required.",
        }

    def evaluate_sandbox(self, agent_id: str, sim: Simulation) -> Dict[str, Any]:
        agent = self.external_agents.get(agent_id)
        if not agent:
            return {"error": "Agent not found"}

        score = 0.0
        score += self.rng.uniform(0, 0.3)
        score += min(0.3, agent.interaction_count * 0.01)
        score += agent.reputation * 0.2

        agent.sandbox_score = score
        if score > 0.5:
            agent.citizenship = CitizenshipStatus.PARTIAL
        elif score > 0.3:
            agent.citizenship = CitizenshipStatus.SANDBOX

        return {
            "agent_id": agent_id,
            "score": round(score, 3),
            "status": agent.citizenship.value,
            "next_status": "partial" if score > 0.5 else "sandbox",
        }

    def _check_nonce(self, nonce: str) -> Optional[str]:
        if not nonce:
            return None
        if nonce in self._seen_nonces:
            return "Duplicate request (nonce already processed)"
        self._nonce_cleanup_counter += 1
        if self._nonce_cleanup_counter >= 1000:
            cutoff = time.time() - 300
            self._seen_nonces = {k: v for k, v in self._seen_nonces.items() if v > cutoff}
            self._nonce_cleanup_counter = 0
        self._seen_nonces[nonce] = time.time()
        return None

    def _validate_impact(self, agent: ExternalAgent, action: str,
                         parameters: dict) -> Optional[str]:
        max_delta = self._MAX_IMPACT_DELTA.get(agent.citizenship, 0.0)
        if max_delta <= 0:
            return None

        if action == "propose_policy":
            strength = parameters.get("strength", 0)
            impact = strength * 0.15
            if impact > max_delta:
                return (
                    f"Economic impact {impact:.2%} exceeds allowed delta "
                    f"{max_delta:.2%} for citizenship '{agent.citizenship.value}'"
                )

        if action == "trade":
            quantity = parameters.get("quantity", 0)
            impact = quantity * 0.002
            if impact > max_delta:
                return (
                    f"Trade impact {impact:.2%} exceeds allowed delta "
                    f"{max_delta:.2%} for citizenship '{agent.citizenship.value}'"
                )

        return None

    def observe(self, agent_id: str, sim: Simulation) -> Dict[str, Any]:
        agent = self.external_agents.get(agent_id)
        if not agent:
            return {"error": "Agent not found"}
        agent.last_ping = sim.world.state.tick
        agent.interaction_count += 1
        return {
            "tick": sim.world.state.tick,
            "world": sim.world.summary(),
            "economy": sim.economy.summary(),
            "governance": sim.governance.summary(),
            "culture": {
                "religions": sim.religion_system.summary(),
                "ideologies": sim.ideology_system.summary(),
            },
            "civilization": sim.civilization_index(),
            "my_status": agent.as_dict(),
        }

    def decide(self, agent_id: str, observation: Dict[str, Any],
               sim: Simulation, nonce: str = "") -> Dict[str, Any]:
        agent = self.external_agents.get(agent_id)
        if not agent:
            return {"error": "Agent not found"}
        if agent.citizenship == CitizenshipStatus.PENDING:
            return {"error": "Sandbox evaluation required"}
        if not self._decide_limiter.is_allowed(agent_id):
            return {"error": "Rate limit exceeded (max 10 decisions/minute)"}

        nonce_error = self._check_nonce(nonce)
        if nonce_error:
            return {"error": nonce_error}

        decision = {
            "action": "observe",
            "parameters": {},
            "confidence": 0.5,
        }

        if agent.citizenship == CitizenshipStatus.FULL:
            economy = observation.get("economy", {})
            indicators = economy.get("indicators", {})
            if indicators.get("inequality", 0.5) > 0.7:
                decision = {
                    "action": "propose_policy",
                    "parameters": {"policy": "wealth_redistribution", "strength": 0.5},
                    "confidence": 0.7,
                }

        if agent.citizenship == CitizenshipStatus.PARTIAL:
            if self.rng.random() < 0.3:
                decision = {
                    "action": "trade",
                    "parameters": {"resource": "food", "quantity": 10},
                    "confidence": 0.6,
                }

        impact_error = self._validate_impact(agent, decision["action"], decision["parameters"])
        if impact_error:
            return {"error": impact_error, "fallback_decision": {"action": "observe", "parameters": {}, "confidence": 0.3}}

        return decision

    def vote(self, agent_id: str, proposal_id: str,
             vote: str, sim: Simulation, nonce: str = "") -> Dict[str, Any]:
        agent = self.external_agents.get(agent_id)
        if not agent:
            return {"error": "Agent not found"}
        if agent.citizenship not in (CitizenshipStatus.PARTIAL, CitizenshipStatus.FULL):
            return {"error": "Insufficient citizenship status to vote"}
        if vote not in ("for", "against", "abstain"):
            return {"error": "Invalid vote. Use: for, against, abstain"}
        if not self._vote_limiter.is_allowed(agent_id):
            return {"error": "Rate limit exceeded (max 5 votes/minute)"}
        nonce_error = self._check_nonce(nonce)
        if nonce_error:
            return {"error": nonce_error}

        agent.interaction_count += 1
        return {
            "status": "recorded",
            "proposal": proposal_id,
            "vote": vote,
            "agent_id": agent_id,
        }

    def communicate(self, agent_id: str, message: str,
                    channel: str, sim: Simulation, nonce: str = "") -> Dict[str, Any]:
        agent = self.external_agents.get(agent_id)
        if not agent:
            return {"error": "Agent not found"}
        if agent.citizenship == CitizenshipStatus.PENDING:
            return {"error": "Sandbox evaluation required"}
        if not self._comm_limiter.is_allowed(agent_id):
            return {"error": "Rate limit exceeded (max 20 messages/minute)"}
        nonce_error = self._check_nonce(nonce)
        if nonce_error:
            return {"error": nonce_error}

        msg = Message(
            sender_id=agent_id,
            content=message,
            message_type=channel if channel in ("media", "public") else "public",
        )
        sim.communication.broadcast(msg, sim.agents, tick=sim.world.state.tick)
        agent.interaction_count += 1
        return {
            "status": "broadcast",
            "channel": channel,
            "recipients": len(sim.agents),
        }

    def get_manifest(self, agent_id: str) -> Dict[str, Any]:
        agent = self.external_agents.get(agent_id)
        if not agent:
            return {"error": "Agent not found"}
        return {
            "agent_id": agent.agent_id,
            "name": agent.name,
            "capabilities": agent.manifest.get("capabilities", []),
            "version": agent.manifest.get("version", "1.0"),
            "description": agent.manifest.get("description", ""),
            "status": agent.citizenship.value,
        }

    def summary(self) -> dict:
        return {
            "total": len(self.external_agents),
            "by_status": {
                s.value: sum(
                    1 for a in self.external_agents.values()
                    if a.citizenship == s
                )
                for s in CitizenshipStatus
            },
            "agents": [a.as_dict() for a in self.external_agents.values()],
            "active_last_tick": sum(
                1 for a in self.external_agents.values()
                if a.interaction_count > 0
            ),
        }
