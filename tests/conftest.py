from __future__ import annotations

import random
from typing import Dict, Optional

import pytest

from pangeia.config import SimulationConfig
from pangeia.simulation import Simulation
from pangeia.core.agent import Agent
from pangeia.core.collective_memory import CollectiveMemorySystem
from pangeia.economy.market import Economy
from pangeia.governance.government import GovernanceSystem
from pangeia.culture.religion import ReligiousSystem
from pangeia.technology.tech_tree import TechnologySystem


@pytest.fixture
def seed() -> int:
    return 42


@pytest.fixture
def rng(seed: int) -> random.Random:
    return random.Random(seed)


@pytest.fixture
def config(seed: int) -> SimulationConfig:
    cfg = SimulationConfig.default()
    cfg.world.seed = seed
    cfg.world.initial_population = 30
    return cfg


@pytest.fixture
def simulation(config: SimulationConfig) -> Simulation:
    return Simulation(config)


@pytest.fixture
def small_simulation(seed: int) -> Simulation:
    cfg = SimulationConfig.default()
    cfg.world.seed = seed
    cfg.world.initial_population = 10
    return Simulation(cfg)


@pytest.fixture
def cm_system(rng: random.Random) -> CollectiveMemorySystem:
    return CollectiveMemorySystem(rng=rng)


@pytest.fixture
def economy(config: SimulationConfig) -> Economy:
    return Economy(config)


@pytest.fixture
def governance(config: SimulationConfig) -> GovernanceSystem:
    return GovernanceSystem(config)


@pytest.fixture
def religion(rng: random.Random) -> ReligiousSystem:
    return ReligiousSystem(rng=rng)


@pytest.fixture
def tech(rng: random.Random) -> TechnologySystem:
    return TechnologySystem(rng=rng)


@pytest.fixture
def ticked_simulation(simulation: Simulation) -> Simulation:
    for _ in range(50):
        simulation.step()
    return simulation


def assert_deterministic(sim_a: Simulation, sim_b: Simulation, ticks: int = 20):
    """Verifica que duas simulações com mesma seed produzem mesmo estado."""
    for t in range(ticks):
        sa = sim_a.step()
        sb = sim_b.step()
        for key in sa:
            if key in ("tick_time_ms",):
                continue
            assert sa[key] == sb[key], (
                f"Mismatch at tick {t} key '{key}': "
                f"{sa[key]} != {sb[key]}"
            )
