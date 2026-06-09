from __future__ import annotations

from typing import List, TYPE_CHECKING

from pangeia.core.agent import Agent

if TYPE_CHECKING:
    from pangeia.simulation import Simulation


class Journalist(Agent):
    def __init__(self, config, rng=None):
        super().__init__("journalist", config, rng)
        self.articles_written: List[str] = []
        self.bias: float = self.rng.gauss(0, 0.2)
        self.add_goal("Inform the public", 0.8, "information")
        self.add_goal("Gain influence", 0.7, "social")

    def decide(self, sim: "Simulation") -> List[str]:
        actions = []
        if not self.state.is_alive:
            return ["dead"]

        if self.state.energy > 20:
            article = self._write_article(sim)
            self.articles_written.append(article)
            self.memory.remember(
                f"Published article: {article}",
                memory_type="publication",
                importance=0.6,
            )

            from pangeia.core.communication import Message
            msg = Message(
                sender_id=self.agent_id,
                content=article,
                message_type="media",
                truth_value=self.rng.random() > abs(self.bias),
            )
            sim.communication.broadcast(msg, sim.agents, tick=sim.world.state.tick)

            self.state.influence += 0.02
            actions.append(f"published:{article[:30]}")

        actions.append("investigating")
        self.consume_resources()
        return actions

    def _write_article(self, sim: "Simulation") -> str:
        topics = ["economy", "politics", "resources", "society", "technology",
                   "conflict", "culture", "science"]
        topic = self.rng.choice(topics)
        events = sim.world.state.events[-5:] if sim.world.state.events else []
        if events:
            event = self.rng.choice(events)
            base = f"Report on {topic}: {event['description']}"
        else:
            base = f"Analysis of current {topic} in Pangeia"
        if self.rng.random() < abs(self.bias):
            if self.bias > 0:
                base += " [optimistic tone]"
            else:
                base += " [critical tone]"
        return base
