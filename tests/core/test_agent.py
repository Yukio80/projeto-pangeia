"""Testes da classe base Agent."""

import random

import pytest
from pangeia.core.agent import Agent, AgentState, ReputationEntry, LifeEvent
from pangeia.core.psychology import Temperament, EmotionalState, PsychologicalNeeds
from pangeia.config import SimulationConfig


class DummyAgent(Agent):
    """Agente concreto para teste (Agent é abstrato)."""
    def __init__(self, config, rng=None):
        super().__init__("citizen", config, rng)

    def decide(self, sim):
        return ["working"]


@pytest.fixture
def config():
    return SimulationConfig.default()


@pytest.fixture
def rng():
    return random.Random(42)


@pytest.fixture
def agent(config, rng):
    return DummyAgent(config, rng=rng)


class TestAgentCreation:
    def test_agent_id_format(self, agent):
        assert agent.agent_id.startswith("A")
        assert len(agent.agent_id) == 9  # A + 8 hex chars

    def test_agent_id_deterministic(self, config):
        a = DummyAgent(config, rng=random.Random(42))
        b = DummyAgent(config, rng=random.Random(42))
        assert a.agent_id == b.agent_id

    def test_initial_state(self, agent):
        assert agent.state.is_alive
        assert agent.state.wealth > 0
        assert agent.state.health > 0
        assert agent.state.energy > 0
        assert agent.state.age == 0

    def test_personality_initialized(self, agent):
        assert isinstance(agent.temperament, Temperament)
        assert isinstance(agent.emotions, EmotionalState)
        assert isinstance(agent.needs, PsychologicalNeeds)
        assert len(agent.temperament.as_dict()) == 11

    def test_archetype_assigned(self, agent):
        assert agent.archetype is not None
        assert agent.archetype.archetype_type.value in (
            "mercador", "guerreiro", "inventor", "sacerdote",
            "diplomata", "artista", "explorador", "burocrata", "criminoso",
        )

    def test_memory_initialized(self, agent):
        assert agent.memory is not None
        assert len(agent.memory.short_term) > 0  # identity memory

    def test_skills_initialized(self, agent):
        assert isinstance(agent.skills, dict)

    def test_goals_from_archetype(self, agent):
        assert len(agent.goals) >= 1


class TestAgentState:
    def test_add_life_event(self, agent):
        agent.state.add_life_event(0, "test", "test event", 0.5)
        assert len(agent.state.life_events) == 1
        ev = agent.state.life_events[0]
        assert ev.tick == 0
        assert ev.event_type == "test"

    def test_trim_reputation(self, agent):
        for i in range(30):
            agent.state.reputation[f"A{i:08x}"] = ReputationEntry(
                agent_id=f"A{i:08x}", trust=0.5, respect=0.3, fear=0.1,
                last_interaction=i,
            )
        agent.state.trim_reputation(20)
        assert len(agent.state.reputation) <= 20

    def test_get_friends(self, agent):
        agent.state.add_personal_relation("A001", "friend", 0.8, "test", 0)
        agent.state.add_personal_relation("A002", "enemy", 0.2, "test", 0)
        friends = agent.state.get_friends()
        assert "A001" in friends
        assert "A002" not in friends

    def test_as_dict(self, agent):
        d = agent.state.as_dict()
        assert d["agent_id"] == agent.agent_id
        assert d["alive"] is True
        assert "wealth" in d


class TestAgentMethods:
    def test_work_accumulates_wealth(self, agent):
        initial = agent.state.wealth
        output = agent.work()
        assert agent.state.wealth >= initial
        assert output >= 0

    def test_learn(self, agent):
        initial = agent.skills.get("test_skill", 0.0)
        agent.learn("test_skill", amount=0.1)
        assert agent.skills.get("test_skill", 0) > initial

    def test_add_goal(self, agent):
        agent.add_goal("test goal", 0.9, "custom")
        assert any(g.description == "test goal" for g in agent.goals)

    def test_perceive_returns_dict(self, agent, small_simulation):
        sim = small_simulation
        for _ in range(5):
            sim.step()
        for a in sim.agents.values():
            perception = a.perceive(sim)
            assert isinstance(perception, dict)
            assert "tick" in perception
            break

    def test_record_emotional_event(self, agent):
        agent.record_emotional_event(tick=0, event_type="discovery", description="Found something")
        assert len(agent.emotional_memories) >= 1
        mem = agent.emotional_memories[-1]
        assert mem.event_type == "discovery"

    def test_add_cultural_influence(self, agent):
        agent.add_cultural_influence("TestGroup", "religion", {"trust": 0.8, "cooperation": 0.7})
        assert len(agent.cultural_influences) >= 1


class TestAgentPersonalityEvolution:
    def test_temperament_mutates(self, agent, rng):
        original = agent.temperament.as_dict().copy()
        for _ in range(100):
            agent.temperament.mutate(rate=0.005, rng=rng)
        mutated = agent.temperament.as_dict()
        # After 100 mutations, at least one trait should have changed
        assert any(abs(mutated[k] - original[k]) > 0.001 for k in original)

    def test_needs_decay(self, agent):
        initial = agent.needs.as_dict().copy()
        for _ in range(50):
            agent.needs.decay(rate=0.003)
        current = agent.needs.as_dict()
        for k in initial:
            assert current[k] <= initial[k], f"Need {k} should decay"

    def test_needs_satisfy(self, agent):
        agent.needs.decay(rate=0.1)
        agent.needs.satisfy(autonomy=0.2, competence=0.15, belonging=0.1)
        assert agent.needs.autonomy > 0.5  # Satisfied from decay


class TestAgentConsistency:
    def test_summarize_returns_all_keys(self, agent):
        s = agent.summarize()
        expected_keys = {"agent_id", "name", "class", "wealth", "health",
                         "energy", "age", "alive", "personality", "archetype",
                         "emotions", "needs", "goals", "skills", "memory",
                         "relations", "life_events", "cultural_influences",
                         "behavior_modifiers", "contradictions", "knowledge",
                         "reputation", "social", "emotional_memories"}
        for k in expected_keys:
            assert k in s, f"Key {k} missing from summarize()"
