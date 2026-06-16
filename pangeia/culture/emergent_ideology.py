from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any, List, Optional, Set


PREFIXES: dict[str, list[str]] = {
    "technology_positive": ["Techno", "Digital", "Progressive", "Synthetic"],
    "technology_negative": ["Neo-Luddite", "Organic", "Primal", "Natural"],
    "economy_positive": ["Merchant", "Liberal", "Free", "Open"],
    "economy_negative": ["Collectivist", "Egalitarian", "Common", "Shared"],
    "governance_positive": ["Imperial", "Sovereign", "Order", "Unified"],
    "governance_negative": ["Anarchist", "Free", "Liberated", "Autonomous"],
    "social_positive": ["Humanist", "Social", "Communal", "Collective"],
    "social_negative": ["Individualist", "Solitary", "Isolated", "Pure"],
}

SUFFIXES: list[str] = [
    "Movement", "Doctrine", "Path", "Order", "Creed",
    "Way", "Philosophy", "Manifesto", "Vision", "Covenant",
]


@dataclass
class IdeologyTenet:
    domain: str
    stance: float
    target: str | None = None
    strength: float = 1.0


@dataclass
class EmergentIdeology:
    id: str
    name: str
    founder_id: str
    founder_class: str
    founded_tick: int
    tenets: list[IdeologyTenet] = field(default_factory=list)
    followers: set[str] = field(default_factory=set)
    influence: float = 0.0
    spread_rate: float = 0.05
    active: bool = True
    _decay_counter: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "founder_id": self.founder_id,
            "founder_class": self.founder_class,
            "founded_tick": self.founded_tick,
            "tenets": [
                {"domain": t.domain, "stance": t.stance,
                 "target": t.target, "strength": t.strength}
                for t in self.tenets
            ],
            "follower_count": len(self.followers),
            "influence": round(self.influence, 4),
            "spread_rate": self.spread_rate,
            "active": self.active,
        }


def _dominant_domain_stance(tenets: list[IdeologyTenet], domain: str) -> float | None:
    domain_tenets = [t for t in tenets if t.domain == domain and t.target is None]
    if not domain_tenets:
        return None
    return max(domain_tenets, key=lambda t: abs(t.stance)).stance


def generate_name(tenets: list[IdeologyTenet], rng: random.Random) -> str:
    prefix_pool = []
    for domain in ["technology", "economy", "governance", "social"]:
        stance = _dominant_domain_stance(tenets, domain)
        if stance is not None:
            key = f"{domain}_{'positive' if stance >= 0 else 'negative'}"
            prefix_pool.extend(PREFIXES.get(key, []))
    if not prefix_pool:
        prefix_pool = ["Neutral", "Generic"]
    prefix = rng.choice(prefix_pool)
    suffix = rng.choice(SUFFIXES)
    return f"{prefix} {suffix}"


def generate_tenets_from_personality(agent: Any, rng: random.Random) -> list[IdeologyTenet]:
    tenets: list[IdeologyTenet] = []
    personality = agent.personality

    tech_stance = (personality.curiosidade - 0.5) * 2
    tenets.append(IdeologyTenet(
        domain="technology",
        stance=tech_stance,
        target=None,
        strength=abs(tech_stance),
    ))

    agreeableness = (personality.empatia + personality.altruismo) / 2
    social_stance = (agreeableness - 0.5) * 2
    tenets.append(IdeologyTenet(
        domain="social",
        stance=social_stance,
        target=None,
        strength=abs(social_stance),
    ))

    gov_stance = (personality.disciplina - 0.5) * 2
    if abs(gov_stance) > 0.3:
        tenets.append(IdeologyTenet(
            domain="governance",
            stance=gov_stance,
            target=None,
            strength=abs(gov_stance),
        ))

    curiosidade_norm = (personality.curiosidade - 0.5) * 2
    if curiosidade_norm < -0.3:
        tenets.append(IdeologyTenet(
            domain="technology",
            stance=-0.8,
            target="Digital Ascension",
            strength=0.8,
        ))

    return tenets
