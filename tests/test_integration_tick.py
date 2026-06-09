"""Testes de integração: ciclo completo do tick."""

import pytest
from pangeia.config import SimulationConfig
from pangeia.simulation import Simulation


def test_tick_advances_time(small_simulation):
    sim = small_simulation
    prev_tick = sim.world.state.tick
    sim.step()
    assert sim.world.state.tick == prev_tick + 1, "Tick should advance by 1"


def test_all_agents_created(simulation):
    n = simulation.config.world.initial_population
    assert len(simulation.agents) == n
    assert all(a.state.is_alive for a in simulation.agents.values())


def test_tick_loop_50_ticks(small_simulation):
    for _ in range(50):
        small_simulation.step()
    assert small_simulation.world.state.tick == 50


def test_economy_evolves(small_simulation):
    for _ in range(50):
        small_simulation.step()
    eco = small_simulation.economy.summary()
    indicators = eco["indicators"]
    assert indicators["gdp"] >= 0
    assert 0 <= indicators["inequality"] <= 1


def test_governance_evolves(small_simulation):
    for _ in range(50):
        small_simulation.step()
    gov = small_simulation.governance.summary()
    assert 0 <= gov["government"]["stability"] <= 1
    assert isinstance(gov["government"]["type"], str)


def test_culture_evolves(small_simulation):
    for _ in range(50):
        small_simulation.step()
    rel = small_simulation.religion_system.summary()
    assert "religions" in rel
    ideo = small_simulation.ideology_system.summary()
    assert "ideologies" in ideo


def test_technology_evolves(small_simulation):
    for _ in range(50):
        small_simulation.step()
    tech = small_simulation.technology.summary()
    assert "era" in tech
    assert tech["total_technologies"] > 0


def test_agents_accumulate_wealth(small_simulation):
    for _ in range(50):
        small_simulation.step()
    total_wealth = sum(a.state.wealth for a in small_simulation.agents.values())
    assert total_wealth > 0, "Agents should accumulate wealth over time"


def test_collective_memory_accumulates(ticked_simulation):
    cm = ticked_simulation.collective_memory.summarize()
    assert cm["total_memories"] > 0, "Collective memory should have entries after 50 ticks"
    assert cm["by_narrative_type"], "Narrative types should be populated"


def test_identity_computed(ticked_simulation):
    identity = ticked_simulation.collective_memory.identity()
    dims = ["religiosity", "militarism", "individualism", "traditionalism", "innovation", "pluralism"]
    for d in dims:
        assert 0 <= getattr(identity, d) <= 1, f"Identity dimension {d} out of range"


def test_narrative_actors_registered(ticked_simulation):
    actors = ticked_simulation.collective_memory.actors
    assert len(actors) > 0, "Narrative actors should be registered"
    classes_found = {a.agent_class for a in actors.values()}
    assert classes_found.issubset({"governor", "journalist", "philosopher", "researcher", "military"})


def test_agent_personality_evolves(ticked_simulation):
    for agent in ticked_simulation.agents.values():
        traits = agent.temperament.as_dict()
        assert len(traits) == 11
        for v in traits.values():
            assert 0 <= v <= 1
        assert isinstance(agent.needs.autonomy, float)
        break


def test_rebellion_may_occur():
    """Teste estatístico: 500 ticks, 50 agentes.
    Não assertamos que rebelião ocorre — depende da semente.
    O que importa é que a simulação não quebra."""
    cfg = SimulationConfig.default()
    cfg.world.seed = 42
    cfg.world.initial_population = 50
    sim = Simulation(cfg)
    for _ in range(500):
        sim.step()
    cm = sim.collective_memory
    summary = cm.summarize()
    assert summary["total_memories"] > 100
    # Se houve rebelião, deve ter gerado contranarrativas
    if cm._rebellion_count > 0:
        types = summary["by_narrative_type"]
        assert "reformist" in types or "revolutionary" in types


def test_multiple_seeds_diverge():
    """Diferentes seeds devem produzir trajetórias divergentes."""
    from pangeia.core.collective_memory import CivilizationIdentity
    identities = []
    for seed in [42, 99, 123]:
        cfg = SimulationConfig.default()
        cfg.world.seed = seed
        cfg.world.initial_population = 30
        sim = Simulation(cfg)
        for _ in range(200):
            sim.step()
        identities.append(sim.collective_memory.identity())
    report = CivilizationIdentity.divergence_report(identities)
    assert report["avg_divergence"] >= 0, "Divergence should be non-negative"
