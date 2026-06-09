"""Testes do sistema de Memória Coletiva."""

import random
import math

import pytest
from pangeia.core.collective_memory import (
    CollectiveMemorySystem,
    CollectiveMemory,
    HistoricalVolatility,
    CivilizationIdentity,
    NarrativeActor,
    GenerationCohort,
    get_cohort,
)


@pytest.fixture
def cm():
    return CollectiveMemorySystem(rng=random.Random(42))


def test_add_memory(cm):
    mem = cm.add_memory(tick=0, event_type="founding", description="City founded",
                        narrative="The great founding", importance=0.8)
    assert mem.event_id == "CM00001"
    assert mem.importance == 0.8
    assert mem.dominance > 0
    assert mem.narrative_type == "foundational"
    assert len(cm.memories) == 1


def test_add_memory_with_custom_dominance(cm):
    mem = cm.add_memory(tick=0, event_type="war", description="Great war",
                        narrative="The war to end all wars", importance=0.9,
                        dominance=0.8)
    assert mem.dominance == 0.8


def test_memory_age(cm):
    mem = cm.add_memory(tick=0, event_type="founding", description="Test",
                        narrative="Test", importance=1.0, dominance=0.8)
    mem.age()
    assert mem.generations_passed == 1
    assert mem.importance < 1.0


def test_memory_age_removes_low_importance(cm):
    mem = cm.add_memory(tick=0, event_type="founding", description="Test",
                        narrative="Test", importance=0.05)
    mem.importance = 0.005
    cm.memories = [m for m in cm.memories if m.importance > 0.01]
    assert len(cm.memories) == 0


def test_memory_mythologizes(cm):
    mem = cm.add_memory(tick=0, event_type="founding", description="Test",
                        narrative="Test", importance=0.8, dominance=0.8)
    for _ in range(5):
        mem.age()
    if mem.narrative_type == "myth":
        assert "lenda" in mem.narrative.lower() or "antigos" in mem.narrative.lower()


def test_step_no_memories(cm):
    cm.step(tick=20, generations=1)
    assert cm.rebellion_probability == 0.0


def test_step_accumulates_rebellion_probability(cm):
    for i in range(5):
        cm.add_memory(tick=i, event_type="founding", description=f"Event {i}",
                      narrative=f"Event {i}", importance=0.9, dominance=0.8)
    for _ in range(10):
        cm.step(tick=20, generations=1)
    assert cm.rebellion_probability > 0


def test_rebellion_generates_counter_narratives(cm):
    for i in range(5):
        cm.add_memory(tick=i, event_type="founding", description=f"Event {i}",
                      narrative=f"Event {i}", importance=0.9, dominance=0.8)
    cm.rebellion_probability = 1.0
    cm._do_rebellion()
    assert cm._rebellion_count == 1
    types = [m.narrative_type for m in cm.memories]
    assert "reformist" in types
    assert cm.summarize()["by_narrative_type"].get("reformist", 0) >= 1


def test_cohort_bias(cm):
    assert cm.get_cohort_rebellion_bias(0) == 1.4
    assert cm.get_cohort_rebellion_bias(30) == 1.4
    assert cm.get_cohort_rebellion_bias(31) == 0.8
    assert cm.get_cohort_rebellion_bias(100) == 0.8
    assert cm.get_cohort_rebellion_bias(101) == 0.3


def test_get_cohort():
    assert get_cohort(0) == GenerationCohort.YOUNG
    assert get_cohort(30) == GenerationCohort.YOUNG
    assert get_cohort(31) == GenerationCohort.ADULT
    assert get_cohort(100) == GenerationCohort.ADULT
    assert get_cohort(101) == GenerationCohort.ELDER


def test_get_memories_filters(cm):
    for i in range(10):
        cm.add_memory(tick=i, event_type="founding", description=f"Event {i}",
                      narrative=f"Event {i}", importance=0.5)
    assert len(cm.get_memories(min_importance=0.6)) == 0
    assert len(cm.get_memories(min_importance=0.3)) == 10


def test_get_memories_limit(cm):
    for i in range(20):
        cm.add_memory(tick=i, event_type="founding", description=f"Event {i}",
                      narrative=f"Event {i}", importance=0.5)
    assert len(cm.get_memories(limit=5)) == 5


def test_get_emotional_bias(cm):
    cm.add_memory(tick=0, event_type="war", description="War",
                  narrative="War", importance=0.8,
                  emotional_charge={"anger": 0.8, "fear": 0.6})
    bias = cm.get_emotional_bias()
    assert abs(bias.get("anger", 0)) > 0


def test_get_myths(cm):
    mem = cm.add_memory(tick=0, event_type="founding", description="Test",
                        narrative="Test", importance=0.8, dominance=0.8)
    mem.narrative_type = "myth"
    assert len(cm.get_myths()) == 1


def test_most_influential(cm):
    for i in range(10):
        cm.add_memory(tick=i, event_type="founding", description=f"Event {i}",
                      narrative=f"Event {i}", importance=0.3 + i * 0.07)
    top = cm.most_influential(3)
    assert len(top) == 3
    assert top[0].importance >= top[1].importance >= top[2].importance


def test_cite(cm):
    mem = cm.add_memory(tick=0, event_type="founding", description="Test",
                        narrative="Test", importance=0.5)
    cm.cite(mem.event_id)
    assert mem.citation_count >= 2


class TestHistoricalVolatility:
    def test_default_regime(self):
        v = HistoricalVolatility()
        assert v.regime_label() == "estável"

    def test_compute_no_memories(self, cm):
        v = HistoricalVolatility()
        v.compute(cm, tick=0)
        assert v.composite == 0.0

    def test_compute_with_memories(self, cm):
        for i in range(10):
            cm.add_memory(tick=i, event_type="founding", description=f"Event {i}",
                          narrative=f"Event {i}", importance=0.7, dominance=0.6)
        cm.step(tick=20, generations=5)
        v = cm.volatility(20)
        assert 0 <= v.composite <= 1
        assert v.regime_label() in ("estável", "instável", "revolucionária", "decadente", "fragmentada")

    def test_as_dict(self, cm):
        v = cm.volatility(0)
        d = v.as_dict()
        assert "composite" in d
        assert "regime" in d
        assert "rebellion_count" in d


class TestNarrativeActor:
    def test_register_actor(self, cm):
        cm.register_actor("A001", "Test Actor", "governor",
                          influence=0.7, ideology="conservative", charisma=0.6)
        assert "A001" in cm.actors
        assert cm.actors["A001"].effective_power() > 0

    def test_actor_promote_increases_dominance(self, cm):
        mem = cm.add_memory(tick=0, event_type="founding", description="Test",
                            narrative="Test", importance=0.5, dominance=0.5)
        actor = cm.register_actor("A001", "Test", "governor",
                                  influence=0.9, ideology="conservative", charisma=0.9)
        impact = actor.promote(mem, cm)
        assert impact > 0
        assert mem.dominance > 0.5
        assert actor.promote_count == 1

    def test_actor_attack_decreases_dominance(self, cm):
        mem = cm.add_memory(tick=0, event_type="revolution", description="Rev",
                            narrative="Rev", importance=0.8, dominance=0.8)
        actor = cm.register_actor("A001", "Test", "governor",
                                  influence=0.9, ideology="conservative", charisma=0.9)
        impact = actor.attack(mem, cm)
        assert impact > 0
        assert mem.dominance < 0.8
        assert actor.attack_count == 1

    def test_actor_step_promotes_or_attacks(self, cm):
        for i in range(5):
            cm.add_memory(tick=i, event_type="founding", description=f"Event {i}",
                          narrative=f"Event {i}", importance=0.7, dominance=0.6,
                          narrative_type="foundational")
        cm.register_actor("A001", "Conservative Gov", "governor",
                          influence=0.9, ideology="conservative", charisma=0.9)
        cm.register_actor("A002", "Rebel Philosopher", "philosopher",
                          influence=0.9, ideology="revolutionary", charisma=0.9)
        for _ in range(200):
            cm.actor_step(tick=0)
        total_actions = sum(a.promote_count + a.attack_count for a in cm.actors.values())
        assert total_actions > 0

    def test_remove_actor(self, cm):
        cm.register_actor("A001", "Test", "governor")
        assert "A001" in cm.actors
        cm.remove_actor("A001")
        assert "A001" not in cm.actors


class TestCivilizationIdentity:
    def test_default_values(self):
        ident = CivilizationIdentity()
        for dim in ["religiosity", "militarism", "individualism",
                     "traditionalism", "innovation", "pluralism"]:
            assert getattr(ident, dim) == 0.5

    def test_compute_no_memories(self, cm):
        ident = CivilizationIdentity()
        ident.compute([], HistoricalVolatility(), {}, 0, 1)
        assert ident.religiosity == 0.5  # unchanged for empty

    def test_compute_with_memories(self, cm):
        cm.add_memory(tick=0, event_type="founding", description="Founding",
                      narrative="Founding", importance=0.8, dominance=0.7)
        ident = cm.compute_identity(tech_discovered=5, total_techs=26)
        dims = ["religiosity", "militarism", "individualism",
                "traditionalism", "innovation", "pluralism"]
        for d in dims:
            assert 0 <= getattr(ident, d) <= 1, f"Dimension {d} out of range"

    def test_dominant_tendency(self, cm):
        ident = CivilizationIdentity()
        ident.religiosity = 0.9
        ident.traditionalism = 0.8
        ident.innovation = 0.2
        tendency = ident.dominant_tendency()
        assert tendency == "religiosa"

    def test_as_dict_keys(self, cm):
        ident = cm.compute_identity()
        d = ident.as_dict()
        assert "dominant_tendency" in d
        assert d["dominant_tendency"] in (
            "religiosa", "militarista", "individualista",
            "tradicionalista", "inovadora", "plural"
        )

    def test_divergence_report(self, cm):
        idents = [
            CivilizationIdentity(religiosity=0.8, militarism=0.3),
            CivilizationIdentity(religiosity=0.2, militarism=0.7),
        ]
        report = CivilizationIdentity.divergence_report(idents)
        assert "religiosity" in report
        assert report["avg_divergence"] > 0


class TestCollectiveMemorySystem:
    def test_full_cycle_500_ticks(self):
        """Teste de longa duração: 500 ticks com 30 agentes."""
        from pangeia.config import SimulationConfig
        from pangeia.simulation import Simulation
        cfg = SimulationConfig.default()
        cfg.world.seed = 42
        cfg.world.initial_population = 30
        sim = Simulation(cfg)
        for _ in range(500):
            sim.step()
        cm = sim.collective_memory
        summary = cm.summarize()
        assert summary["total_memories"] > 50
        # Se houve rebelião, deve ter gerado contranarrativas
        if cm._rebellion_count > 0:
            types = summary["by_narrative_type"]
            assert any(t in types for t in ("reformist", "revolutionary"))

    def test_summarize_keys(self, cm):
        s = cm.summarize()
        assert "total_memories" in s
        assert "by_narrative_type" in s
        assert "avg_dominance" in s
        assert "rebellion_count" in s
        assert "volatility" in s
        assert "identity" in s
        assert "actors" in s
