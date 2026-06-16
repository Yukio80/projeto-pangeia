from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Set

from pangeia.culture.emergent_ideology import (
    EmergentIdeology,
    IdeologyTenet,
    generate_name,
    generate_tenets_from_personality,
)


class IdeologyManager:
    def __init__(self, world: Any, rng: random.Random):
        self.world = world
        self.rng = rng
        self.ideologies: dict[str, EmergentIdeology] = {}
        self._creation_cooldown: dict[str, int] = {}
        self._inactive_counters: dict[str, int] = {}
        self._ideology_counter: int = 0

    def tick(self, agents: dict[str, Any], current_tick: int):
        self._maybe_create_ideologies(agents, current_tick)
        self._spread_ideologies(agents, current_tick)
        self._decay_ideologies(agents, current_tick)
        self._update_influence(agents)

    def _maybe_create_ideologies(self, agents: dict[str, Any], tick: int):
        for agent in list(agents.values()):
            if not agent.state.is_alive:
                continue
            if agent.state.agent_class not in ("philosopher", "governor", "teacher"):
                continue
            if agent.agent_id in self._creation_cooldown:
                if tick - self._creation_cooldown[agent.agent_id] < 50:
                    continue
            already_founder = any(
                i.active and i.founder_id == agent.agent_id
                for i in self.ideologies.values()
            )
            if already_founder:
                continue
            if self.rng.random() >= 0.02:
                continue
            self._create_ideology(agent, tick)

    def _create_ideology(self, agent: Any, tick: int):
        self._ideology_counter += 1
        ideology_id = f"emergent_{self._ideology_counter}"
        tenets = generate_tenets_from_personality(agent, self.rng)
        name = generate_name(tenets, self.rng)
        ideology = EmergentIdeology(
            id=ideology_id,
            name=name,
            founder_id=agent.agent_id,
            founder_class=agent.state.agent_class,
            founded_tick=tick,
            tenets=tenets,
            followers={agent.agent_id},
        )
        self.ideologies[ideology_id] = ideology
        self._creation_cooldown[agent.agent_id] = tick
        agent.state.influence += 0.05

    def _spread_ideologies(self, agents: dict[str, Any], tick: int):
        for ideology in list(self.ideologies.values()):
            if not ideology.active:
                continue
            candidates = [
                a for a in agents.values()
                if a.state.is_alive
                and a.agent_id not in ideology.followers
            ]
            sample_size = min(20, len(candidates))
            if sample_size == 0:
                continue
            sample = self.rng.sample(candidates, sample_size)
            for candidate in sample:
                compatibility = self._compute_compatibility(ideology, candidate)
                if compatibility <= 0.0:
                    continue
                if self.rng.random() < ideology.spread_rate * compatibility:
                    self._convert_agent(candidate, ideology, tick)

    def _compute_compatibility(self, ideology: EmergentIdeology, agent: Any) -> float:
        dot = 0.0
        weights = 0
        for tenet in ideology.tenets:
            if tenet.target is not None:
                continue
            trait_value = self._domain_to_trait(tenet.domain, agent)
            if trait_value is None:
                continue
            agent_stance = (trait_value - 0.5) * 2
            dot += tenet.stance * agent_stance
            weights += 1
        if weights == 0:
            return 0.0
        similarity = dot / weights
        return max(0.0, similarity)

    def _domain_to_trait(self, domain: str, agent: Any) -> float | None:
        p = agent.personality
        mapping = {
            "technology": p.curiosidade,
            "social": (p.empatia + p.altruismo) / 2,
            "governance": p.disciplina,
            "economy": p.ambicao,
        }
        return mapping.get(domain)

    def _convert_agent(self, agent: Any, ideology: EmergentIdeology, tick: int):
        ideology.followers.add(agent.agent_id)
        for tenet in ideology.tenets:
            proposition = f"{ideology.name}: {tenet.domain}={tenet.stance:.2f}"
            if tenet.target:
                proposition += f" target={tenet.target}"
            confidence = 0.3 + abs(tenet.stance) * 0.4
            agent.knowledge.add_shared_knowledge(
                proposition=proposition,
                confidence=min(1.0, confidence),
                source="ideology",
                category="ideology",
            )

    def _decay_ideologies(self, agents: dict[str, Any], tick: int):
        for ideology in list(self.ideologies.values()):
            if not ideology.active:
                continue
            if ideology.founder_id not in agents:
                continue
            if not agents[ideology.founder_id].state.is_alive:
                decay_count = 5
                for _ in range(decay_count):
                    if ideology.followers:
                        ideology.followers.pop()
            if ideology.influence < 0.01:
                self._inactive_counters[ideology.id] = self._inactive_counters.get(ideology.id, 0) + 1
            else:
                self._inactive_counters[ideology.id] = 0
            if self._inactive_counters.get(ideology.id, 0) >= 50:
                ideology.active = False

    def _update_influence(self, agents: dict[str, Any]):
        alive_count = sum(1 for a in agents.values() if a.state.is_alive)
        if alive_count == 0:
            for ideology in self.ideologies.values():
                ideology.influence = 0.0
            return
        for ideology in self.ideologies.values():
            ideology.influence = len(ideology.followers) / alive_count

    def get_technology_modifier(self, agent_id: str, technology_name: str) -> float:
        modifier = 0.0
        for ideology in self.ideologies.values():
            if not ideology.active:
                continue
            if agent_id not in ideology.followers:
                continue
            for tenet in ideology.tenets:
                if tenet.domain != "technology":
                    continue
                if tenet.target == technology_name:
                    modifier += tenet.stance * tenet.strength * 2.0
                elif tenet.target is None:
                    modifier += tenet.stance * tenet.strength * 0.5
        return max(-1.0, min(1.0, modifier))

    def get_active_ideologies(self) -> list[EmergentIdeology]:
        return [i for i in self.ideologies.values() if i.active]

    def to_dict(self) -> dict:
        return {
            "emergent": [i.to_dict() for i in self.get_active_ideologies()],
            "count": len(self.get_active_ideologies()),
            "total_followers": sum(len(i.followers) for i in self.get_active_ideologies()),
        }
