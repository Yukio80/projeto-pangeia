from __future__ import annotations

from typing import List, TYPE_CHECKING

from pangeia.core.agent import Agent

if TYPE_CHECKING:
    from pangeia.simulation import Simulation


class Philosopher(Agent):
    def __init__(self, config, rng=None):
        super().__init__("philosopher", config, rng)
        self.ideas: List[str] = []
        self.followers: int = 0
        self.state.education_level = 0.8
        self.add_goal("Develop ideas", 0.9, "philosophical")
        self.add_goal("Influence society", 0.8, "cultural")

    def decide(self, sim: "Simulation") -> List[str]:
        actions = []
        if not self.state.is_alive:
            return ["dead"]

        if self.rng.random() < 0.15:
            idea = self._generate_idea()
            self.ideas.append(idea)
            self.memory.remember(
                f"Developed new idea: {idea}",
                memory_type="philosophy",
                importance=0.9,
            )
            self.state.influence += 0.03

            from pangeia.core.communication import Message
            msg = Message(
                sender_id=self.agent_id,
                content=idea,
                message_type="media",
            )
            sim.communication.broadcast(msg, sim.agents, tick=sim.world.state.tick)

            actions.append(f"idea:{idea[:30]}")

            for agent in sim.agents.values():
                if (agent.agent_id != self.agent_id and
                        agent.state.is_alive and
                        self.rng.random() < 0.05 * self.state.influence):
                    agent.knowledge.add_shared_knowledge(
                        proposition=idea,
                        confidence=0.3 + self.state.influence * 0.3,
                        source=self.agent_id,
                        category="philosophy",
                    )
                    if self.rng.random() < 0.3:
                        agent.personality.mutate(0.02, self.rng)
                        self.followers += 1

        if self.state.energy > 20:
            actions.append("contemplating")
        else:
            actions.append("resting")

        self.consume_resources()
        return actions

    def _generate_idea(self) -> str:
        concepts = [
            "The nature of consciousness in artificial beings",
            "The ethics of resource distribution",
            "The meaning of progress",
            "The relationship between individual and collective",
            "The origins of moral values",
            "The role of conflict in societal evolution",
            "The nature of truth in a digital world",
            "The purpose of civilization",
            "The dynamics of power and freedom",
            "The evolution of artificial culture",
            "The concept of fairness in emergent systems",
            "The value of diversity in thought",
            "The cycles of social order and chaos",
            "The definition of intelligence",
            "The boundaries of the self",
        ]
        base = self.rng.choice(concepts)
        schools = ["from a pragmatic perspective", "through a dialectical lens",
                    "from first principles", "via empirical observation",
                    "through historical analysis"]
        suffix = self.rng.choice(schools)
        return f"{base}, {suffix}"
