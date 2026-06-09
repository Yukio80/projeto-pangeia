from __future__ import annotations

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from pangeia.simulation import Simulation


ERA_ORDER = [
    "primordial", "stone", "agricultural", "industrial",
    "information", "quantum", "singularity",
]


@dataclass
class Technology:
    id: str
    name: str
    era: str
    description: str
    prerequisites: List[str]
    effects: Dict[str, float]
    research_cost: float
    discovered: bool = False
    discoverer_id: Optional[str] = None
    discovery_tick: Optional[int] = None
    spread: float = 0.0

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "era": self.era,
            "description": self.description,
            "prerequisites": self.prerequisites,
            "effects": self.effects,
            "discovered": self.discovered,
            "discoverer": self.discoverer_id,
            "discovery_tick": self.discovery_tick,
            "spread": round(self.spread, 3),
        }


TECHNOLOGY_TREE: List[dict] = [
    {"id": "fire", "name": "Fire Mastery", "era": "primordial",
     "description": "Control of fire for warmth, protection, and cooking",
     "prerequisites": [], "research_cost": 10,
     "effects": {"productivity": 0.05, "survival": 0.1}},
    {"id": "tools", "name": "Basic Tools", "era": "primordial",
     "description": "Fashioning stones and sticks into tools",
     "prerequisites": [], "research_cost": 10,
     "effects": {"productivity": 0.1, "mining_efficiency": 0.1}},
    {"id": "language", "name": "Structured Language", "era": "primordial",
     "description": "Complex communication and knowledge transfer",
     "prerequisites": [], "research_cost": 15,
     "effects": {"education": 0.1, "cooperation": 0.1}},
    {"id": "agriculture", "name": "Agriculture", "era": "stone",
     "description": "Cultivation of crops and domestication of plants",
     "prerequisites": ["fire", "tools"],
     "research_cost": 30,
     "effects": {"food_production": 0.3, "population_capacity": 0.2, "productivity": 0.1}},
    {"id": "domestication", "name": "Animal Domestication", "era": "stone",
     "description": "Taming and breeding animals for labor and food",
     "prerequisites": ["fire"],
     "research_cost": 25,
     "effects": {"productivity": 0.15, "transport": 0.2}},
    {"id": "writing", "name": "Writing Systems", "era": "stone",
     "description": "Recording information and codifying knowledge",
     "prerequisites": ["language", "agriculture"],
     "research_cost": 40,
     "effects": {"education": 0.2, "administration": 0.2, "knowledge_transfer": 0.3}},
    {"id": "wheel", "name": "The Wheel", "era": "stone",
     "description": "Circular motion for transport and machinery",
     "prerequisites": ["tools"],
     "research_cost": 25,
     "effects": {"transport": 0.3, "productivity": 0.1}},
    {"id": "metallurgy", "name": "Metallurgy", "era": "agricultural",
     "description": "Extracting and shaping metals for tools and weapons",
     "prerequisites": ["tools", "fire"],
     "research_cost": 50,
     "effects": {"productivity": 0.2, "military": 0.2, "mining_efficiency": 0.3}},
    {"id": "currency", "name": "Currency & Trade", "era": "agricultural",
     "description": "Standardized medium of exchange enabling complex trade",
     "prerequisites": ["writing", "agriculture"],
     "research_cost": 45,
     "effects": {"trade_efficiency": 0.3, "taxation": 0.2, "gdp": 0.15}},
    {"id": "philosophy", "name": "Philosophy & Law", "era": "agricultural",
     "description": "Systematic thinking about ethics, governance, and existence",
     "prerequisites": ["writing", "language"],
     "research_cost": 50,
     "effects": {"governance": 0.2, "stability": 0.1, "culture": 0.3}},
    {"id": "sailing", "name": "Sailing & Navigation", "era": "agricultural",
     "description": "Travel across water for trade and exploration",
     "prerequisites": ["wheel", "domestication"],
     "research_cost": 40,
     "effects": {"transport": 0.3, "trade_efficiency": 0.2}},
    {"id": "steam_power", "name": "Steam Power", "era": "industrial",
     "description": "Harnessing steam for mechanical power",
     "prerequisites": ["metallurgy", "wheel"],
     "research_cost": 80,
     "effects": {"productivity": 0.3, "transport": 0.3, "energy": 0.3}},
    {"id": "electricity", "name": "Electricity", "era": "industrial",
     "description": "Generation and transmission of electrical power",
     "prerequisites": ["metallurgy", "steam_power"],
     "research_cost": 100,
     "effects": {"energy": 0.4, "productivity": 0.2, "computing": 0.2}},
    {"id": "mass_production", "name": "Mass Production", "era": "industrial",
     "description": "Assembly lines and scalable manufacturing",
     "prerequisites": ["steam_power", "currency"],
     "research_cost": 90,
     "effects": {"productivity": 0.4, "gdp": 0.3, "inequality": 0.1}},
    {"id": "medicine", "name": "Modern Medicine", "era": "industrial",
     "description": "Scientific understanding of disease and treatment",
     "prerequisites": ["writing", "agriculture"],
     "research_cost": 75,
     "effects": {"health": 0.3, "population_capacity": 0.2, "productivity": 0.1}},
    {"id": "computing", "name": "Computing", "era": "information",
     "description": "Electronic computation and data processing",
     "prerequisites": ["electricity", "mass_production"],
     "research_cost": 150,
     "effects": {"computing": 0.5, "productivity": 0.3, "education": 0.3}},
    {"id": "internet", "name": "Global Network", "era": "information",
     "description": "Interconnected communication systems spanning the world",
     "prerequisites": ["computing", "electricity"],
     "research_cost": 140,
     "effects": {"communication": 0.5, "knowledge_transfer": 0.4, "gdp": 0.2}},
    {"id": "automation", "name": "Automation & Robotics", "era": "information",
     "description": "Self-operating machines replacing human labor",
     "prerequisites": ["computing", "mass_production"],
     "research_cost": 160,
     "effects": {"productivity": 0.5, "unemployment": 0.2, "inequality": 0.15}},
    {"id": "biotech", "name": "Biotechnology", "era": "information",
     "description": "Manipulation of biological systems for practical purposes",
     "prerequisites": ["medicine", "computing"],
     "research_cost": 130,
     "effects": {"health": 0.3, "food_production": 0.3, "productivity": 0.1}},
    {"id": "ai", "name": "Artificial Intelligence", "era": "quantum",
     "description": "Machines capable of learning, reasoning, and creating",
     "prerequisites": ["computing", "automation", "internet"],
     "research_cost": 250,
     "effects": {"computing": 0.6, "productivity": 0.5, "education": 0.4}},
    {"id": "quantum_computing", "name": "Quantum Computing", "era": "quantum",
     "description": "Computation using quantum mechanical phenomena",
     "prerequisites": ["computing", "ai"],
     "research_cost": 280,
     "effects": {"computing": 0.7, "research_speed": 0.5, "energy": 0.2}},
    {"id": "nanotech", "name": "Nanotechnology", "era": "quantum",
     "description": "Engineering at the molecular and atomic scale",
     "prerequisites": ["biotech", "ai"],
     "research_cost": 300,
     "effects": {"productivity": 0.6, "health": 0.3, "mining_efficiency": 0.5}},
    {"id": "space_exploration", "name": "Space Exploration", "era": "quantum",
     "description": "Travel and habitation beyond the home world",
     "prerequisites": ["automation", "ai", "energy"],
     "research_cost": 350,
     "effects": {"resources": 0.5, "culture": 0.2, "energy": 0.3}},
    {"id": "singularity_ai", "name": "Singularity AI", "era": "singularity",
     "description": "Artificial superintelligence exceeding all human capability",
     "prerequisites": ["ai", "quantum_computing", "nanotech"],
     "research_cost": 500,
     "effects": {"computing": 1.0, "productivity": 1.0, "research_speed": 1.0}},
    {"id": "matter_energy", "name": "Matter-Energy Conversion", "era": "singularity",
     "description": "Direct conversion between matter and energy",
     "prerequisites": ["nanotech", "quantum_computing"],
     "research_cost": 600,
     "effects": {"energy": 1.0, "resources": 1.0, "productivity": 0.5}},
    {"id": "ascension", "name": "Digital Ascension", "era": "singularity",
     "description": "Transfer of consciousness to pure digital form",
     "prerequisites": ["singularity_ai", "matter_energy"],
     "research_cost": 1000,
     "effects": {"culture": 1.0, "education": 1.0, "computing": 1.0}},
]


class TechnologySystem:
    def __init__(self, rng: Optional[random.Random] = None):
        self.rng = rng or random.Random()
        self.technologies: Dict[str, Technology] = {}
        self.research_progress: Dict[str, float] = {}
        self._researchable_cache: Optional[List[Technology]] = None
        self._init_techs()

    def _init_techs(self):
        for t_def in TECHNOLOGY_TREE:
            tech = Technology(
                id=t_def["id"],
                name=t_def["name"],
                era=t_def["era"],
                description=t_def["description"],
                prerequisites=t_def["prerequisites"],
                effects=t_def["effects"],
                research_cost=t_def["research_cost"],
            )
            self.technologies[t_def["id"]] = tech
            self.research_progress[t_def["id"]] = 0.0

    def get_era(self) -> str:
        discovered_eras = set()
        for tech in self.technologies.values():
            if tech.discovered:
                discovered_eras.add(tech.era)
        for era in reversed(ERA_ORDER):
            if era in discovered_eras:
                return era
        return "primordial"

    def get_tech_level(self) -> float:
        total = len(self.technologies)
        if total == 0:
            return 0.0
        discovered = sum(1 for t in self.technologies.values() if t.discovered)
        era_bonus = ERA_ORDER.index(self.get_era()) / max(1, len(ERA_ORDER) - 1)
        return (discovered / total) * 0.6 + era_bonus * 0.4

    def can_research(self, tech_id: str) -> bool:
        tech = self.technologies.get(tech_id)
        if not tech or tech.discovered:
            return False
        for prereq in tech.prerequisites:
            ptech = self.technologies.get(prereq)
            if not ptech or not ptech.discovered:
                return False
        return True

    def research(self, tech_id: str, amount: float,
                 researcher_id: Optional[str] = None) -> bool:
        tech = self.technologies.get(tech_id)
        if not tech or tech.discovered:
            return False
        if not self.can_research(tech_id):
            return False
        self.research_progress[tech_id] += amount
        if self.research_progress[tech_id] >= tech.research_cost:
            tech.discovered = True
            tech.discoverer_id = researcher_id
            self._researchable_cache = None
            return True
        return False

    def get_researchable(self) -> List[Technology]:
        if self._researchable_cache is not None:
            return self._researchable_cache
        result = [
            t for t in self.technologies.values()
            if not t.discovered and self.can_research(t.id)
        ]
        self._researchable_cache = result
        return result

    def step(self, sim: Simulation):
        researchers = [
            a for a in sim.agents.values()
            if a.state.is_alive and a.state.agent_class == "researcher"
        ]
        for researcher in researchers:
            if self.rng.random() < 0.3:
                researchable = self.get_researchable()
                if not researchable:
                    continue
                target = self.rng.choice(researchable)
                progress = researcher.state.education_level * 2.0 * self.rng.uniform(0.5, 1.5)
                discovered = self.research(target.id, progress, researcher.agent_id)
                if discovered:
                    target.discovery_tick = sim.world.state.tick
                    researcher.state.add_life_event(
                        sim.world.state.tick, "discovery",
                        f"Discovered {target.name} ({target.era} era)",
                        0.9,
                    )
                    researcher.state.notable_achievements.append(
                        f"Discovered {target.name}"
                    )
                    researcher.state.influence += 0.15
                    sim.world.log_event(
                        "technology",
                        f"Technology discovered: {target.name} by {researcher.state.name}",
                        {"tech_id": target.id, "researcher": researcher.agent_id},
                    )
                    for effect_key, effect_val in target.effects.items():
                        self._apply_tech_effect(effect_key, effect_val, sim)

        self._spread_tech(sim)

    def _spread_tech(self, sim: Simulation):
        for tech in self.technologies.values():
            if not tech.discovered:
                continue
            tech.spread = min(1.0, tech.spread + 0.001)
            if self.rng.random() < 0.01 * tech.spread:
                for agent in sim.agents.values():
                    if agent.state.is_alive and self.rng.random() < 0.001:
                        agent.knowledge.add_shared_knowledge(
                            proposition=f"Knowledge of {tech.name}",
                            confidence=self.rng.uniform(0.3, 0.6),
                            source="cultural_diffusion",
                            category="technology",
                        )

    def _apply_tech_effect(self, key: str, value: float, sim: Simulation):
        if key == "productivity":
            for agent in sim.agents.values():
                if agent.state.is_alive:
                    agent.state.productivity *= (1 + value * 0.05)
        elif key == "education":
            for agent in sim.agents.values():
                if agent.state.is_alive:
                    agent.state.education_level = min(
                        1.0, agent.state.education_level + value * 0.02
                    )
        elif key == "computing" and sim.economy:
            pass
        elif key == "governance" and sim.governance:
            sim.governance.government.stability = min(
                1.0, sim.governance.government.stability + value * 0.02
            )
        if sim.economy:
            sim.economy.indicators.tech_level = self.get_tech_level()

    def summary(self) -> dict:
        discovered = [t for t in self.technologies.values() if t.discovered]
        by_era = {}
        for tech in self.technologies.values():
            by_era.setdefault(tech.era, {"total": 0, "discovered": 0})
            by_era[tech.era]["total"] += 1
            if tech.discovered:
                by_era[tech.era]["discovered"] += 1
        return {
            "era": self.get_era(),
            "tech_level": round(self.get_tech_level(), 3),
            "total_technologies": len(self.technologies),
            "discovered": len(discovered),
            "researchable": len(self.get_researchable()),
            "by_era": by_era,
            "recent_discoveries": [
                t.as_dict() for t in discovered[-5:]
            ],
            "current_era_index": ERA_ORDER.index(self.get_era()),
            "max_era_index": len(ERA_ORDER) - 1,
        }
