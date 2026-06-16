from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from pangeia.config import SimulationConfig
from pangeia.culture.ideology_manager import IdeologyManager


@dataclass
class ResourcePool:
    energy: float
    water: float
    food: float
    raw_materials: float
    compute: float

    def __add__(self, other: "ResourcePool") -> "ResourcePool":
        return ResourcePool(
            energy=self.energy + other.energy,
            water=self.water + other.water,
            food=self.food + other.food,
            raw_materials=self.raw_materials + other.raw_materials,
            compute=self.compute + other.compute,
        )

    def __sub__(self, other: "ResourcePool") -> "ResourcePool":
        return ResourcePool(
            energy=self.energy - other.energy,
            water=self.water - other.water,
            food=self.food - other.food,
            raw_materials=self.raw_materials - other.raw_materials,
            compute=self.compute - other.compute,
        )

    def clamp(self, min_val: float = 0) -> "ResourcePool":
        return ResourcePool(
            energy=max(min_val, self.energy),
            water=max(min_val, self.water),
            food=max(min_val, self.food),
            raw_materials=max(min_val, self.raw_materials),
            compute=max(min_val, self.compute),
        )

    def scale(self, factor: float) -> "ResourcePool":
        return ResourcePool(
            energy=self.energy * factor,
            water=self.water * factor,
            food=self.food * factor,
            raw_materials=self.raw_materials * factor,
            compute=self.compute * factor,
        )

    def as_dict(self) -> dict:
        return {
            "energy": round(self.energy, 2),
            "water": round(self.water, 2),
            "food": round(self.food, 2),
            "raw_materials": round(self.raw_materials, 2),
            "compute": round(self.compute, 2),
        }


@dataclass
class Territory:
    id: int
    name: str
    area: float
    resources: ResourcePool
    population: int = 0
    owner_id: Optional[str] = None


@dataclass
class WorldState:
    tick: int = 0
    time: float = 0.0
    global_resources: ResourcePool = field(default_factory=lambda: ResourcePool(0, 0, 0, 0, 0))
    territories: List[Territory] = field(default_factory=list)
    events: List[dict] = field(default_factory=list)

    def advance_time(self, delta: float = 1.0):
        self.tick += 1
        self.time += delta


class World:
    def __init__(self, config: SimulationConfig, rng: random.Random | None = None):
        self.config = config
        self.state = WorldState()
        self.ideology_manager = IdeologyManager(self, rng or random)

        cfg = config.resources
        self.state.global_resources = ResourcePool(
            energy=cfg.energy,
            water=cfg.water,
            food=cfg.food,
            raw_materials=cfg.raw_materials,
            compute=cfg.compute,
        )
        self._regen_rates = ResourcePool(
            energy=cfg.energy_regen,
            water=cfg.water_regen,
            food=cfg.food_regen,
            raw_materials=cfg.raw_materials_regen,
            compute=cfg.compute_regen,
        )
        self._init_territories()

    def _init_territories(self):
        names = [
            "Aethra", "Borealia", "Caelum", "Dravidia", "Erythra",
            "Ferox", "Gelida", "Hesperia", "Ithaka", "Jotunheim",
            "Kronos", "Lumina", "Mare", "Nyx", "Orion",
            "Polaris", "Quartus", "Regnum", "Solaris", "Tellus",
        ]
        total_area = self.config.world.territory_size
        per_territory = total_area // len(names)
        for i, name in enumerate(names):
            frac = random.uniform(0.5, 1.5)
            t = Territory(
                id=i,
                name=name,
                area=per_territory * frac,
                resources=self._random_resources(),
            )
            self.state.territories.append(t)

    def _random_resources(self) -> ResourcePool:
        return ResourcePool(
            energy=random.uniform(10_000, 100_000),
            water=random.uniform(10_000, 100_000),
            food=random.uniform(5_000, 50_000),
            raw_materials=random.uniform(5_000, 50_000),
            compute=random.uniform(1_000, 10_000),
        )

    def regenerate(self):
        r = self._regen_rates
        self.state.global_resources += r
        self.state.global_resources = self.state.global_resources.clamp()

    def consume(self, resources: ResourcePool) -> bool:
        new_pool = self.state.global_resources - resources
        if any(getattr(new_pool, attr) < 0 for attr in
               ["energy", "water", "food", "raw_materials", "compute"]):
            return False
        self.state.global_resources = new_pool
        return True

    def log_event(self, event_type: str, description: str, data: Optional[dict] = None):
        entry = {
            "tick": self.state.tick,
            "type": event_type,
            "description": description,
            "data": data or {},
        }
        self.state.events.append(entry)
        return entry

    def summary(self) -> dict:
        return {
            "tick": self.state.tick,
            "time": self.state.time,
            "resources": self.state.global_resources.as_dict(),
            "territories": len(self.state.territories),
            "events_recent": len(self.state.events),
        }
