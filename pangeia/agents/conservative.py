from __future__ import annotations

from typing import Any, List, TYPE_CHECKING

from pangeia.core.agent import Agent

if TYPE_CHECKING:
    from pangeia.simulation import Simulation


HIGH_RISK_TECHNOLOGIES = {
    "Digital Ascension",
    "Neural Interface",
    "Genetic Engineering",
    "Artificial General Intelligence",
}

HIGH_RISK_THRESHOLD_ERA = 4


class Conservative(Agent):
    def __init__(self, config, rng=None):
        super().__init__("conservative", config, rng)
        self.lobbying_power = 0.3 + (self.personality.disciplina * 0.4)
        self.risk_awareness = 0.5 + ((1.0 - self.personality.curiosidade) * 0.3)
        if self.personality.curiosidade < 0.5:
            self.risk_awareness = min(1.0, self.risk_awareness + 0.2)
        self._lobbying_cooldown = 0
        self._active_campaigns: dict[str, int] = {}
        self.add_goal("Restrict dangerous technology", 0.9, "political")
        self.add_goal("Preserve social stability", 0.8, "cultural")

    def decide(self, sim: "Simulation") -> List[str]:
        actions = []
        if not self.state.is_alive:
            return ["dead"]

        perception = self.perceive(sim)
        risks = self._identify_risks(perception)

        for tech_name in risks:
            if tech_name in self._active_campaigns:
                self._reinforce_campaign(tech_name, sim)
                actions.append(f"reinforce:{tech_name}")
            elif self._lobbying_cooldown <= 0:
                influence = self._lobby_governor(tech_name, sim)
                if influence > 0:
                    self._active_campaigns[tech_name] = sim.world.state.tick
                    self._lobbying_cooldown = 20
                    actions.append(f"lobbying:{tech_name}")
                    sim.world.log_event(
                        "politics",
                        f"Conservative {self.state.name} lobbied against {tech_name}",
                        {"tech": tech_name, "influence": round(influence, 3)},
                    )

        if self._lobbying_cooldown > 0:
            self._lobbying_cooldown -= 1

        if self.rng.random() < 0.1:
            actions.append("socializing")
        actions.append("contemplating")
        self.consume_resources()
        return actions

    def perceive(self, sim: "Simulation") -> dict:
        base = super().perceive(sim)
        tech_info = {}
        if sim.technology:
            tech_info["technologies_in_research"] = [
                t.as_dict() for t in sim.technology.get_researchable()
            ]
            tech_info["recently_discovered"] = [
                t.as_dict() for t in sim.technology.technologies.values()
                if t.discovered
                and t.discovery_tick is not None
                and sim.world.state.tick - t.discovery_tick < 50
            ]
        tech_info["active_tech_restrictions"] = sim.world.governance.get_active_restrictions() if hasattr(sim.world, 'governance') else []
        governors = [
            a for a in sim.agents.values()
            if a.state.is_alive and a.state.agent_class == "governor"
        ]
        sample = self.rng.sample(governors, min(10, len(governors))) if len(governors) <= 10 else self.rng.sample(governors, 10)
        tech_info["nearby_governors"] = [g.state.name for g in sample]
        active_anti = []
        try:
            for ideo in sim.world.ideology_manager.ideologies.values():
                if not ideo.active:
                    continue
                for tenet in ideo.tenets:
                    if tenet.domain == "technology" and tenet.stance < -0.3:
                        active_anti.append(ideo.name)
                        break
        except Exception:
            pass
        tech_info["active_anti_tech_ideologies"] = active_anti
        base["technology"] = tech_info
        return base

    def _identify_risks(self, perception: dict) -> list[str]:
        risks: list[str] = []
        tech = perception.get("technology", {})
        for t in tech.get("technologies_in_research", []):
            name = t.get("name", "")
            era_idx = _era_index(t.get("era", "primordial"))
            if name in HIGH_RISK_TECHNOLOGIES or era_idx >= HIGH_RISK_THRESHOLD_ERA:
                risks.append(name)
        for t in tech.get("recently_discovered", []):
            name = t.get("name", "")
            if name in HIGH_RISK_TECHNOLOGIES:
                risks.append(name)
        return risks

    def _lobby_governor(self, technology_name: str, sim: "Simulation") -> float:
        governors = [
            a for a in sim.agents.values()
            if a.state.is_alive and a.state.agent_class == "governor"
        ]
        if not governors:
            return 0.0
        total_influence = 0.0
        sample = self.rng.sample(governors, min(10, len(governors)))
        for gov in sample:
            receptivity = gov.personality.disciplina + (1.0 - gov.personality.curiosidade) * 0.5
            if receptivity > 0.4:
                gov_reader = _GovernanceReader(sim.world.governance)
                gov_reader.propose_tech_restriction(technology_name, self.lobbying_power)
                total_influence += self.lobbying_power
        return total_influence

    def _reinforce_campaign(self, technology_name: str, sim: "Simulation"):
        try:
            im = sim.world.ideology_manager
            found = False
            for ideo in im.ideologies.values():
                if not ideo.active:
                    continue
                for tenet in ideo.tenets:
                    if tenet.domain == "technology" and tenet.stance < -0.3:
                        ideo.influence = min(1.0, ideo.influence + 0.01)
                        found = True
                        break
                if found:
                    break
        except Exception:
            pass

    def get_status(self) -> dict:
        return {
            "id": self.agent_id,
            "class": "conservative",
            "lobbying_power": round(self.lobbying_power, 3),
            "risk_awareness": round(self.risk_awareness, 3),
            "active_campaigns": list(self._active_campaigns.keys()),
            "lobbying_cooldown": self._lobbying_cooldown,
        }


def _era_index(era: str) -> int:
    from pangeia.technology.tech_tree import ERA_ORDER
    try:
        return ERA_ORDER.index(era)
    except ValueError:
        return -1


class _GovernanceReader:
    def __init__(self, governance_system):
        self._gs = governance_system

    def propose_tech_restriction(self, technology_name: str, lobbying_power: float):
        self._gs.propose_tech_restriction(technology_name, lobbying_power)
