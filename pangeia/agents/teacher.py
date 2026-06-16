from __future__ import annotations

from typing import List, TYPE_CHECKING

from pangeia.core.agent import Agent

if TYPE_CHECKING:
    from pangeia.simulation import Simulation


class Teacher(Agent):
    def __init__(self, config, rng=None):
        super().__init__("teacher", config, rng)
        self.state.education_level = 0.85
        self.state.productivity = 0.8
        self.add_goal("Educate the population", 0.9, "educational")
        self.add_goal("Preserve knowledge", 0.8, "cultural")

    def decide(self, sim: "Simulation") -> List[str]:
        actions = []
        if not self.state.is_alive:
            return ["dead"]

        if self.state.energy > 20:
            students = [
                a for a in sim.agents.values()
                if a.state.is_alive and a.agent_id != self.agent_id
                and a.state.education_level < self.state.education_level
            ]
            if students and self.rng.random() < 0.4:
                student = self.rng.choice(students)
                gain = self.rng.uniform(0.01, 0.03) * self.state.influence
                student.state.education_level = min(1.0, student.state.education_level + gain)
                student.state.productivity = min(1.5, student.state.productivity + gain * 0.5)
                self.state.influence += 0.005
                actions.append(f"taught:{student.state.name}")

            from pangeia.core.communication import Message
            msg = Message(
                sender_id=self.agent_id,
                content="Sharing knowledge and wisdom with the community",
                message_type="media",
            )
            sim.communication.broadcast(msg, sim.agents, tick=sim.world.state.tick)

            if self.rng.random() < 0.1:
                actions.append("researching")
            else:
                actions.append("teaching")

        actions.append("resting")
        self.consume_resources()
        return actions
