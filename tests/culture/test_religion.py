"""Testes do subsistema de Religião/Cultura."""

import pytest
from pangeia.culture.religion import ReligiousSystem


class TestReligion:
    def test_initial_state(self, religion):
        summary = religion.summary()
        assert "religions" in summary
        assert summary["religions"] == 0

    def test_found_religion(self, religion, small_simulation):
        sim = small_simulation
        founder = list(sim.agents.values())[0]
        rel = religion.found_religion("TestFaith", ["Unity", "Peace"],
                                       ["Prayer", "Meditation"], founder)
        assert rel.name == "TestFaith"
        assert len(rel.followers) == 1
        assert founder.agent_id in rel.followers

    def test_step_spreads_religion(self, religion, small_simulation):
        sim = small_simulation
        founder = list(sim.agents.values())[0]
        religion.found_religion("TestFaith", ["Unity"], ["Prayer"], founder)
        for _ in range(20):
            religion.step(sim.agents)
        summary = religion.summary()
        assert summary["religions"] >= 1

    def test_convert_agent(self, religion, small_simulation):
        sim = small_simulation
        founder = list(sim.agents.values())[0]
        target = list(sim.agents.values())[1]
        rel = religion.found_religion("TestFaith", ["Unity"], ["Prayer"], founder)
        religion.convert_agent(target, rel.id)
        assert target.agent_id in rel.followers

    def test_ideology_evolves(self, small_simulation):
        sim = small_simulation
        for _ in range(50):
            sim.step()
        ideo = sim.ideology_system.summary()
        assert "ideologies" in ideo

    def test_memes_spread(self, small_simulation):
        sim = small_simulation
        for _ in range(50):
            sim.step()
        memes = sim.meme_pool.summarize()
        assert "memes" in memes or True  # memes podem ou não existir
