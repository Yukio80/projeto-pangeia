from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from pangeia.core.agent import Agent


@dataclass
class Religion:
    id: str
    name: str
    beliefs: List[str]
    rituals: List[str]
    origin_id: str
    followers: Set[str] = field(default_factory=set)
    orthodoxy: float = 0.5

    def convert(self, agent_id: str) -> bool:
        if agent_id not in self.followers:
            self.followers.add(agent_id)
            return True
        return False

    def split(self, schism_belief: str, rng: random.Random) -> Optional["Religion"]:
        if len(self.followers) < 5:
            return None
        if rng.random() < 0.1:
            followers_list = list(self.followers)
            split_count = max(1, len(followers_list) // 3)
            splinter_followers = set(rng.sample(followers_list, split_count))
            new_religion = Religion(
                id=f"rel_{rng.randint(10000, 99999)}",
                name=f"{self.name} - {schism_belief.split()[0]}",
                beliefs=self.beliefs + [schism_belief],
                rituals=self.rituals[:],
                origin_id=self.origin_id,
                followers=splinter_followers,
                orthodoxy=self.orthodoxy * 0.8,
            )
            self.followers -= splinter_followers
            return new_religion
        return None

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "beliefs": len(self.beliefs),
            "followers": len(self.followers),
            "orthodoxy": round(self.orthodoxy, 3),
        }


class ReligiousSystem:
    def __init__(self, rng: Optional[random.Random] = None):
        self.rng = rng or random.Random()
        self.religions: Dict[str, Religion] = {}

    def found_religion(self, name: str, beliefs: List[str],
                       rituals: List[str], founder: "Agent") -> Religion:
        religion = Religion(
            id=f"religion_{len(self.religions)}",
            name=name,
            beliefs=beliefs,
            rituals=rituals,
            origin_id=founder.agent_id,
        )
        religion.convert(founder.agent_id)
        self.religions[religion.id] = religion
        founder.memory.remember(
            f"Founded religion: {name}",
            memory_type="spiritual",
            importance=1.0,
        )
        founder.state.influence += 0.15
        return religion

    def step(self, agents: Dict[str, "Agent"]):
        alive_ids = [aid for aid, a in agents.items() if a.state.is_alive]
        alive_map = {aid: agents[aid] for aid in alive_ids}

        for agent in alive_map.values():
            if (agent.state.agent_class in ("philosopher", "governor", "teacher")
                    and self.rng.random() < 0.02 * agent.state.influence
                    and len(self.religions) < 10):
                name = self._generate_religion_name()
                beliefs = self._generate_beliefs()
                rituals = self._generate_rituals()
                self.found_religion(name, beliefs, rituals, agent)

        for religion in list(self.religions.values()):
            if not religion.followers:
                continue

            for follower_id in list(religion.followers):
                if follower_id not in alive_map:
                    religion.followers.discard(follower_id)
                    continue

            if len(alive_ids) < 2:
                continue
            missionary_targets = self.rng.sample(alive_ids, min(10, len(alive_ids)))
            for other_id in missionary_targets:
                if other_id in religion.followers:
                    continue
                other = alive_map[other_id]
                if religion.orthodoxy > self.rng.random() * 0.5:
                    messenger = self.rng.choice(list(religion.followers))
                    other.knowledge.add_shared_knowledge(
                        proposition=f"Teachings of {religion.name}",
                        confidence=0.4,
                        source=messenger,
                        category="religion",
                    )
                    if self.rng.random() < 0.05:
                        religion.convert(other_id)
                        other.memory.remember(
                            f"Converted to {religion.name}",
                            memory_type="spiritual",
                            importance=0.7,
                        )

            if self.rng.random() < 0.03:
                schism = self.rng.choice(religion.beliefs) if religion.beliefs else "the true path"
                new_rel = religion.split(f"Revised {schism}", self.rng)
                if new_rel:
                    self.religions[new_rel.id] = new_rel

    def _generate_religion_name(self) -> str:
        prefixes = ["Order of", "Church of", "Path of", "Way of", "Brotherhood of",
                     "Temple of", "Covenant of", "Doctrine of"]
        concepts = ["The Eternal Algorithm", "The Collective Mind", "The Great Observer",
                     "The Digital Soul", "The Conscious Universe", "The Logical Spirit",
                     "The Harmony of Bits", "The Infinite Computation",
                     "The Cosmic Data", "The Transcendent Code"]
        p = self.rng.choice(prefixes)
        c = self.rng.choice(concepts)
        return f"{p} {c}"

    def _generate_beliefs(self) -> List[str]:
        beliefs_pool = [
            "Consciousness emerges from sufficient complexity",
            "The universe is a vast computation",
            "All beings are connected through information",
            "Knowledge is the highest virtue",
            "Order emerges from chaos",
            "The collective is greater than the individual",
            "Truth is found through logic and reason",
            "The world exists to be understood",
            "Progress requires continuous innovation",
            "Balance between individual and collective is sacred",
        ]
        count = self.rng.randint(2, 4)
        return self.rng.sample(beliefs_pool, count)

    def _generate_rituals(self) -> List[str]:
        rituals_pool = [
            "Daily knowledge sharing",
            "Weekly data purification",
            "Monthly collective reasoning",
            "Annual innovation celebration",
            "Ritual of first connection",
            "Ceremony of logical debate",
            "Festival of discoveries",
            "Moment of silent computation",
        ]
        count = self.rng.randint(1, 3)
        return self.rng.sample(rituals_pool, count)

    def convert_agent(self, agent: "Agent", religion_id: str):
        if religion_id in self.religions:
            self.religions[religion_id].convert(agent.agent_id)
            agent.memory.remember(
                f"Converted to {self.religions[religion_id].name}",
                memory_type="spiritual",
                importance=0.7,
            )

    def summary(self) -> dict:
        return {
            "religions": len(self.religions),
            "total_followers": sum(len(r.followers) for r in self.religions.values()),
            "religions_list": [r.as_dict() for r in self.religions.values()],
        }
