from __future__ import annotations

import random

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from pangeia.core.memory import Memory
from pangeia.core.psychology import (
    Temperament, EmotionalState, Goal,
    Archetype, ArchetypeType,
    random_archetype, ARCHETYPE_DEFINITIONS,
    generate_temperament_with_contradictions,
    AgentBehaviorModifiers, EmotionalMemory,
    PsychologicalNeeds, CulturalInfluence,
    get_emotional_profile,
    compute_action_bias,
)
from pangeia.core.knowledge import KnowledgeBase
from pangeia.core.social_network import SocialNetwork
from pangeia.config import SimulationConfig

if TYPE_CHECKING:
    from pangeia.simulation import Simulation


@dataclass
class ReputationEntry:
    agent_id: str
    trust: float
    respect: float
    fear: float
    last_interaction: int = 0

    def as_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "trust": round(self.trust, 3),
            "respect": round(self.respect, 3),
            "fear": round(self.fear, 3),
        }


@dataclass
class PersonalRelation:
    agent_id: str
    relation_type: str
    strength: float
    reason: str
    tick: int

    def as_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "type": self.relation_type,
            "strength": round(self.strength, 3),
            "reason": self.reason,
            "tick": self.tick,
        }


@dataclass
class LifeEvent:
    tick: int
    event_type: str
    description: str
    importance: float

    def as_dict(self) -> dict:
        return {
            "tick": self.tick,
            "type": self.event_type,
            "description": self.description,
            "importance": round(self.importance, 2),
        }


@dataclass
class AgentState:
    agent_id: str
    name: str
    agent_class: str

    wealth: float
    health: float
    energy: float
    age: int = 0
    is_alive: bool = True

    territory_id: Optional[int] = None
    employer_id: Optional[str] = None
    political_alignment: float = 0.0

    education_level: float = 0.3
    productivity: float = 1.0
    influence: float = 0.0

    reputation: Dict[str, ReputationEntry] = field(default_factory=dict)
    personal_relations: List[PersonalRelation] = field(default_factory=list)
    life_events: List[LifeEvent] = field(default_factory=list)
    notable_achievements: List[str] = field(default_factory=list)

    def add_life_event(self, tick: int, event_type: str,
                       description: str, importance: float = 0.5):
        self.life_events.append(LifeEvent(
            tick=tick, event_type=event_type,
            description=description, importance=importance,
        ))
        if len(self.life_events) > 50:
            self.life_events = self.life_events[-50:]

    def add_personal_relation(self, other_id: str, relation_type: str,
                              strength: float, reason: str, tick: int):
        existing = [r for r in self.personal_relations
                    if r.agent_id == other_id and r.relation_type == relation_type]
        if existing:
            existing[0].strength = max(existing[0].strength, strength)
            existing[0].tick = tick
        else:
            self.personal_relations.append(PersonalRelation(
                agent_id=other_id, relation_type=relation_type,
                strength=strength, reason=reason, tick=tick,
            ))
            if len(self.personal_relations) > 30:
                self.personal_relations = self.personal_relations[-30:]

    def get_friends(self) -> List[str]:
        return [
            r.agent_id for r in self.personal_relations
            if r.relation_type == "friend" and r.strength > 0.3
        ]

    def get_enemies(self) -> List[str]:
        return [
            r.agent_id for r in self.personal_relations
            if r.relation_type == "enemy" and r.strength > 0.3
        ]

    def memory_footprint(self) -> dict:
        return {
            "life_events": len(self.life_events),
            "personal_relations": len(self.personal_relations),
            "reputation": len(self.reputation),
            "notable_achievements": len(self.notable_achievements),
        }

    def trim_reputation(self, max_entries: int = 20):
        if len(self.reputation) > max_entries:
            sorted_entries = sorted(
                self.reputation.values(),
                key=lambda e: e.last_interaction,
                reverse=True,
            )
            keep = {e.agent_id for e in sorted_entries[:max_entries]}
            self.reputation = {
                k: v for k, v in self.reputation.items() if k in keep
            }

    def as_dict(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "class": self.agent_class,
            "wealth": round(self.wealth, 2),
            "health": round(self.health, 2),
            "energy": round(self.energy, 2),
            "age": self.age,
            "alive": self.is_alive,
            "territory_id": self.territory_id,
            "employer_id": self.employer_id,
            "political_alignment": round(self.political_alignment, 3),
            "education": round(self.education_level, 3),
            "productivity": round(self.productivity, 3),
            "influence": round(self.influence, 3),
            "friends": len(self.get_friends()),
            "enemies": len(self.get_enemies()),
            "achievements": self.notable_achievements[-5:],
        }


class Agent(ABC):
    def __init__(self, agent_class: str, config: SimulationConfig,
                 rng: Optional[random.Random] = None):
        self.config = config
        self.rng = rng or random.Random()
        self.agent_id = f"A{self.rng.getrandbits(32):08x}"

        self.state = AgentState(
            agent_id=self.agent_id,
            name=self._generate_name(),
            agent_class=agent_class,
            wealth=config.agent.starting_wealth,
            health=config.agent.max_health,
            energy=100.0,
        )

        # --- Novo sistema de personalidade ---
        self.temperament = generate_temperament_with_contradictions(self.rng)
        archetype_type = random_archetype(self.rng)
        self.archetype: Archetype = ARCHETYPE_DEFINITIONS[archetype_type]
        self.temperament = self.archetype.apply(self.temperament)
        self._contradictions = self.temperament.contradictions()

        # Backward compat para código que usa self.personality
        self._personality_backdoor = self.temperament.as_dict()

        self.emotions = EmotionalState()
        self.behavior_modifiers = AgentBehaviorModifiers()
        self.emotional_memories: List[EmotionalMemory] = []
        self.needs = PsychologicalNeeds()
        self.cultural_influences: List[CulturalInfluence] = []

        self.memory = Memory(capacity=config.agent.memory_capacity)
        self.knowledge = KnowledgeBase(max_items=config.agent.max_knowledge_items)
        self.social = SocialNetwork(self.agent_id)
        self.goals: List[Goal] = []
        self.skills: Dict[str, float] = {}

        # Metas do arquétipo
        for g in self.archetype.preferred_goals:
            self.add_goal(**g)

        self.memory.remember(
            f"I am {self.state.name}, a {agent_class} in the world of Pangeia.",
            memory_type="identity",
            importance=1.0,
        )

    @property
    def personality(self) -> Temperament:
        return self.temperament

    def _generate_name(self) -> str:
        prefixes = ["Ae", "Be", "Ca", "De", "El", "Fa", "Ga", "He", "Ir", "Ka",
                     "Le", "Ma", "Na", "Or", "Pa", "Qu", "Ra", "Sa", "Ta", "Va"]
        suffixes = ["ius", "on", "ara", "or", "is", "os", "um", "ia", "an", "en"]
        return f"{self.rng.choice(prefixes)}{self.rng.choice(suffixes)}"

    @abstractmethod
    def decide(self, sim: "Simulation") -> List[str]:
        ...

    def perceive(self, sim: "Simulation") -> dict:
        world = sim.world
        cache = getattr(sim, '_expensive_cache', {})
        return {
            "tick": world.state.tick,
            "resources": cache.get('resources') or world.state.global_resources.as_dict(),
            "population": len(sim.agents),
            "economy": cache.get('economy_summary') or (sim.economy.summary() if sim.economy else {}),
            "governance": cache.get('governance_summary') or (sim.governance.summary() if sim.governance else {}),
            "my_state": self.state.as_dict(),
        }

    def consume_resources(self) -> bool:
        cfg = self.config.agent
        needed = {
            "energy": cfg.base_energy_consumption,
            "food": cfg.base_food_consumption,
            "water": cfg.base_water_consumption,
            "compute": cfg.base_compute_cost * self.state.productivity,
        }

        self.state.energy -= needed["energy"]
        if self.state.energy <= 0:
            self.state.health -= 5
            return False

        self.state.health = max(0, self.state.health - 0.1)
        if self.state.health <= 0:
            self.state.is_alive = False

        return True

    def work(self, base_output: float = 1.0) -> float:
        output = base_output * self.state.productivity * self.state.education_level
        output *= random.uniform(0.8, 1.2)
        self.state.energy -= 2.0
        return output

    def learn(self, topic: str, amount: float = 0.01):
        if topic not in self.skills:
            self.skills[topic] = 0.0
        self.skills[topic] = min(1.0, self.skills[topic] + amount)
        self.state.education_level = min(1.0, self.state.education_level + amount * 0.1)
        self.state.productivity = 1.0 + self.state.education_level * 0.5

    def communicate(self, other: "Agent", message: str, importance: float = 0.3):
        self.memory.remember(
            f"Told {other.state.name}: {message}",
            memory_type="communication",
            importance=importance,
        )
        other.memory.remember(
            f"Received from {self.state.name}: {message}",
            memory_type="communication",
            importance=importance,
        )
        self.social.add_relationship(other.agent_id)
        other.social.add_relationship(self.agent_id)

    def add_goal(self, description: str, priority: float,
                 goal_type: str, target: str = ""):
        self.goals.append(Goal(
            description=description,
            priority=priority,
            goal_type=goal_type,
            target=target,
        ))
        self.goals.sort(key=lambda g: g.priority, reverse=True)
        self.goals = self.goals[:5]

    def record_emotional_event(self, tick: int, event_type: str,
                                description: str, participants: Optional[List[str]] = None):
        """Registra um evento com carga emocional."""
        profile = get_emotional_profile(event_type)
        if not profile and event_type in ("robbery", "assault", "death", "war",
                                           "victory", "defeat", "betrayal", "famine",
                                           "disease", "disaster"):
            profile = {"fear": 0.5, "sadness": 0.3, "trust": -0.2}

        if not profile:
            return

        mem = EmotionalMemory(
            event_id=f"{tick}_{event_type}_{self.agent_id}",
            tick=tick,
            event_type=event_type,
            description=description,
            participants=participants or [],
            anger=profile.get("anger", 0),
            fear=profile.get("fear", 0),
            sadness=profile.get("sadness", 0),
            joy=profile.get("joy", 0),
            trust=profile.get("trust", 0),
        )
        self.emotional_memories.append(mem)
        if len(self.emotional_memories) > 50:
            self.emotional_memories = self.emotional_memories[-50:]

        # Aplica delta imediato no estado emocional
        self.emotions.update(
            delta_happiness=profile.get("happiness", 0) * 0.3,
            delta_trust=profile.get("trust", 0) * 0.3,
            delta_anger=profile.get("anger", 0) * 0.3,
            delta_fear=profile.get("fear", 0) * 0.3,
            delta_curiosity=profile.get("curiosity", 0) * 0.3,
            delta_sadness=profile.get("sadness", 0) * 0.3,
        )

    def add_cultural_influence(self, group_name: str, group_type: str,
                                values: Optional[Dict[str, float]] = None):
        """Adiciona ou atualiza influência cultural."""
        existing = [c for c in self.cultural_influences if c.group_name == group_name]
        if existing:
            ci = existing[0]
            if values:
                ci.values.update(values)
        else:
            self.cultural_influences.append(CulturalInfluence(
                group_name=group_name,
                group_type=group_type,
                values=values or {},
            ))

    def compute_action_score(self, action: str, tick: int) -> float:
        """Aplica a fórmula completa de decisão."""
        return compute_action_bias(
            action=action,
            temperament=self.temperament,
            modifiers=self.behavior_modifiers,
            emotions=self.emotions,
            needs=self.needs,
            tick=tick,
        )

    def summarize(self) -> dict:
        return {
            **self.state.as_dict(),
            "personality": self.temperament.as_dict(),
            "archetype": self.archetype.name if self.archetype else "none",
            "contradictions": self._contradictions,
            "emotions": self.emotions.as_dict(),
            "needs": self.needs.as_dict(),
            "behavior_modifiers": self.behavior_modifiers.count(),
            "emotional_memories": len(self.emotional_memories),
            "cultural_influences": [c.as_dict() for c in self.cultural_influences],
            "memory": self.memory.summarize(),
            "knowledge": self.knowledge.summarize(),
            "social": self.social.summarize(),
            "goals": [g.as_dict() for g in self.goals[:3]],
            "skills": dict(sorted(self.skills.items(), key=lambda x: x[1], reverse=True)[:5]),
            "life_events": [e.as_dict() for e in self.state.life_events[-10:]],
            "reputation": [r.as_dict() for r in self.state.reputation.values()][:10],
            "relations": [r.as_dict() for r in self.state.personal_relations[-10:]],
        }
