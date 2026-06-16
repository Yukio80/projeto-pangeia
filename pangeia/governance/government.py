from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from pangeia.core.agent import Agent


class GovernmentType(Enum):
    DIRECT_DEMOCRACY = "direct_democracy"
    REPRESENTATIVE = "representative"
    MERITOCRACY = "meritocracy"
    TECHNOCRACY = "technocracy"
    MONARCHY = "monarchy"
    OLIGARCHY = "oligarchy"
    ORGANIZED_ANARCHY = "organized_anarchy"


@dataclass
class Law:
    id: str
    name: str
    description: str
    category: str
    support: float = 0.5
    enacted_tick: int = 0
    active: bool = True
    votes_for: int = 0
    votes_against: int = 0


@dataclass
class Government:
    type: GovernmentType = GovernmentType.REPRESENTATIVE
    officials: List[str] = field(default_factory=list)
    laws: List[Law] = field(default_factory=list)
    stability: float = 0.7
    legitimacy: float = 0.8
    tax_rate: float = 0.1

    def add_law(self, name: str, description: str, category: str = "general",
                tick: int = 0) -> Law:
        law = Law(
            id=f"law_{len(self.laws)}",
            name=name,
            description=description,
            category=category,
            enacted_tick=tick,
        )
        self.laws.append(law)
        return law

    def collect_taxes(self, wealth: float) -> float:
        tax = wealth * self.tax_rate
        return tax

    def as_dict(self) -> dict:
        return {
            "type": self.type.value,
            "officials": len(self.officials),
            "laws": len(self.laws),
            "stability": round(self.stability, 3),
            "legitimacy": round(self.legitimacy, 3),
            "tax_rate": round(self.tax_rate, 4),
        }


@dataclass
class TechRestriction:
    technology_name: str
    restriction_level: float = 0.0
    proposed_tick: int = 0
    active: bool = False
    votes_for: int = 0
    votes_against: int = 0

    def as_dict(self) -> dict:
        return {
            "technology": self.technology_name,
            "restriction_level": round(self.restriction_level, 3),
            "active": self.active,
            "proposed_tick": self.proposed_tick,
        }


class GovernanceSystem:
    def __init__(self, config):
        self.config = config
        self.government = Government()
        self.voter_registry: Set[str] = set()
        self.term_tick = 0
        self.election_cycle = config.governance.election_cycle
        self.tech_restrictions: Dict[str, TechRestriction] = {}

    def register_voter(self, agent_id: str):
        self.voter_registry.add(agent_id)

    def hold_election(self, agents: Dict[str, "Agent"], tick: int):
        self.term_tick = tick
        votes: Dict[str, int] = {}
        for aid, agent in agents.items():
            if not agent.state.is_alive:
                continue
            if aid not in self.voter_registry:
                continue
            if agent.rng.random() < 0.6:
                preferred = self._find_preferred(agent, agents)
                if preferred:
                    votes[preferred] = votes.get(preferred, 0) + 1

        if votes:
            winner = max(votes, key=votes.get)
            self.government.officials = [winner]
            if winner in agents:
                agents[winner].memory.remember(
                    f"Elected to office in tick {tick}",
                    memory_type="political",
                    importance=1.0,
                )

    def _find_preferred(self, voter: "Agent",
                        agents: Dict[str, "Agent"]) -> Optional[str]:
        candidates = [
            aid for aid, a in agents.items()
            if a.state.agent_class in ("governor", "philosopher") and a.state.is_alive
        ]
        if not candidates:
            candidates = [aid for aid, a in agents.items() if a.state.is_alive]
        if not candidates:
            return None
        compatible = sorted(candidates, key=lambda aid: abs(
            agents[aid].state.political_alignment - voter.state.political_alignment
        ))
        return compatible[0] if compatible else voter.agent_id

    def propose_law(self, name: str, description: str, category: str,
                    proposer: "Agent", tick: int) -> Law:
        law = self.government.add_law(name, description, category, tick)
        proposer.memory.remember(
            f"Proposed law '{name}': {description}",
            memory_type="governance",
            importance=0.7,
        )
        return law

    def step(self, agents: Dict[str, "Agent"], tick: int):
        self.government.stability += (self.government.legitimacy - self.government.stability) * 0.01
        self.government.stability = max(0, min(1, self.government.stability))
        self.government.legitimacy += self.rng_gauss(0, 0.005)
        self.government.legitimacy = max(0, min(1, self.government.legitimacy))

        if tick - self.term_tick >= self.election_cycle:
            self.hold_election(agents, tick)

    def propose_tech_restriction(self, technology_name: str, lobbying_power: float) -> bool:
        if technology_name in self.tech_restrictions:
            existing = self.tech_restrictions[technology_name]
            existing.restriction_level = min(0.8, existing.restriction_level + lobbying_power * 0.1)
            if existing.restriction_level > 0.5 and not existing.active:
                existing.active = True
            return True
        restriction = TechRestriction(
            technology_name=technology_name,
            restriction_level=min(0.8, lobbying_power * 0.8),
            proposed_tick=self.government.laws[-1].enacted_tick if self.government.laws else 0,
            active=lobbying_power > 0.5,
        )
        self.tech_restrictions[technology_name] = restriction
        return True

    def get_tech_restriction(self, technology_name: str) -> Optional[TechRestriction]:
        return self.tech_restrictions.get(technology_name)

    def get_active_restrictions(self) -> list[dict]:
        return [
            r.as_dict() for r in self.tech_restrictions.values()
            if r.active
        ]

    def rng_gauss(self, mu: float, sigma: float) -> float:
        import random
        return random.gauss(mu, sigma)

    def summary(self) -> dict:
        return {
            "government": self.government.as_dict(),
            "voters": len(self.voter_registry),
            "term_tick": self.term_tick,
            "election_cycle": self.election_cycle,
            "tech_restrictions": self.get_active_restrictions(),
        }
