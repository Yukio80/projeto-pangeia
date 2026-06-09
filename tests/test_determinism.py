"""Teste de determinismo: mesma seed → mesmo estado."""

from pangeia.config import SimulationConfig
from pangeia.simulation import Simulation


def _run_sim(seed: int, population: int = 30, ticks: int = 50):
    cfg = SimulationConfig.default()
    cfg.world.seed = seed
    cfg.world.initial_population = population
    sim = Simulation(cfg)
    snapshots = []
    for _ in range(ticks):
        snapshots.append(sim.step().as_dict())
    return sim, snapshots


def test_same_seed_same_state():
    sim_a, snaps_a = _run_sim(42)
    sim_b, snaps_b = _run_sim(42)

    for tick, (sa, sb) in enumerate(zip(snaps_a, snaps_b)):
        for key in sa:
            if key == "tick_time_ms":
                continue
            assert sa[key] == sb[key], (
                f"Seed determinism failed at tick {tick}, key '{key}': "
                f"{sa[key]} != {sb[key]}"
            )

    ids_a = sorted(sim_a.agents.keys())
    ids_b = sorted(sim_b.agents.keys())
    assert ids_a == ids_b, "Agent ID sets differ between runs"


def test_different_seeds_different_state():
    sim_a, _ = _run_sim(42)
    sim_b, _ = _run_sim(99)

    ids_a = sorted(sim_a.agents.keys())
    ids_b = sorted(sim_b.agents.keys())
    assert ids_a != ids_b, "Different seeds should produce different agent IDs"


def test_rng_controls_all_iteration():
    sim_a, snaps_a = _run_sim(42, ticks=100)
    sim_b, snaps_b = _run_sim(42, ticks=100)

    for tick, (sa, sb) in enumerate(zip(snaps_a, snaps_b)):
        for key in sa:
            if key == "tick_time_ms":
                continue
            assert sa[key] == sb[key], (
                f"Iteration determinism failed at tick {tick}, key '{key}'"
            )

    wealths_a = [a.state.wealth for a in sorted(sim_a.agents.values(), key=lambda x: x.agent_id)]
    wealths_b = [a.state.wealth for a in sorted(sim_b.agents.values(), key=lambda x: x.agent_id)]
    assert wealths_a == wealths_b, "Wealth order diverged between deterministic runs"
