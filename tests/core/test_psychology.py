"""Testes do sistema de personalidade (psychology.py)."""

import random
import math

import pytest
from pangeia.core.psychology import (
    Temperament,
    Archetype,
    ArchetypeType,
    random_archetype,
    ARCHETYPE_DEFINITIONS,
    generate_temperament_with_contradictions,
    EmotionalState,
    EmotionalMemory,
    PsychologicalNeeds,
    AgentBehaviorModifiers,
    CulturalInfluence,
    compute_action_bias,
    DecisionWeights,
    TRAIT_NAMES,
)
from pangeia.config import SimulationConfig


@pytest.fixture
def rng():
    return random.Random(42)


class TestTemperament:
    def test_defaults_in_range(self):
        t = Temperament()
        for name in TRAIT_NAMES:
            val = getattr(t, name)
            assert 0 <= val <= 1, f"Trait {name} = {val} out of [0,1]"

    def test_random_distribution(self, rng):
        t = Temperament.random(rng)
        for name in TRAIT_NAMES:
            val = getattr(t, name)
            assert 0 <= val <= 1, f"Trait {name} = {val} out of [0,1]"

    def test_random_is_deterministic(self):
        rng_a = random.Random(42)
        rng_b = random.Random(42)
        a = Temperament.random(rng_a).as_dict()
        b = Temperament.random(rng_b).as_dict()
        assert a == b

    def test_get(self, rng):
        t = Temperament.random(rng)
        for name in TRAIT_NAMES:
            assert t.get(name) == getattr(t, name)
        assert t.get("nonexistent") == 0.5

    def test_mutate_small_change(self, rng):
        t = Temperament.random(rng)
        original = t.as_dict().copy()
        t.mutate(rate=0.005, rng=rng)
        mutated = t.as_dict()
        total_delta = sum(abs(mutated[k] - original[k]) for k in TRAIT_NAMES)
        assert total_delta < 0.5, "Mutation should produce small changes"

    def test_mutate_bounds(self, rng):
        t = Temperament.random(rng)
        # Force extremes
        for name in TRAIT_NAMES:
            setattr(t, name, 0.0)
        t.mutate(rate=0.1, rng=rng)
        for name in TRAIT_NAMES:
            val = getattr(t, name)
            assert 0 <= val <= 1, f"Trait {name} = {val} out of bounds after mutate"

    def test_mutate_bounds_high(self, rng):
        t = Temperament.random(rng)
        for name in TRAIT_NAMES:
            setattr(t, name, 1.0)
        t.mutate(rate=0.1, rng=rng)
        for name in TRAIT_NAMES:
            val = getattr(t, name)
            assert 0 <= val <= 1, f"Trait {name} = {val} out of bounds after mutate"

    def test_contradictions_valid(self, rng):
        t = generate_temperament_with_contradictions(rng)
        cs = t.contradictions()
        for c in cs:
            assert " vs " in c, f"Invalid contradiction format: {c}"

    def test_as_dict_keys(self, rng):
        t = Temperament.random(rng)
        d = t.as_dict()
        assert set(d.keys()) == set(TRAIT_NAMES)


class TestArchetype:
    def test_all_archetypes_have_modifiers(self):
        for at in ArchetypeType:
            arch = ARCHETYPE_DEFINITIONS[at]
            assert arch.trait_modifiers, f"Archetype {at} has no trait modifiers"
            assert arch.preferred_actions, f"Archetype {at} has no preferred actions"

    def test_all_archetypes_loaded(self):
        assert len(ARCHETYPE_DEFINITIONS) == 9

    def test_apply_modifies_temperament(self, rng):
        base = Temperament.random(rng)
        for at in ArchetypeType:
            arch = ARCHETYPE_DEFINITIONS[at]
            modified = arch.apply(base)
            assert modified is not base, "apply() should return a new instance"

    def test_random_archetype_distribution(self, rng):
        counts = {}
        for _ in range(1000):
            at = random_archetype(rng)
            counts[at] = counts.get(at, 0) + 1
        # All archetypes should appear at least once
        assert len(counts) == 9
        # Should be roughly uniform
        for count in counts.values():
            assert 80 <= count <= 150, f"Archetype count {count} outside expected range"


class TestEmotionalState:
    def test_default_values(self):
        e = EmotionalState()
        assert 0 <= e.happiness <= 1
        assert e.anger == 0.0
        assert e.fear == 0.0
        assert e.sadness == 0.0

    def test_update_modifies(self):
        e = EmotionalState()
        e.update(delta_anger=0.5, delta_happiness=-0.2)
        assert e.anger == pytest.approx(0.5)
        assert e.happiness == pytest.approx(0.3)
        assert e.trust == 0.5  # unchanged

    def test_as_dict(self):
        e = EmotionalState()
        d = e.as_dict()
        assert "happiness" in d
        assert "anger" in d


class TestPsychologicalNeeds:
    def test_defaults(self):
        n = PsychologicalNeeds()
        assert n.autonomy == 0.7
        assert n.competence == 0.7
        assert n.belonging == 0.7

    def test_decay(self):
        n = PsychologicalNeeds()
        n.decay(rate=0.005)
        assert n.autonomy == pytest.approx(0.695, rel=1e-3)
        assert n.competence == pytest.approx(0.695, rel=1e-3)
        assert n.belonging == pytest.approx(0.695, rel=1e-3)

    def test_satisfy(self):
        n = PsychologicalNeeds()
        n.satisfy(autonomy=0.1, competence=0.05)
        assert n.autonomy == pytest.approx(0.8)
        assert n.competence == pytest.approx(0.75)
        assert n.belonging == pytest.approx(0.7)

    def test_satisfy_bounds(self):
        n = PsychologicalNeeds()
        n.satisfy(autonomy=1.0)
        assert n.autonomy <= 1.0

    def test_lowest(self):
        n = PsychologicalNeeds()
        n.autonomy = 0.3
        name, val = n.lowest()
        assert name == "autonomy"
        assert val == pytest.approx(0.3)


class TestEmotionalMemory:
    def test_decay(self):
        em = EmotionalMemory(
            event_id="E001", tick=0, event_type="test",
            description="test", participants=[],
            anger=0.8, intensity=1.0,
        )
        em.decay(rate=0.002)
        assert em.anger < 0.8
        assert em.intensity < 1.0

    def test_decay_bounds(self):
        em = EmotionalMemory(
            event_id="E001", tick=0, event_type="test",
            description="test", participants=[],
            anger=0.01, intensity=0.01,
        )
        em.decay(rate=0.1)
        assert em.anger >= 0.0
        assert em.intensity >= 0.0


class TestAgentBehaviorModifiers:
    def test_add_and_get(self):
        bm = AgentBehaviorModifiers()
        bm.add("war", 0, "agressividade", 0.2, duration=10, decay=0.01)
        delta = bm.get_total_delta(0, "agressividade")
        assert delta == pytest.approx(0.2)

    def test_decay_over_time(self):
        bm = AgentBehaviorModifiers()
        bm.add("war", 0, "agressividade", 0.2, duration=10, decay=0.02)
        delta = bm.get_total_delta(5, "agressividade")
        assert delta < 0.2, "Delta should decay over time"


class TestComputeActionBias:
    def test_returns_float_in_range(self, rng):
        t = Temperament.random(rng)
        em = EmotionalState()
        needs = PsychologicalNeeds()
        bm = AgentBehaviorModifiers()
        for action in ("working", "socializing", "researching"):
            score = compute_action_bias(action, t, bm, em, needs, tick=0)
            assert 0 <= score <= 1, f"Score {score} for {action} out of [0,1]"

    def test_working_preferred_by_diligent(self, rng):
        t = Temperament.random(rng)
        t.disciplina = 0.9
        t.impulsividade = 0.1
        t.ambicao = 0.9
        em = EmotionalState()
        needs = PsychologicalNeeds()
        bm = AgentBehaviorModifiers()
        work_score = compute_action_bias("working", t, bm, em, needs, tick=0)
        social_score = compute_action_bias("socializing", t, bm, em, needs, tick=0)
        assert work_score > social_score, "Diligent agent should prefer work over socializing"

    def test_socializing_preferred_by_sociable(self, rng):
        t = Temperament.random(rng)
        t.sociabilidade = 0.9
        t.disciplina = 0.1
        em = EmotionalState()
        needs = PsychologicalNeeds()
        needs.belonging = 0.1  # Low belonging → higher need
        bm = AgentBehaviorModifiers()
        social_score = compute_action_bias("socializing", t, bm, em, needs, tick=0)
        work_score = compute_action_bias("working", t, bm, em, needs, tick=0)
        assert social_score >= work_score, "Sociable agent should prefer socializing"
